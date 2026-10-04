"""Speaking in the earbuds, one sentence at a time, in a background thread.

Urgent sentences ("Stop. Something right in front of you.") cut off whatever is being said.
With the ElevenLabs voice (voices.py) a recorded sentence plays from the on-device cache;
anything not available in time uses the local voice (espeak-ng / Windows), so nothing
is ever delayed for want of a network. On the Pi, audio goes to the paired Bluetooth earbuds.
"""

from dataclasses import dataclass
import os
import shutil
import signal
import subprocess
import threading
import time

import config


@dataclass
class Line:
    text: str
    urgent: bool = False


def pick_backend(name: str) -> str:
    if name != "auto":
        return name
    if os.name == "nt":
        return "windows"
    if shutil.which("espeak-ng"):
        return "espeak"
    return "print"


class Speaker:
    def __init__(self, backend: str = config.TTS_BACKEND, cloud=None):
        self.backend = pick_backend(backend)
        self.cloud = cloud if self.backend != "print" else None   # print = tests / silent runs
        self._queue: list[Line] = []
        self._cv = threading.Condition()
        self._proc: subprocess.Popen | None = None
        self._playing = False
        self._current: Line | None = None
        threading.Thread(target=self._run, daemon=True).start()

    @property
    def busy(self) -> bool:
        return bool(self._queue) or self._current is not None

    def say(self, text: str, urgent: bool = False):
        with self._cv:
            if urgent:
                self._queue.clear()
                self._stop_current()
                self._queue.insert(0, Line(text, True))
            else:
                self._queue.append(Line(text))
            self._cv.notify()

    def interrupt(self):
        """The user wants to talk: stop speaking and drop what's queued (except urgent warnings)."""
        with self._cv:
            self._queue = [line for line in self._queue if line.urgent]
            if not (self._current and self._current.urgent):
                self._stop_current()

    def _run(self):
        while True:
            with self._cv:
                while not self._queue:
                    self._cv.wait()
                self._current = self._queue.pop(0)
            try:
                self._say(self._current)
            except Exception as exc:
                print(f"[speech] failed: {exc}")
            finally:
                self._current = None

    def _say(self, line: Line):
        if self.cloud is not None:
            audio = self.cloud.prepare(line.text, urgent=line.urgent)
            if audio:
                self._play_wav(audio)
                return
        self._speak(line.text)                        # local voice

    def _play_wav(self, data: bytes):
        import io
        import wave

        import numpy as np
        import sounddevice as sd

        with wave.open(io.BytesIO(data)) as w:
            rate, channels = w.getframerate(), w.getnchannels()
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, channels)
        self._playing = True
        try:
            sd.play(pcm, rate)
            sd.wait()
        finally:
            self._playing = False

    def _speak(self, text: str):
        if self.backend == "print":
            return
        if self.backend == "espeak":
            proc = subprocess.Popen(["espeak-ng", "-s", str(config.ESPEAK_SPEED), "--stdin"],
                                    stdin=subprocess.PIPE, start_new_session=True)
        elif self.backend == "windows":
            ps = ("Add-Type -AssemblyName System.Speech; "
                  "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak([Console]::In.ReadToEnd())")
            proc = subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], stdin=subprocess.PIPE)
        else:
            raise ValueError(f"Unknown TTS backend {self.backend!r}")
        self._proc = proc
        try:
            proc.communicate(text.encode())
        finally:
            self._proc = None

    def _stop_current(self):
        if self._playing:
            import sounddevice as sd

            sd.stop()                               # cut off a recorded sentence
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            if os.name != "nt":
                os.killpg(proc.pid, signal.SIGTERM)
            else:
                proc.kill()
        except ProcessLookupError:
            pass


def wait_quiet(speaker: Speaker, timeout: float = 15):
    """Block until everything queued has been said (used before beeps and in tests)."""
    end = time.monotonic() + timeout
    while speaker.busy and time.monotonic() < end:
        time.sleep(0.05)
