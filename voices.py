"""Natural English voice (ElevenLabs) with an on-device cache.

    text --(audio cache hit)--> play instantly, offline
         --(miss, not urgent, online)--> synthesize, cache, play
         --(miss, urgent or offline)--> None: the caller uses the local voice now; the
                                         ElevenLabs version is generated in the background

Run tools/prewarm_voices.py once so the standard sentences are cached before going out.
"""

import hashlib
import json
import os
import threading
import time

import config


class CloudVoices:
    def __init__(self):
        self._offline_until = 0.0
        self._warming: set[str] = set()

    @property
    def provider(self) -> str | None:
        return "elevenlabs" if config.ELEVENLABS_API_KEY else None

    @property
    def online(self) -> bool:
        return time.monotonic() >= self._offline_until

    def _went_offline(self, exc: Exception):
        print(f"[voice] ElevenLabs failed ({exc}); local voice for {config.OFFLINE_RETRY_S} s")
        self._offline_until = time.monotonic() + config.OFFLINE_RETRY_S

    def voice_id(self) -> str:
        return f"eleven-{config.ELEVENLABS_MODEL}-{config.ELEVENLABS_VOICE_ID}"

    def cache_path(self, text: str) -> str:
        key = hashlib.sha1(f"{self.voice_id()}|{text}".encode("utf-8")).hexdigest()[:20]
        return os.path.join(config.VOICE_CACHE_DIR, self.voice_id(), key + ".wav")

    def cached(self, text: str) -> bytes | None:
        try:
            with open(self.cache_path(text), "rb") as f:
                return f.read()
        except OSError:
            return None

    def synthesize(self, text: str) -> bytes | None:
        """ElevenLabs speech as WAV bytes (and cache it), or None."""
        if not self.provider or not self.online:
            return None
        try:
            import urllib.error
            import urllib.request

            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
                "?output_format=wav_22050",
                data=json.dumps({"text": text, "model_id": config.ELEVENLABS_MODEL}).encode(),
                headers={"xi-api-key": config.ELEVENLABS_API_KEY, "Content-Type": "application/json"},
                method="POST")
            try:
                with urllib.request.urlopen(req, timeout=config.CLOUD_VOICE_TIMEOUT_S) as r:
                    audio = r.read()
            except urllib.error.HTTPError as exc:
                if exc.code == 402:
                    # e.g. "Free users cannot use library voices via the API": a plan issue, not
                    # a network one. Say so plainly and use the local voice.
                    detail = json.loads(exc.read() or b"{}").get("detail", {})
                    raise RuntimeError(detail.get("message", "payment required")) from None
                raise
        except Exception as exc:
            self._went_offline(exc)
            return None
        path = self.cache_path(text)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(audio)
        return audio

    def prepare(self, text: str, urgent: bool) -> bytes | None:
        """WAV audio for the sentence, or None (= use the local voice).

        Urgent sentences never wait for the network: only cached audio is used, and anything
        missing is fetched in the background so it's ready next time."""
        audio = self.cached(text)
        if audio or not self.provider:
            return audio
        if urgent or not self.online:
            self._warm(text)
            return None
        return self.synthesize(text)

    def _warm(self, text: str):
        if text in self._warming or not self.online:
            return
        self._warming.add(text)

        def work():
            try:
                if not self.cached(text):
                    self.synthesize(text)
            finally:
                self._warming.discard(text)
        threading.Thread(target=work, daemon=True).start()
