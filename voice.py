"""Push-to-talk: hold the button, speak, release.

Audio is only kept while the button is held, and recognised once on release, so the
microphone costs almost no processor time the rest of the time (no always-on wake word).
Recognition: ElevenLabs speech-to-text when online (much more accurate); offline, Vosk on the Pi,
which also gives its top few guesses so Claude can pick the one that makes sense.
The INMP441 delivers quiet 32-bit stereo I2S audio (usually 48 kHz); we take one channel,
amplify it and resample to the 16 kHz mono Vosk expects.
"""

import io
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


def vosk_guesses(result: dict) -> list[str]:
    """Vosk's result -> its guesses, best first (with or without alternatives turned on)."""
    if "alternatives" in result:
        return [a.get("text", "") for a in result["alternatives"] if a.get("text", "").strip()]
    return [result["text"]] if result.get("text", "").strip() else []


def to_wav(pcm16: bytes, rate: int = VOSK_RATE) -> bytes:
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm16)
    return buf.getvalue()


_STT_DENIED = False      # the ElevenLabs key isn't allowed to do speech-to-text


def elevenlabs_stt(pcm16: bytes) -> str | None:
    """Speech-to-text with ElevenLabs (Scribe). None if it fails (then Vosk is used)."""
    import urllib.request
    import uuid

    boundary = uuid.uuid4().hex
    fields = {"model_id": "scribe_v1", "language_code": "en", "tag_audio_events": "false"}
    body = b""
    for name, value in fields.items():
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                 f"{value}\r\n").encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"speech.wav\"\r\n"
             f"Content-Type: audio/wav\r\n\r\n").encode() + to_wav(pcm16) + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body, method="POST",
                                 headers={"xi-api-key": config.ELEVENLABS_API_KEY,
                                          "Content-Type": f"multipart/form-data; boundary={boundary}"})
    import urllib.error

    global _STT_DENIED
    try:
        with urllib.request.urlopen(req, timeout=config.STT_TIMEOUT_S) as r:
            return json.loads(r.read()).get("text", "").strip()
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 402, 403):             # the key or plan doesn't allow it: stop trying
            _STT_DENIED = True
            print(f"[voice] ElevenLabs speech-to-text not allowed (HTTP {exc.code}): turn on the "
                  f"'Speech to Text' permission for the API key in ElevenLabs. Using Vosk.")
        else:
            print(f"[voice] ElevenLabs speech-to-text failed ({exc}); using Vosk")
        return None
    except Exception as exc:
        print(f"[voice] ElevenLabs speech-to-text failed ({exc}); using Vosk")
        return None


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
        self._cloud_off_until = 0.0
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
        """Load the model and open the mic in the background. on_text(text, guesses) gets each
        utterance: the best transcript, and other possible transcripts (may be empty)."""
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

            audio = to_vosk(np.concatenate(blocks), self._rate, self._gain) if blocks else b""
            text, guesses = self.recognise(audio)
            self.on_text(clean(text), [clean(g) for g in guesses])
        threading.Thread(target=work, daemon=True).start()

    def recognise(self, audio: bytes) -> tuple[str, list[str]]:
        """(best transcript, other guesses). Cloud first when online; Vosk otherwise."""
        if len(audio) < VOSK_RATE * 2 * 0.3:            # under 0.3 s: nothing was said
            return "", []
        use_cloud = (config.STT_BACKEND in ("auto", "elevenlabs") and config.ELEVENLABS_API_KEY
                     and not _STT_DENIED and time.monotonic() >= self._cloud_off_until)
        if use_cloud:
            text = elevenlabs_stt(audio)
            if text is not None:
                return text, []
            self._cloud_off_until = time.monotonic() + config.OFFLINE_RETRY_S
        import vosk

        rec = vosk.KaldiRecognizer(self._model, VOSK_RATE)
        rec.SetMaxAlternatives(config.VOSK_ALTERNATIVES)
        rec.AcceptWaveform(audio)
        guesses = vosk_guesses(json.loads(rec.FinalResult()))
        return (guesses[0], guesses[1:]) if guesses else ("", [])

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
