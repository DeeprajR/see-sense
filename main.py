"""SENSE Wayfinder: hold the button, say where you want to go, and get guided there.

    python main.py                          # on the Pi (Pi Camera, button, mic, motors, sensor)
    python main.py --source 0 --show        # laptop webcam, preview window, type requests

Claude looks through the chest camera, asks you to turn until it can see the way, then gives
the route a few steps at a time (press the button for the next step) and looks again to update
it. The distance sensor buzzes, and says "Stop" when something is very close: that part needs
no internet and no AI.
"""

import argparse
import sys
import threading
import time

import config
from camera import is_live, open_camera
from controls import HELP, Controls
from distance import DistanceSensor
from haptics import Haptics
from motion import YawEstimator
from planner import MESSAGES, Planner, PlannerError
from speech import Speaker, wait_quiet
from voice import Listener, clean
from voices import CloudVoices

# Fixed sentences (tools/prewarm_voices.py records them, so they play instantly and offline).
READY = "Wayfinder ready. Hold the button and tell me where you want to go."
LOOKING = "Let me look."
LOOKING_AGAIN = "Let me look again."
STILL_LOOKING = "Still looking."
NO_ROUTE = "There's no route yet. Hold the button and tell me where you want to go."
ASK_HINT = "Hold the button to answer."
NOT_HEARD = "I didn't hear anything. Hold the button while you speak."
NOTHING_TO_REPEAT = "Nothing to repeat."
STOPPED = "Stopped."
OBSTACLE = "Stop. Something right in front of you."
MIC_MISSING = "The microphone is not available."
CAMERA_MISSING = "Camera not found."
CAMERA_LOST = "Camera disconnected."
PRESS_WHEN_DONE = "Press the button when you're done."
KEEP_TURNING = {"left": "Keep turning left.", "right": "Keep turning right."}
FIXED_SENTENCES = [READY, LOOKING, LOOKING_AGAIN, STILL_LOOKING, NO_ROUTE, ASK_HINT, NOT_HEARD,
                   PRESS_WHEN_DONE,
                   NOTHING_TO_REPEAT, STOPPED, OBSTACLE, MIC_MISSING, CAMERA_MISSING, CAMERA_LOST,
                   *KEEP_TURNING.values(), *MESSAGES]

# Short spoken commands (anything else is a new request, or the answer to Claude's question).
COMMANDS = {
    "stop": {"stop", "cancel", "stop guiding", "never mind", "nevermind", "quit"},
    "next": {"next", "next step", "continue", "go on", "done", "ok", "okay", "what next",
             "what's next", "and then", "then what"},
    "repeat": {"repeat", "again", "say again", "say that again", "pardon", "what", "sorry"},
    "look": {"look again", "check again", "look", "where am i", "where now", "am i there",
             "are we there", "now what"},
}


def parse_command(text: str) -> str | None:
    t = clean(text)
    return next((name for name, phrases in COMMANDS.items() if t in phrases), None)


def cpu_temp() -> float | None:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read()) / 1000
    except OSError:
        return None


