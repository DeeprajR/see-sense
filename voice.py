"""Push-to-talk: hold the button, speak, release. Offline speech-to-text with Vosk.

Audio is only kept while the button is held, and recognised once on release, so the
microphone costs almost no processor time the rest of the time (no always-on wake word).
The INMP441 delivers quiet 32-bit stereo I2S audio (usually 48 kHz); we take one channel,
amplify it and resample to the 16 kHz mono Vosk expects.
"""

import json
import os
import re
import threading
import time
import urllib.request
import zipfile

import config

VOSK_RATE = 16000
I2S_NAMES = ("voicehat", "googlevoi", "i2s", "inmp441", "adau7002", "simple-card")


def ensure_model() -> str:
    """Download the small English Vosk model (~40 MB) on first use."""
    path = config.VOSK_MODEL_DIR
    if os.path.isdir(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    zip_path = path + ".zip"
    print(f"[voice] downloading speech model to {path} (~40 MB, one time)...")
    urllib.request.urlretrieve(config.VOSK_MODEL_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(os.path.dirname(path))
    os.remove(zip_path)
    return path


def pick_input_device(devices) -> tuple[int | str | None, bool]:
    """(device, is_i2s). Prefers an I2S mic (INMP441) if one is listed, else the default input."""
    if config.MIC_DEVICE not in (None, "auto"):
        return config.MIC_DEVICE, False
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0 and any(k in d["name"].lower() for k in I2S_NAMES):
            return i, True
    return None, False


def to_vosk(block, rate: int, gain: float) -> bytes:
    """One channel of int16/int32 samples at `rate` -> 16 kHz mono int16 bytes."""
    import numpy as np

    x = block.astype(np.float32)
    x /= 2147483648.0 if block.dtype == np.int32 else 32768.0
    x *= gain
    if rate != VOSK_RATE:
        if rate % VOSK_RATE == 0:          # e.g. 48 kHz: average groups of 3 (cheap anti-alias)
            k = rate // VOSK_RATE
            x = x[: len(x) - len(x) % k].reshape(-1, k).mean(axis=1)
        else:
            n = int(len(x) * VOSK_RATE / rate)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    return (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()


def clean(text: str) -> str:
    """Lower case, no punctuation, and no leading "sense" (people often say it anyway)."""
    words = re.sub(r"[^\w\s']", " ", text.lower()).split()
    if words[:1] == ["sense"]:
        words = words[1:]
    elif words[:2] in (["hey", "sense"], ["okay", "sense"]):
        words = words[2:]
    return " ".join(words)


class Listener:
    def __init__(self):
        self.available = False
        self.ready = False                  # model loaded and microphone open
        self._model = None
        self._blocks: list | None = None    # audio while the button is held
        self._started = 0.0
        self._rate, self._gain = VOSK_RATE, 1.0
        try:
            import sounddevice  # noqa: F401
            import vosk  # noqa: F401
            self.available = True
        except Exception as exc:
            print(f"[voice] microphone unavailable: {exc}")

    def start(self, on_text):
        """Load the model and open the mic in the background. on_text(str) gets each utterance."""
        self.on_text = on_text
        if self.available:
            threading.Thread(target=self._open, daemon=True).start()

    @property
    def capturing(self) -> bool:
        return self._blocks is not None

    def start_capture(self) -> bool:
        if not self.ready:
            return False
        self._blocks = []
        self._started = time.monotonic()
        self._beep(1046)                       # high beep: speak now
        return True

    def stop_capture(self):
        if self._blocks is None:
            return
        blocks, self._blocks = self._blocks, None
        self._beep(587)                        # low beep: got it

        def work():
            import numpy as np
            import vosk

            audio = to_vosk(np.concatenate(blocks), self._rate, self._gain) if blocks else b""
            rec = vosk.KaldiRecognizer(self._model, VOSK_RATE)
            rec.AcceptWaveform(audio)
            self.on_text(clean(json.loads(rec.FinalResult()).get("text", "")))
        threading.Thread(target=work, daemon=True).start()

    def _beep(self, hz: int):
        try:
            import numpy as np
            import sounddevice as sd

            t = np.linspace(0, 0.15, int(VOSK_RATE * 0.15), endpoint=False)
            sd.play((0.3 * np.sin(2 * np.pi * hz * t)).astype(np.float32), VOSK_RATE)
        except Exception:
            pass

    def _callback(self, indata, frames, t, status):
        blocks = self._blocks
        if blocks is None:
            return
        blocks.append(indata[:, self._channel].copy())
        if time.monotonic() - self._started > config.PTT_MAX_S:
            threading.Thread(target=self.stop_capture, daemon=True).start()   # held too long

    def _open(self):
        try:
            import sounddevice as sd
            import vosk

            vosk.SetLogLevel(-1)
            self._model = vosk.Model(ensure_model())
            device, is_i2s = pick_input_device(sd.query_devices())
            info = sd.query_devices(device, "input")
            default_rate = int(info["default_samplerate"])
            self._gain = config.MIC_GAIN or (config.I2S_MIC_GAIN if is_i2s else 1.0)
            last = None
            # I2S hardware often only allows its native rate and stereo, so try a few formats.
            formats = ((default_rate, 1), (48000, 1), (default_rate, 2), (48000, 2)) if is_i2s else \
                ((VOSK_RATE, 1), (default_rate, 1), (default_rate, 2))
            for rate, channels in formats:
                try:
                    self._channel = min(config.MIC_CHANNEL, channels - 1)
                    self._stream = sd.InputStream(device=device, samplerate=rate, channels=channels,
                                                  dtype="int32" if is_i2s else "int16",
                                                  blocksize=int(rate * 0.1), callback=self._callback)
                    self._stream.start()
                    self._rate = rate
                    self.ready = True
                    print(f"[voice] mic: {info['name']} @ {rate} Hz x{channels}, gain {self._gain:g}")
                    return
                except Exception as exc:
                    last = exc
            raise RuntimeError(f"could not open microphone: {last}")
        except Exception as exc:
            print(f"[voice] microphone unavailable: {exc}")
            self.available = False
