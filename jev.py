"""JEV (TypeSafe): quick (~0.3 s), confidence-scored choices on short text. Two jobs:

  A. check_speech(): before anything goes to Claude, is what speech recognition heard a real
     request, a command said another way ("what do I do now" = next), or misheard words?
     "the mind to my home" -> "Sorry, I didn't catch that." at once, not after a slow Claude call.
  B. relevance(): after Claude has planned a route, which of the things it saw need an extra
     alert: say it, buzz on its side, or ignore it. Runs in the background; never delays the route.

Without a key, offline, or unsure (low confidence), SEE SENSE simply carries on without it:
speech goes to Claude as before and nothing extra is announced.
"""

import threading
import time

import config

SPEECH = {
    "request": "asks to be guided or taken somewhere, or to find something: a door, the exit, a "
               "seat, a counter, a room, a toilet, a lift",
    "answer": "answers the question the guide just asked",
    "next": "asks for the next step, or what to do now",
    "stop": "asks to stop or cancel the guidance",
    "repeat": "asks to hear the last instruction again",
    "look": "asks to check again, where they are now, or whether they have arrived",
    "unclear": "makes no sense as any of these: misheard words, unrelated talk or noise",
}

RELEVANCE = {
    "warn": "they must hear about it now to stay safe, and what they were already told doesn't "
            "cover it: someone walking into their path, a step, a drop, something at head "
            "height, a wet floor",
    "buzz": "close by and worth a short vibration on its side, but already covered or minor",
    "ignore": "not relevant to walking there safely",
}


class Jev:
    def __init__(self):
        self.client = None
        self.reason = "" if config.JEV_API_KEY else "no TYPESAFE_API_KEY in .env"
        self._offline_until = 0.0
        if config.JEV_API_KEY:
            threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        try:
            from typesafe_sdk import TypeSafeClient

            self.client = TypeSafeClient(api_key=config.JEV_API_KEY, base_url=None, model=None,
                                         timeout=config.JEV_TIMEOUT_S)
        except Exception as exc:
            self.reason = str(exc)
            print(f"[jev] unavailable: {exc}")

    @property
    def available(self) -> bool:
        return self.client is not None and time.monotonic() >= self._offline_until

    def _choose(self, state: str, questions: dict[str, tuple[str, dict[str, str]]]):
        """{name: (choice, confidence)}, or None if JEV failed (then retried after a pause)."""
        from typesafe_sdk import Choice

        t0 = time.monotonic()
        try:
            resp = self.client.system_one(
                state=state,
                questions={k: Choice(instructions=i, criteria=c) for k, (i, c) in questions.items()})
        except Exception as exc:
            print(f"[jev] failed ({exc}); skipped for {config.OFFLINE_RETRY_S} s")
            self._offline_until = time.monotonic() + config.OFFLINE_RETRY_S
            return None
        out = {k: (resp.answers[k].choice, resp.answers[k].confidence) for k in questions}
        print(f"[jev] {out} in {time.monotonic() - t0:.1f} s")
        return out

    # --- A: what did they say? --------------------------------------------------------

    def check_speech(self, text: str, question: str = "") -> str | None:
        """One of SPEECH's labels, or None (unsure / unavailable: treat it as before)."""
        if not self.available:
            return None
        labels = dict(SPEECH) if question else {k: v for k, v in SPEECH.items() if k != "answer"}
        state = (f'A blind person using a wearable indoor guide said this (from speech recognition, '
                 f'which can mishear): "{text}"')
        if question:
            state += f'\nThe guide had just asked them: "{question}"'
        result = self._choose(state, {"said": ("What did they say?", labels)})
        if result is None:
            return None
        label, confidence = result["said"]
        return label if confidence >= config.JEV_MIN_CONFIDENCE else None

    # --- B: which things that Claude saw need an alert? ---------------------------------

    def relevance(self, objects: list[dict], told: str) -> list[str]:
        """"warn" / "buzz" / "ignore" for each object (ignore when unsure or unavailable)."""
        if not objects or not self.available:
            return ["ignore"] * len(objects)
        state = (f"A blind person is walking a route indoors. Their guide just told them: "
                 f'"{told}"\nThings the camera sees now:\n'
                 + "\n".join(f"{i}. {describe(o)}" for i, o in enumerate(objects)))
        questions = {f"o{i}": (f"Does thing {i} ({o['what']}) need an alert?", RELEVANCE)
                     for i, o in enumerate(objects)}
        result = self._choose(state, questions)
        if result is None:
            return ["ignore"] * len(objects)
        out = []
        for i in range(len(objects)):
            label, confidence = result[f"o{i}"]
            if label == "warn" and confidence < config.JEV_MIN_CONFIDENCE:
                label = "buzz"                     # unsure it's urgent: a touch, not words
            if confidence < config.JEV_MIN_CONFIDENCE / 2:
                label = "ignore"
            out.append(label)
        return out


def describe(o: dict) -> str:
    where = {"left": "on the left", "right": "on the right", "ahead": "ahead"}[o["where"]]
    moving = ", moving toward them" if o["moving_toward"] else ""
    return f"{o['what']} {where}, about {o['distance_m']:g} m{moving}"


def warning(o: dict) -> str:
    """The sentence for a "warn": "A person ahead, coming toward you, about 3 steps away." """
    where = {"left": "on your left", "right": "on your right", "ahead": "ahead"}[o["where"]]
    steps = max(1, round(o["distance_m"] / 0.7))
    moving = ", coming toward you" if o["moving_toward"] else ""
    what = o["what"].strip()
    what = what[0].upper() + what[1:] if what else "Something"
    return f"{what} {where}{moving}, about {steps} step{'s' if steps > 1 else ''} away."