class App:
    def __init__(self, args):
        self.args = args
        self.speaker = Speaker(args.tts, cloud=CloudVoices() if args.tts != "print" else None)
        self.haptics = Haptics(args.haptics)
        self.distance = DistanceSensor()
        self.listener = Listener()
        self.controls = Controls()
        self.yaw = YawEstimator()
        self.planner = Planner()
        self.frame = None
        self.last_said = ""
        self.gen = 0                    # bumped on every new request / stop: older work is dropped
        self.thinking = False
        self.waiting_answer = False     # Claude asked a question; the next utterance answers it
        self._last_buzz = self._last_warn = 0.0
        self._expected_until = 0.0      # a known blocker is right ahead: buzz, but don't say "Stop"
        self.running = True
        print(f"[wayfinder] tts: {self.speaker.backend} | voice: "
              f"{'elevenlabs' if config.ELEVENLABS_API_KEY else 'local'} | haptics: {self.haptics.name} | "
              f"distance: {self.distance.model or 'none'} | claude: "
              f"{config.CLAUDE_MODEL if self.planner.client else 'off (' + self.planner.reason + ')'}")

    # --- output -------------------------------------------------------------------

    def say(self, text: str, urgent: bool = False, haptic: str | None = None, where: str = "all"):
        print(f"[say] {text}")
        self.speaker.say(text, urgent=urgent)
        if haptic:
            self.haptics.play(haptic, where)
        if not urgent:
            self.last_said = text

    # --- input ----------------------------------------------------------------------

    def handle(self, action: tuple):
        kind = action[0]
        if kind == "quit":
            self.running = False
        elif kind == "ptt_toggle":
            self.handle(("ptt_stop",) if self.listener.capturing else ("ptt_start",))
        elif kind == "ptt_start":
            self.speaker.interrupt()                    # stop talking: the user wants to speak
            if self.listener.start_capture():
                self.haptics.play("listening", "all")
                print("[voice] recording... (release the button / press v again to send)")
            else:
                self.say(MIC_MISSING)
        elif kind == "ptt_stop":
            self.listener.stop_capture()
        elif kind == "text":
            self.on_text(action[1])
        elif kind == "next":
            self.next_step()
        elif kind == "look":
            self.look_again()
        elif kind == "repeat":
            self.say(self.last_said or NOTHING_TO_REPEAT)
        elif kind == "stop":
            self.stop()

    def on_text(self, text: str):
        print(f"[voice] heard: {text!r}")
        text = clean(text)
        if not text:
            self.say(NOT_HEARD)
            return
        command = parse_command(text)
        if command == "stop":
            self.stop()
        elif command == "next":
            self.next_step()
        elif command == "repeat":
            self.say(self.last_said or NOTHING_TO_REPEAT)
        elif command == "look":
            self.look_again()
        elif self.waiting_answer:
            self.waiting_answer = False
            self.think(f'They answered: "{text}"')
        else:
            self.start(text)

    # --- guiding ---------------------------------------------------------------------

    def start(self, goal: str):
        self.gen += 1                                   # a new request replaces the old one
        self.waiting_answer = False
        self.planner.begin(goal, self.yaw.yaw)
        self.say(LOOKING)
        self.think()

    def stop(self):
        self.gen += 1
        self.thinking = self.waiting_answer = False
        self.planner.reset()
        self.speaker.interrupt()
        self.say(STOPPED)

    def next_step(self):
        if self.thinking:
            self.say(STILL_LOOKING)
        elif not self.planner.has_goal:
            self.say(NO_ROUTE)
        else:
            step = self.planner.next_step()
            if step:
                self.say(step)
            else:                                       # time for a new photo
                self.say(LOOKING_AGAIN)
                self.think(self.planner.progress_note())

    def look_again(self):
        if self.thinking:
            self.say(STILL_LOOKING)
        elif not self.planner.has_goal:
            self.say(NO_ROUTE)
        else:
            self.say(LOOKING_AGAIN)
            self.think(self.planner.progress_note())

    def think(self, note: str = ""):
        self.thinking = True
        threading.Thread(target=self._think, args=(self.gen, note), daemon=True).start()

    def _think(self, gen: int, note: str):
        """Look -> (turn the wearer and look again)* -> plan / ask / arrived / answer."""
        cancelled = lambda: gen != self.gen                       # noqa: E731
        self.thinking = True
        try:
            while not cancelled():
                if self.frame is None:
                    return
                try:
                    turn = self.planner.think(self.frame.copy(), self.yaw.yaw, self.distance.read(), note)
                except PlannerError as exc:
                    if not cancelled():
                        self.say(str(exc))
                    return
                if cancelled():
                    return
                print(f"[plan] {turn.action}: {turn.say} {turn.steps or ''}")
                turning = turn.look_direction in ("left", "right")
                if turn.action == "look":
                    self.say(turn.say, haptic="turn" if turning else None,
                             where=turn.look_direction if turning else "all")
                    note = self.guide_turn(turn.look_direction, turn.look_degrees, cancelled)
                    continue
                if turn.action == "arrived":
                    self.say(turn.say, haptic="arrived")
                elif turn.action == "plan":
                    self.say(turn.say, haptic="turn" if turning else "ready",
                             where=turn.look_direction if turning else "all")
                    if turning and turn.look_degrees >= config.TURN_TOLERANCE_DEG:
                        self.guide_turn(turn.look_direction, turn.look_degrees, cancelled)
                    step = self.planner.next_step()       # first walking step, after the turn
                    if step and not cancelled():
                        self.say(step)
                elif turn.action == "ask_user":
                    self.say(turn.say)
                    self.say(ASK_HINT)
                    self.waiting_answer = True
                else:
                    self.say(turn.say)
                return
        finally:
            if not cancelled():         # a newer request owns the flag otherwise
                self.thinking = False

    def guide_turn(self, direction: str, degrees: int, cancelled) -> str:
        """Wait while the wearer turns as asked (measured from the image); report what happened."""
        wait_quiet(self.speaker, 8)                     # let them hear the instruction first
        if direction in ("up", "down"):
            time.sleep(3)
            return f"They tilted the camera {direction}."
        if direction in ("step_left", "step_right"):
            time.sleep(config.STEP_ASIDE_S)
            return f"They took one step to the {direction[5:]}."
        target = max(10, min(abs(degrees), 150))
        start = self.yaw.yaw
        t0 = last_pulse = last_remind = time.monotonic()
        sign = -1 if direction == "left" else 1
        while time.monotonic() - t0 < config.TURN_TIMEOUT_S and not cancelled():
            if sign * (self.yaw.yaw - start) >= target - config.TURN_TOLERANCE_DEG:
                break
            now = time.monotonic()
            if now - last_pulse >= config.TURN_PULSE_EVERY_S:
                self.haptics.play("turn", direction)    # keep turning this way
                last_pulse = now
            if now - last_remind >= config.TURN_REMIND_S and not self.speaker.busy:
                self.say(KEEP_TURNING[direction])
                last_remind = now
            time.sleep(0.1)
        time.sleep(config.SETTLE_S)                     # let the picture settle
        turned = self.yaw.yaw - start
        short = sign * turned < target - config.TURN_TOLERANCE_DEG
        return (f"They turned {abs(turned):.0f} degrees to the {'left' if turned < 0 else 'right'}"
                + (f" (asked for {target}; they may not have turned fully)" if short else "") + ".")

    # --- every frame -------------------------------------------------------------------

    def guard(self, now: float):
        """Distance sensor: buzz when something is close ahead, say "Stop" when very close.
        Walking up to a known blocker (a chair to move), say what to do with it instead."""
        d = self.distance.read()
        if d is None:
            return
        if self.planner.blocker and not self.thinking and d < config.APPROACH_NOTIFY_M:
            self.say(self.planner.reached_blocker(), haptic="stop", where="ahead")
            self.say(PRESS_WHEN_DONE)
            self._expected_until = now + config.BLOCKER_QUIET_S
            return
        if d >= config.OBSTACLE_BUZZ_M:
            return
        if d < config.OBSTACLE_STOP_M:
            if now - self._last_warn >= config.OBSTACLE_SAY_EVERY_S and now >= self._expected_until:
                self._last_warn = now
                self.say(OBSTACLE, urgent=True)
            if now - self._last_buzz >= config.OBSTACLE_BUZZ_EVERY_S:
                self._last_buzz = now
                self.haptics.play("stop", "ahead")
        elif now - self._last_buzz >= config.OBSTACLE_BUZZ_EVERY_S:
            self._last_buzz = now
            self.haptics.play("obstacle", "ahead")

    def step(self, frame):
        now = time.monotonic()
        self.frame = frame
        self.yaw.update(frame, now)
        self.guard(now)
        for action in self.controls.poll():
            self.handle(action)

    def run(self):
        try:
            cam = open_camera(self.args.source)
        except Exception:
            self.speaker.say(CAMERA_MISSING, urgent=True)   # the wearer can't see the terminal
            time.sleep(3)
            raise
        self.listener.start(lambda text: self.controls.actions.put(("text", text)))
        self.say(READY if self.planner.client else
                 f"Wayfinder started, but route planning is off: {self.planner.reason}.", haptic="ready")
        print(HELP)
        if self.args.show:
            import cv2

        frames, t_report, lost = 0, time.monotonic(), False
        try:
            while self.running:
                frame = cam.read()
                if frame is None:
                    lost = is_live(self.args.source)
                    break
                self.step(frame[..., :3])
                if self.args.show:
                    cv2.imshow("Wayfinder", draw_overlay(frame.copy(), self))
                    self.controls.key(cv2.waitKey(1))
                frames += 1
                if time.monotonic() - t_report >= 10:
                    temp, d = cpu_temp(), self.distance.read()
                    print(f"[wayfinder] {frames / (time.monotonic() - t_report):.0f} fps, "
                          f"turned {self.yaw.yaw:+.0f} deg" + (f", cpu {temp:.0f} C" if temp else "")
                          + (f", ahead {d:.2f} m" if d is not None else ""))
                    frames, t_report = 0, time.monotonic()
        except KeyboardInterrupt:
            pass
        finally:
            if lost:
                self.speaker.say(CAMERA_LOST, urgent=True)
                time.sleep(3)
            self.haptics.off()
            cam.close()
            if self.args.show:
                cv2.destroyAllWindows()
        if lost:
            sys.exit(1)            # the service restarts and reconnects the camera


