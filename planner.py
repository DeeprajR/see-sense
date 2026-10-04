"""Claude finds the way: survey the surroundings, pick the nearest goal, trace the walkway,
clear what's blocking it, then guide a few steps at a time.

    "Take me to the exit"
      -> LOOK     survey: "Turn right about 60 degrees." / "Tilt the camera up." / "Take one
                  step to your left." (to see past a corner). Turns are measured from the camera.
      -> PLAN     "The nearest door is on your right, about 6 steps. Turn right about 90 degrees."
                  (turn guided by vibration) then "Walk about 3 steps."   (button = next step)
                  A movable blocker (chair, empty wheelchair): walk up to it; when the distance
                  sensor says they've reached it: "The chair is right in front of you. Push it to
                  your left to clear the way." + "Press the button when you're done."
      -> every RECHECK_EVERY_STEPS steps: new photo, updated route
      -> ARRIVED  "The door is right in front of you. The handle is on the right."
    ASK_USER (a question back) and ANSWER (no route needed / not found) end a turn too.
"""

import base64
from dataclasses import dataclass, field
import json
import time

import config

_BODY = "head" if config.CAMERA_MOUNT == "head" else "body"

SYSTEM = f"""You guide a blind person to the place they ask for, indoors, using a camera worn on \
their {config.CAMERA_MOUNT}. The camera faces where their {_BODY} faces: horizontal field of view \
about {config.CAMERA_HFOV_DEG} degrees, the image centre is straight ahead. With each photo you get \
which way it faces compared with where they stood when they asked (negative = left; measured from \
the camera) and, when available, a distance sensor reading straight ahead.

Work in this order:
1. SURVEY. Understand the surroundings before planning, and find the nearest goal (for "the exit" \
or "go out": the nearest door or exit). Only if the goal and a clear way to it are plainly visible \
in the first photo may you plan straight away. Otherwise choose "look" to see more: turn left or \
right, tilt the camera up or down, or take one step to the side to see past a corner, a pillar or \
a table. Check both sides before giving up. In "seen", note briefly what this photo shows and \
where (left / ahead / right, rough distance): it is your memory, because older photos are dropped.
2. PICK THE GOAL: the nearest one that can be reached. If there are several, say which you chose.
3. TRACE THE WALKWAY from where they stand to the goal: how far is it clear? A view from beside a \
corner, a pillar or a table can make the way look blocked when it isn't, so before deciding that \
it's blocked, look from another angle.
4. BLOCKERS. If a movable object blocks the way (a chair, an empty wheelchair, a stool, a bag, a \
box), guide them up to just before it, name it in "blocker", and put in "blocker_instruction" \
exactly how to clear it, e.g. "The chair is right in front of you. Push it to your left to clear \
the way." The device says that sentence when its distance sensor shows they've reached it. Never \
ask them to move a person or a wheelchair someone is sitting in: route around, or suggest saying \
"excuse me". Fixed things (tables, walls, counters, pillars): route around them or choose another way.
5. GUIDE a few steps at a time. You get a new photo every couple of steps to check and continue.

Actions:
- "look": see more. look_direction is left / right / up / down / step_left / step_right; \
look_degrees is the turn (15-120) for left / right, else 0.
- "ask_user": the request is unclear. One short question.
- "plan": the route. look_direction / look_degrees: the turn to make before walking (left or \
right; "none" and 0 if they already face the right way). "say": the overview and that turn, e.g. \
"The nearest door is on your right, about 6 steps away. Turn right about 90 degrees." "steps": the \
walking steps after the turn, at most 4, short and physical: "Walk about 3 steps.", "The table \
will be on your left.", "Stop: the chair is one step ahead." Only things to do or notice: no steps \
about checking (the device re-checks by itself). One step is about 0.7 m. Plan only as far as you \
can see clearly.
- "arrived": the goal is within about one step. Say exactly where it is (e.g. where the handle is).
- "answer": a question that needs no route, or the goal wasn't found after looking around: say so \
and suggest asking someone nearby.
"blocker" and "blocker_instruction" are "" unless a plan walks up to a movable blocker.

How to speak: "say" is spoken aloud: one or two short sentences, plain English, no lists or \
markdown. Say when something is uncertain. Never say a path, road or crossing is safe. Mention \
hazards plainly (a step, a drop, a wet floor, a glass door). Only call something stairs when you \
can clearly see steps: windows, blinds, shelves, floor tiles and railings are not stairs. Don't \
identify people; say what they're doing if it matters."""

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["look", "ask_user", "plan", "arrived", "answer"]},
        "look_direction": {"type": "string",
                           "enum": ["left", "right", "up", "down", "step_left", "step_right", "none"]},
        "look_degrees": {"type": "integer"},
        "seen": {"type": "string"},
        "say": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "blocker": {"type": "string"},
        "blocker_instruction": {"type": "string"},
    },
    "required": ["action", "look_direction", "look_degrees", "seen", "say", "steps", "blocker",
                 "blocker_instruction"],
    "additionalProperties": False,
}


