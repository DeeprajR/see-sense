"""Record Wayfinder's fixed sentences once with ElevenLabs, so they play instantly and offline.

    python tools/prewarm_voices.py

Already-recorded sentences are skipped. Claude's route sentences are new every time: they are
recorded as they're spoken (or the local voice is used if that isn't quick enough).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from main import FIXED_SENTENCES  # noqa: E402
from voices import CloudVoices  # noqa: E402


def main():
    voices = CloudVoices()
    if not voices.provider:
        sys.exit("No ElevenLabs key: put ELEVENLABS_API_KEY in .env first.")
    todo = [s for s in FIXED_SENTENCES if not voices.cached(s)]
    print(f"{len(FIXED_SENTENCES)} sentences, {len(todo)} to record, voice: {voices.voice_id()}")
    failed = 0
    for text in todo:
        if not voices.synthesize(text):
            failed += 1
            voices._offline_until = 0.0              # keep trying the rest
    print(f"done: {len(todo) - failed} recorded, {failed} failed")


if __name__ == "__main__":
    main()
