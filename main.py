"""SEE SENSE: hold the button, say where you want to go, and get guided there.

    python main.py                          # on the Pi (Pi Camera, button, mic, motors, sensor)
    python main.py --stream                 # ...and watch the camera at http://<PI_IP>:8000
    python main.py --source 0 --show        # laptop webcam, preview window, type requests

Claude looks through the chest camera, asks you to turn until it can see the way, then gives
the route a few steps at a time (press the button for the next step) and looks again to update
it. JEV checks what the mic heard before it goes to Claude, and picks which things Claude saw
need an extra alert. The distance sensor buzzes, and says "Stop" when something is very close:
that part needs no internet and no AI.
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
from jev import Jev, warning
from motion import YawEstimator
from planner import MESSAGES, Planner, PlannerError
from speech import Speaker, wait_quiet
from voice import Listener, clean
from voices import CloudVoices

# Fixed sentences (tools/prewarm_voices.py records them, so they play instantly and offline).
READY = "See Sense ready. Hold the button and tell me where you want to go."
LOOKING = "Let me look."
LOOKING_AGAIN = "Let me look again."
STILL_LOOKING = "Still looking."
NO_ROUTE = "There's no route yet. Hold the button and tell me where you want to go."
ASK_HINT = "Hold the button to answer."
NOT_HEARD = "I didn't hear anything. Hold the button while you speak."
UNCLEAR = "Sorry, I didn't catch that. Hold the button and say it again."
NOTHING_TO_REPEAT = "Nothing to repeat."
STOPPED = "Stopped."
OBSTACLE = "Stop. Something right in front of you."
MIC_MISSING = "The microphone is not available."
CAMERA_MISSING = "Camera not found."
CAMERA_LOST = "Camera disconnected."
PRESS_WHEN_DONE = "Press the button when you're done."
KEEP_TURNING = {"left": "Keep turning left.", "right": "Keep turning right."}
TURN_DONE = "OK, stop."
FIXED_SENTENCES = [READY, LOOKING, LOOKING_AGAIN, STILL_LOOKING, NO_ROUTE, ASK_HINT, NOT_HEARD,
                   UNCLEAR, PRESS_WHEN_DONE,
                   NOTHING_TO_REPEAT, STOPPED, OBSTACLE, MIC_MISSING, CAMERA_MISSING, CAMERA_LOST,
                   *KEEP_TURNING.values(), TURN_DONE, *MESSAGES]

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
        self.jev = Jev()
        self.frame = None
        self.question = ""              # Claude's last question to the wearer (for JEV)
        self.last_seen = ""             # Claude's note on the latest photo (live view)
        self.live = None
        if args.stream:
            from liveview import LiveView

            self.live = LiveView()
        self.last_said = ""
        self.gen = 0                    # bumped on every new request / stop: older work is dropped
        self.thinking = False
        self.waiting_answer = False     # Claude asked a question; the next utterance answers it
        self._last_buzz = self._last_warn = 0.0
        self._expected_until = 0.0      # a known blocker is right ahead: buzz, but don't say "Stop"
        self.running = True
        print(f"[seesense] tts: {self.speaker.backend} | voice: "
              f"{'elevenlabs' if config.ELEVENLABS_API_KEY else 'local'} | haptics: {self.haptics.name} | "
              f"distance: {self.distance.model or 'none'} | claude: "
              f"{config.CLAUDE_MODEL if self.planner.client else 'off (' + self.planner.reason + ')'}"
              f" | jev: {'on' if config.JEV_API_KEY else 'off (' + self.jev.reason + ')'}")

    # --- output -------------------------------------------------------------------

    def say(self, text: str, urgent: bool = False, haptic: str | None = None, where: str = "all"):
        if not text:
            return
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
        elif kind == "checked":                         # JEV's verdict on what was said
            self.route(action[1], action[2])
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
        command = parse_command(text)                  # the usual short commands: instant
        if command:
            self.route(text, command)
        elif self.jev.available:                        # JEV: request, command or misheard? (~0.3 s)
            question = self.question if self.waiting_answer else ""

            def check():
                label = self.jev.check_speech(text, question)
                self.controls.actions.put(("checked", text, label))
            threading.Thread(target=check, daemon=True).start()
        else:
            self.route(text, None)

    def route(self, text: str, label: str | None):
        """Act on what was said. label: a command, "unclear", or None/"request"/"answer"."""
        if label == "stop":
            self.stop()
        elif label == "next":
            self.next_step()
        elif label == "repeat":
            self.say(self.last_said or NOTHING_TO_REPEAT)
        elif label == "look":
            self.look_again()
        elif label == "unclear":
            self.say(UNCLEAR)                           # misheard: don't spend a Claude call on it
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
                # Claude can take a while: say so, so the wearer doesn't think it stopped.
                waiting = threading.Timer(config.STILL_LOOKING_AFTER_S,
                                          lambda: None if cancelled() else self.say(STILL_LOOKING))
                waiting.start()
                try:
                    turn = self.planner.think(self.frame.copy(), self.yaw.yaw, self.distance.read(), note)
                except PlannerError as exc:
                    if not cancelled():
                        self.say(str(exc))
                    return
                finally:
                    waiting.cancel()
                if cancelled():
                    return
                print(f"[plan] {turn.action}: {turn.say} {turn.steps or ''}")
                self.last_seen = turn.seen
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
                    told = " ".join(s for s in (turn.say, step) if s)
                    threading.Thread(target=self.notice, args=(turn.objects, told, cancelled),
                                     daemon=True).start()
                elif turn.action == "ask_user":
                    self.say(turn.say)
                    self.say(ASK_HINT)
                    self.question = turn.say
                    self.waiting_answer = True
                else:
                    self.say(turn.say)
                return
        finally:
            if not cancelled():         # a newer request owns the flag otherwise
                self.thinking = False

    def notice(self, objects: list[dict], told: str, cancelled):
        """JEV picks which things Claude saw need an extra alert: say it, or buzz on its side."""
        labels = self.jev.relevance(objects, told)
        if cancelled():
            return
        warned = 0
        for obj, label in zip(objects, labels):
            side = obj["where"]
            if label == "warn" and warned < config.MAX_WARNINGS_PER_LOOK:
                warned += 1
                self.say(warning(obj), haptic="notice", where=side)
            elif label in ("warn", "buzz"):
                self.haptics.play("notice", side)

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
                self.say(TURN_DONE, urgent=True)        # far enough: stop turning
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
                 f"See Sense started, but route planning is off: {self.planner.reason}.", haptic="ready")
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
                if self.live:
                    self.live.update(frame[..., :3], lambda img: draw_overlay(img, self))
                if self.args.show:
                    cv2.imshow("SEE SENSE", draw_overlay(frame.copy(), self))
                    self.controls.key(cv2.waitKey(1))
                frames += 1
                if time.monotonic() - t_report >= 10:
                    temp, d = cpu_temp(), self.distance.read()
                    print(f"[seesense] {frames / (time.monotonic() - t_report):.0f} fps, "
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
    """Status on the picture (preview window and live view): what SEE SENSE is doing right now."""
    import textwrap

    import cv2

    h, w = img.shape[:2]
    s = max(w / 1280, 0.6)                          # scale text to the picture (readable when small)
    d = app.distance.read()
    lines = [f"turned {round(app.yaw.yaw) + 0:+d} deg" + (f"   ahead {d:.2f} m" if d is not None else ""),
             "thinking..." if app.thinking else ("goal: " + app.planner.goal if app.planner.goal else "idle")]
    if app.planner.steps:
        lines.append(f"step {app.planner.step_index}/{len(app.planner.steps)}")

    def text(t, y, color, size=0.9):              # dark shadow first, so it reads on any background
        x, th, o = int(12 * s), max(1, int(2 * s)), max(1, int(2 * s))
        cv2.putText(img, t, (x + o, y + o), cv2.FONT_HERSHEY_SIMPLEX, size * s, (0, 0, 0), th)
        cv2.putText(img, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, size * s, color, th)

    for i, t in enumerate(lines):
        text(t, int((36 + 36 * i) * s), (0, 255, 255))
    # Bottom: the last thing said and what Claude saw, above the 4 motors.
    bottom = [f"said: {app.last_said}" if app.last_said else "", f"seen: {app.last_seen}" if app.last_seen else ""]
    per_line = max(30, int((w - 24 * s) / (13 * s)))     # characters that fit across
    wrapped = [w_ for b in bottom if b for w_ in textwrap.wrap(b, per_line)][-4:]
    for i, t in enumerate(wrapped):
        text(t, h - int((70 + 30 * (len(wrapped) - i)) * s), (255, 255, 255), 0.65)
    for i, m in enumerate(config.MOTORS):           # the 4 motors along the bottom: filled = on
        cx, cy = int(w * (i + 0.5) / len(config.MOTORS)), h - int(30 * s)
        on = app.haptics.state[m] > 0
        cv2.circle(img, (cx, cy), int(18 * s), (0, 0, 255) if on else (160, 160, 160), -1 if on else 2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="picam", help="'picam', webcam index, video path or stream URL")
    ap.add_argument("--show", action="store_true", help="preview window (laptop, or a Pi with a screen)")
    ap.add_argument("--stream", action="store_true",
                    help=f"live view in a browser: http://<PI_IP>:{config.LIVE_VIEW_PORT}")
    ap.add_argument("--tts", default=config.TTS_BACKEND,
                    choices=["auto", "espeak", "windows", "print"])
    ap.add_argument("--haptics", default=config.HAPTICS_BACKEND, choices=["auto", "gpio", "sim", "off"])
    App(ap.parse_args()).run()


if __name__ == "__main__":
    main()