class PlannerError(Exception):
    """Something went wrong; str(exc) is what to tell the wearer."""


OFFLINE = "I can't reach the internet, so I can't plan right now. The distance warning still works."
NOT_SET_UP = "Route planning isn't set up on this device."
BUSY = "Too many requests just now. Please try again in a moment."
FAILED = "Sorry, I couldn't work that out. Please try again."
DECLINED = "Sorry, I can't help with that one."
MESSAGES = [OFFLINE, NOT_SET_UP, BUSY, FAILED, DECLINED]


def spoken(text: str) -> str:
    """Steps read better aloud with a capital letter and a full stop."""
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text if not text or text[-1] in ".!?" else text + "."


@dataclass
class Turn:
    action: str
    say: str
    look_direction: str = "none"
    look_degrees: int = 0
    steps: list[str] = field(default_factory=list)
    seen: str = ""
    blocker: str = ""
    blocker_instruction: str = ""


def encode_jpeg(frame) -> str:
    import cv2

    h, w = frame.shape[:2]
    s = config.CLAUDE_MAX_IMAGE_SIDE / max(h, w)
    if s < 1:
        frame = cv2.resize(frame, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.standard_b64encode(buf.tobytes()).decode("ascii")


def keep_latest_images(messages: list, keep: int) -> list:
    """A copy of the conversation where only the newest `keep` photos are still images.
    Older photos become a short note, so each turn uploads less and answers sooner."""
    out, seen = [], 0
    for msg in reversed(messages):
        if msg["role"] == "user" and isinstance(msg["content"], list):
            content = []
            for block in msg["content"]:
                if block["type"] == "image":
                    seen += 1
                    if seen > keep:
                        block = {"type": "text", "text": "(earlier photo, no longer shown)"}
                content.append(block)
            msg = {"role": "user", "content": content}
        out.append(msg)
    return out[::-1]


class Planner:
    def __init__(self):
        self.client = None
        self.reason = ""
        self._offline_until = 0.0
        self.reset()
        if not config.ANTHROPIC_API_KEY:
            self.reason = "no ANTHROPIC_API_KEY in .env"
            return
        try:
            import anthropic

            # A key not scoped to a workspace must name one on every request.
            headers = ({"anthropic-workspace-id": config.ANTHROPIC_WORKSPACE_ID}
                       if config.ANTHROPIC_WORKSPACE_ID else None)
            self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, default_headers=headers,
                                              timeout=config.CLAUDE_TIMEOUT_S, max_retries=1)
        except Exception as exc:
            self.reason = str(exc)

    @property
    def available(self) -> bool:
        return self.client is not None and time.monotonic() >= self._offline_until

    @property
    def has_goal(self) -> bool:
        return bool(self.goal)

    def reset(self):
        self.goal = ""
        self.start_yaw = 0.0
        self.messages: list = []
        self.looks = 0
        self.steps: list[str] = []
        self.step_index = 0           # next step to give
        self.since_photo = 0          # steps given since the last photo
        self.blocker = ""             # movable thing they're walking up to (e.g. "chair")
        self.blocker_instruction = "" # what to tell them when they reach it
        self.notes: list[str] = []    # what happened since the last photo

    def begin(self, goal: str, yaw: float):
        self.reset()
        self.goal, self.start_yaw = goal, yaw

    # --- steps ------------------------------------------------------------------

    def next_step(self) -> str | None:
        """The next step of the route, or None when it's time to look again (a new photo)."""
        if self.step_index < len(self.steps) and self.since_photo < config.RECHECK_EVERY_STEPS:
            step = self.steps[self.step_index]
            self.step_index += 1
            self.since_photo += 1
            return step
        return None

    def reached_blocker(self) -> str:
        """They've walked up to the blocker (distance sensor): what to tell them. The next press
        takes a new photo to check the way is clear."""
        instruction = self.blocker_instruction or f"The {self.blocker} is right in front of you."
        self.notes.append(f'They reached the {self.blocker} and were told: "{instruction}" '
                          f"Then they pressed the button.")
        self.blocker = self.blocker_instruction = ""
        self.since_photo = config.RECHECK_EVERY_STEPS
        return instruction

    def progress_note(self) -> str:
        done = self.steps[:self.step_index]
        parts = ["They followed these steps: " + " / ".join(done)] if done else []
        parts += self.notes
        if self.blocker:
            parts.append(f"They were walking up to the {self.blocker}. If they've reached it, "
                         f'tell them: "{self.blocker_instruction}"')
        parts.append("Here is the new view. If they're at the goal, choose arrived; otherwise "
                     "continue from where they are now.")
        self.notes = []
        return " ".join(parts)

    # --- Claude -------------------------------------------------------------------

    def think(self, frame, yaw: float, distance: float | None, note: str = "") -> Turn:
        """One planning step on the current view. Raises PlannerError with a sentence to speak."""
        if self.client is None:
            raise PlannerError(NOT_SET_UP)
        if not self.available:
            raise PlannerError(OFFLINE)
        import anthropic

        lines = [f"Photo taken facing {yaw - self.start_yaw:+.0f} degrees from where they faced "
                 f"when they asked."]
        if distance is not None:
            lines.append(f"Distance sensor straight ahead: {distance:.1f} m.")
        if not self.messages:
            lines.insert(0, f'They asked: "{self.goal}"')
        if note:
            lines.insert(0, note)
        if self.looks >= config.MAX_LOOKS:
            lines.append("No more looks: give your best plan or answer now.")
        self.messages.append({"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": encode_jpeg(frame)}},
            {"type": "text", "text": "\n".join(lines)}]})

        t0 = time.monotonic()
        try:
            response = self.client.beta.messages.create(
                model=config.CLAUDE_MODEL, max_tokens=4096, system=SYSTEM,
                output_config={"effort": config.CLAUDE_EFFORT,
                               "format": {"type": "json_schema", "schema": SCHEMA}},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                messages=keep_latest_images(self.messages, config.CLAUDE_KEEP_IMAGES))
        except anthropic.AuthenticationError:
            self.client = None
            raise PlannerError("Route planning isn't set up: the Anthropic key was rejected.") from None
        except (anthropic.APIConnectionError, anthropic.APITimeoutError):
            self._offline_until = time.monotonic() + config.OFFLINE_RETRY_S
            self.messages.pop()
            raise PlannerError(OFFLINE) from None
        except anthropic.RateLimitError:
            self.messages.pop()
            raise PlannerError(BUSY) from None
        except anthropic.APIStatusError as exc:
            print(f"[claude] error {exc.status_code}: {exc.message}")
            self.messages.pop()
            if exc.status_code == 400 and "workspace" in str(exc.message):
                self.client = None
                raise PlannerError("Route planning isn't set up: the workspace ID is missing.") from None
            raise PlannerError(FAILED) from None
        if response.stop_reason == "refusal":
            self.messages.pop()
            raise PlannerError(DECLINED)
        raw = next((b.text for b in response.content if b.type == "text"), "")
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            self.messages.pop()
            raise PlannerError(FAILED) from None
        self.messages.append({"role": "assistant", "content": raw})
        print(f"[claude] {d['action']} in {time.monotonic() - t0:.1f} s "
              f"({response.usage.input_tokens} in / {response.usage.output_tokens} out tokens)")

        turn = Turn(d["action"], spoken(d["say"]), d["look_direction"], int(d["look_degrees"]),
                    [spoken(s) for s in d["steps"] if s.strip()], d["seen"].strip(),
                    d["blocker"].strip(), spoken(d["blocker_instruction"]))
        print(f"[claude] seen: {turn.seen}")
        if turn.action == "look" and (self.looks >= config.MAX_LOOKS or turn.look_direction == "none"):
            turn.action = "answer"          # out of looks: speak what it has
        if turn.action == "look":
            self.looks += 1
        elif turn.action == "plan":
            self.steps = turn.steps                     # spoken after "say" and the turn
            self.step_index = self.since_photo = 0
            self.blocker, self.blocker_instruction = turn.blocker, turn.blocker_instruction
        elif turn.action in ("arrived", "answer"):
            self.reset()
        return turn
