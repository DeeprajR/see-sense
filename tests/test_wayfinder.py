"""Tests for SENSE Wayfinder that need no camera, mic, motors, sensor or internet:

    python tests/test_wayfinder.py

Claude is replaced by a fake that returns scripted answers, so the whole guiding flow
(look -> turn -> plan -> next steps -> look again -> arrived) is checked offline.
"""

import argparse
import json
import os
import sys
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import config  # noqa: E402
from main import (ASK_HINT, LOOKING, LOOKING_AGAIN, NO_ROUTE, OBSTACLE, PRESS_WHEN_DONE,  # noqa: E402
                  STOPPED, App, parse_command)
from planner import Planner, keep_latest_images  # noqa: E402
from voice import clean, to_vosk  # noqa: E402

config.TURN_TIMEOUT_S = 0.3
config.SETTLE_S = 0.0
config.STEP_ASIDE_S = 0.0


def reply(action, say, direction="none", degrees=0, steps=(), blocker="", instruction=""):
    return {"action": action, "look_direction": direction, "look_degrees": degrees, "seen": "",
            "say": say, "steps": list(steps), "blocker": blocker, "blocker_instruction": instruction}


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeClaude:
    """Stands in for anthropic.Anthropic: returns the scripted replies in order."""

    def __init__(self, replies, delay=0.0, error=None):
        self.replies, self.delay, self.error = list(replies), delay, error
        self.calls: list[dict] = []
        self.beta = Obj(messages=Obj(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        time.sleep(self.delay)
        if self.error:
            raise self.error
        text = json.dumps(self.replies.pop(0))
        return Obj(stop_reason="end_turn", content=[Obj(type="text", text=text)],
                   usage=Obj(input_tokens=1000, output_tokens=50), model=config.CLAUDE_MODEL)

    def last_text(self) -> str:
        return self.calls[-1]["messages"][-1]["content"][1]["text"]


def make_app(replies=(), **kw):
    app = App(argparse.Namespace(source="none", show=False, tts="print", haptics="sim"))
    app.planner.client = FakeClaude(replies, **kw)
    app.frame = np.zeros((360, 640, 3), np.uint8)
    app.said = []
    original = app.say

    def record(text, *a, **k):
        app.said.append(text)
        original(text, *a, **k)
    app.say = record
    return app


def settle(app, timeout=3.0):
    """Wait for the background planning thread to finish."""
    end = time.monotonic() + timeout
    time.sleep(0.05)
    while app.thinking and time.monotonic() < end:
        time.sleep(0.02)


class TestCommands(unittest.TestCase):
    def test_short_commands(self):
        self.assertEqual(parse_command("Sense, next"), "next")
        self.assertEqual(parse_command("stop"), "stop")
        self.assertEqual(parse_command("say that again"), "repeat")
        self.assertEqual(parse_command("am I there"), "look")

    def test_requests_are_not_commands(self):
        for text in ("take me to the door", "next room please", "I want to go out", "find a seat"):
            self.assertIsNone(parse_command(text), text)

    def test_clean(self):
        self.assertEqual(clean("Hey Sense, take me to the EXIT!"), "take me to the exit")


class TestPlanner(unittest.TestCase):
    def test_only_latest_photos_are_resent(self):
        img = {"type": "image", "source": {}}
        msgs = []
        for i in range(3):
            msgs += [{"role": "user", "content": [img, {"type": "text", "text": f"t{i}"}]},
                     {"role": "assistant", "content": "{}"}]
        out = keep_latest_images(msgs, 2)
        kinds = [m["content"][0]["type"] for m in out if m["role"] == "user"]
        self.assertEqual(kinds, ["text", "image", "image"])
        self.assertEqual(msgs[0]["content"][0]["type"], "image")      # original untouched

    def test_steps_then_look_again(self):
        p = Planner()
        p.client = FakeClaude([reply("plan", "The door is ahead.",
                                     steps=["Walk 3 steps.", "Turn left.", "Walk 2 steps."])])
        p.begin("door", 0)
        p.think(np.zeros((90, 160, 3), np.uint8), 0, None)
        self.assertEqual(p.next_step(), "Walk 3 steps.")
        self.assertEqual(p.next_step(), "Turn left.")      # 2 steps since the photo
        self.assertIsNone(p.next_step())                   # time for a new photo
        self.assertIn("Walk 3 steps. / Turn left.", p.progress_note())

    def test_steps_are_spoken_properly(self):
        from planner import spoken
        self.assertEqual(spoken("walk forward about 3 steps"), "Walk forward about 3 steps.")
        self.assertEqual(spoken("Stop here!"), "Stop here!")

    def test_out_of_looks_becomes_answer(self):
        p = Planner()
        p.client = FakeClaude([reply("look", "Turn right.", "right", 40)] * 10)
        p.begin("door", 0)
        actions = [p.think(np.zeros((90, 160, 3), np.uint8), 0, None).action
                   for _ in range(config.MAX_LOOKS + 1)]
        self.assertEqual(actions[-1], "answer")
        self.assertFalse(p.has_goal)


class TestGuiding(unittest.TestCase):
    def test_look_then_plan_then_steps_then_arrived(self):
        app = make_app([
            reply("look", "Turn right about 30 degrees.", "right", 30),
            reply("plan", "The door is ahead, about 5 steps.",
                  steps=["Walk 3 steps.", "The chair will be on your left.", "Walk 2 more steps."]),
            reply("arrived", "The door is right in front of you. The handle is on the right."),
        ])
        app.on_text("take me to the door")
        settle(app)
        self.assertEqual(app.said[:4], [LOOKING, "Turn right about 30 degrees.",
                                        "The door is ahead, about 5 steps.", "Walk 3 steps."])
        claude = app.planner.client
        self.assertIn('They asked: "take me to the door"', claude.calls[0]["messages"][0]["content"][1]["text"])
        self.assertIn("They turned 0 degrees", claude.last_text())       # turn was measured and reported
        app.handle(("next",))
        self.assertEqual(app.said[-1], "The chair will be on your left.")
        app.handle(("next",))                                             # 2 steps done: look again
        settle(app)
        self.assertEqual(app.said[-2:], [LOOKING_AGAIN, "The door is right in front of you. "
                                                         "The handle is on the right."])
        self.assertIn("They followed these steps", claude.last_text())
        self.assertFalse(app.planner.has_goal)
        app.handle(("next",))
        self.assertEqual(app.said[-1], NO_ROUTE)

    def test_question_and_answer(self):
        app = make_app([reply("ask_user", "Which door: the front door or the side door?"),
                        reply("plan", "The front door is ahead.", steps=["Walk 4 steps."])])
        app.on_text("take me to the door")
        settle(app)
        self.assertEqual(app.said[-1], ASK_HINT)
        app.on_text("the front door")
        settle(app)
        self.assertIn('They answered: "the front door"', app.planner.client.last_text())
        self.assertEqual(app.said[-1], "Walk 4 steps.")

    def test_stop_drops_a_late_answer(self):
        app = make_app([reply("plan", "Walk 4 steps.", steps=["Walk 4 steps."])], delay=0.3)
        app.on_text("take me to the exit")
        app.on_text("stop")
        time.sleep(0.5)
        self.assertEqual(app.said[-1], STOPPED)
        self.assertNotIn("Walk 4 steps.", app.said)

    def test_no_internet(self):
        import anthropic
        import httpx

        err = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
        app = make_app(error=err)
        app.on_text("take me to the exit")
        settle(app)
        self.assertIn("can't reach the internet", app.said[-1])
        self.assertFalse(app.planner.available)         # don't retry for OFFLINE_RETRY_S


class TestSurvey(unittest.TestCase):
    def test_plan_turns_first_then_walks(self):
        app = make_app([reply("plan", "The nearest door is on your right. Turn right about 90 degrees.",
                              "right", 90, steps=["Walk about 4 steps.", "Reach out for the handle."])])
        app.on_text("take me to the exit")
        settle(app)
        self.assertEqual(app.said[-2:], ["The nearest door is on your right. Turn right about 90 degrees.",
                                         "Walk about 4 steps."])     # step comes after the guided turn
        self.assertEqual(len(app.planner.client.calls), 1)

    def test_step_aside_to_see_past_a_corner(self):
        app = make_app([reply("look", "Take one step to your left to see past the corner.", "step_left"),
                        reply("plan", "The door is ahead.", steps=["Walk 2 steps."])])
        app.on_text("take me to the exit")
        settle(app)
        self.assertIn("They took one step to the left.", app.planner.client.last_text())
        self.assertEqual(app.said[-1], "Walk 2 steps.")

    def test_prompt_rules(self):
        from planner import SYSTEM
        for rule in ("SURVEY", "nearest", "TRACE THE WALKWAY", "look from another angle",
                     "blocker_instruction", "Never ask them to move a person", "not stairs"):
            self.assertIn(rule, SYSTEM)


class TestBlocker(unittest.TestCase):
    def test_reaching_a_chair_to_move(self):
        move = "The chair is right in front of you. Push it to your left to clear the way."
        app = make_app([reply("plan", "The door is ahead, but a chair is in the way.",
                              steps=["Walk about 2 steps, slowly.", "Stop at the chair."],
                              blocker="chair", instruction=move),
                        reply("plan", "The way is clear now.", steps=["Walk 3 steps."])])
        app.on_text("take me to the door")
        settle(app)
        app.distance.read = lambda: 1.5
        app.guard(100.0)
        self.assertNotIn(move, app.said)                     # not there yet
        app.distance.read = lambda: 0.7
        app.guard(101.0)
        self.assertEqual(app.said[-2:], [move, PRESS_WHEN_DONE])
        app.distance.read = lambda: 0.3                      # touching the chair while moving it
        app.guard(102.0)
        self.assertNotIn(OBSTACLE, app.said)                 # expected: no "Stop"
        app.handle(("next",))                                # done: new photo to check the way
        settle(app)
        self.assertIn("They reached the chair", app.planner.client.last_text())
        self.assertEqual(app.said[-1], "Walk 3 steps.")


class TestDistanceGuard(unittest.TestCase):
    def test_very_close_says_stop_once(self):
        app = make_app()
        app.distance.read = lambda: 0.3
        for t in (100.0, 100.5, 101.0):
            app.guard(t)
        self.assertEqual(app.said.count(OBSTACLE), 1)

    def test_close_only_buzzes(self):
        app = make_app()
        app.distance.read = lambda: 0.8
        app.guard(100.0)
        time.sleep(0.05)
        self.assertNotIn(OBSTACLE, app.said)
        self.assertGreater(app.haptics.state["front_left"], 0)


class TestMic(unittest.TestCase):
    def test_inmp441_audio_to_vosk(self):
        block = (np.sin(np.linspace(0, 200, 48000)) * 2**24).astype(np.int32)   # 1 s, 48 kHz
        pcm = to_vosk(block, 48000, 16.0)
        self.assertEqual(len(pcm), 16000 * 2)                                 # 1 s, 16 kHz, int16


if __name__ == "__main__":
    unittest.main()