def draw_overlay(img, app: App):
    import cv2

    h, w = img.shape[:2]
    d = app.distance.read()
    lines = [f"turned {app.yaw.yaw:+.0f} deg",
             "thinking..." if app.thinking else ("goal: " + app.planner.goal if app.planner.goal else "idle")]
    if app.planner.steps:
        lines.append(f"step {app.planner.step_index}/{len(app.planner.steps)}")
    if d is not None:
        lines.append(f"ahead {d:.2f} m")
    for i, text in enumerate(lines):
        cv2.putText(img, text, (10, 32 + 32 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    for i, m in enumerate(config.MOTORS):           # the 4 motors along the bottom: filled = on
        cx, cy = int(w * (i + 0.5) / len(config.MOTORS)), h - 24
        on = app.haptics.state[m] > 0
        cv2.circle(img, (cx, cy), 15, (0, 0, 255) if on else (90, 90, 90), -1 if on else 2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="picam", help="'picam', webcam index, video path or stream URL")
    ap.add_argument("--show", action="store_true", help="preview window (laptop)")
    ap.add_argument("--tts", default=config.TTS_BACKEND,
                    choices=["auto", "espeak", "windows", "print"])
    ap.add_argument("--haptics", default=config.HAPTICS_BACKEND, choices=["auto", "gpio", "sim", "off"])
    App(ap.parse_args()).run()


if __name__ == "__main__":
    main()
