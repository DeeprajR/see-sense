"""Settings for SEE SENSE: hold the button, say where you want to go, get guided there."""

import os

# Every file path is relative to this folder, so it runs from any working directory.
HERE = os.path.dirname(os.path.abspath(__file__))


def _p(*parts: str) -> str:
    return os.path.join(HERE, *parts)


def _load_env(path: str = _p(".env")):
    """Read KEY=value lines (API keys) without needing python-dotenv."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.strip().partition("=")
                if sep and key and not key.startswith("#"):
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))
    except OSError:
        pass


_load_env()

# --- Camera (Pi Camera 3, head-mounted) ------------------------------------------
FRAME_SIZE = (1280, 720)       # webcams; the Pi Camera keeps width 1280 at its own shape (16:9)
PICAM_ROTATE_180 = False       # True if the camera is mounted upside down (check: pi/camera_check.py)
PICAM_FRAME_US = 33333         # 30 fps; also the longest exposure, so walking doesn't blur
CAMERA_HFOV_DEG = 66           # Pi Camera 3: 66, Pi Camera 3 Wide: 102
CAMERA_MOUNT = "head"          # head | chest: "turn your head" vs "turn your body"
YAW_MIN_RESPONSE = 0.05        # turn measurement skips frames it can't match (blur, blank)

# --- Claude: sees the camera picture and plans the route ----------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_WORKSPACE_ID = os.environ.get("ANTHROPIC_WORKSPACE_ID", "")  # needed if the key isn't workspace-scoped
CLAUDE_MODEL = "claude-sonnet-5-5"   # later: "claude-opus-5-5" (more accurate, slower, costlier)
CLAUDE_EFFORT = "medium"
CLAUDE_TIMEOUT_S = 15         # per try (one retry)
CLAUDE_MAX_IMAGE_SIDE = 1024   # larger pictures are scaled down: smaller uploads, quicker answers
STILL_LOOKING_AFTER_S = 8      # say "Still looking." if Claude takes longer than this
CLAUDE_KEEP_IMAGES = 3         # only the latest pictures are re-sent (a survey: left, ahead, right)
MAX_LOOKS = 6                  # survey looks (turn / tilt / step aside) at most this many per request
RECHECK_EVERY_STEPS = 2        # after this many steps, take a new picture and update the route
OFFLINE_RETRY_S = 30           # after a network failure, wait this long before trying again

# --- JEV (TypeSafe): quick checks on short text (optional) ----------------------------
# A: is what the mic heard a request, a command, or misheard words?  B: which things Claude saw
# need an extra alert (say / buzz / ignore)? Without the key, SEE SENSE works without these.
JEV_API_KEY = os.environ.get("TYPESAFE_API_KEY", "")
JEV_TIMEOUT_S = 2.5
JEV_MIN_CONFIDENCE = 0.6       # alerts: below this JEV's answer is ignored
JEV_COMMAND_CONFIDENCE = 0.7   # "what do I do now" = next: only when this sure
JEV_UNCLEAR_CONFIDENCE = 0.9   # "misheard": only when this sure; otherwise Claude works it out
MAX_WARNINGS_PER_LOOK = 1      # spoken extra alerts after each route update (the rest buzz)

# --- Internet: say when it's lost or back, and try to reconnect the Wi-Fi ----------------
NET_CHECK_HOST = "api.anthropic.com"   # a connection is opened (no API call, no cost)
NET_CHECK_EVERY_S = 5
NET_FAILS_TO_DROP = 2          # checks in a row that must fail before saying "lost"
RECONNECT_EVERY_S = 30         # while offline, ask the Pi to reconnect the Wi-Fi this often
WIFI_INTERFACE = "wlan0"

# --- Live view (python main.py --stream): the camera in a browser ---------------------
LIVE_VIEW_PORT = 8000          # open http://<PI_IP>:8000 on the same Wi-Fi
LIVE_VIEW_FPS = 10             # pictures per second while someone is watching
LIVE_VIEW_WIDTH = 640          # picture width (smaller = lighter on the Pi and the Wi-Fi)

# --- Guiding a turn ("turn right about 60 degrees") -----------------------------------
TURN_TOLERANCE_DEG = 10        # close enough
TURN_TIMEOUT_S = 12            # stop waiting and look anyway
TURN_PULSE_EVERY_S = 1.0       # vibrate on the side to turn toward
TURN_REMIND_S = 5              # "Keep turning left." if still short of the target
SETTLE_S = 0.7                 # let the picture settle before looking
STEP_ASIDE_S = 4               # "take one step to your left" (to see past a corner): time to do it

# --- Distance sensor (VL53L0X / VL53L1X): works offline, no AI ------------------------
DISTANCE_BACKEND = "auto"      # auto (use it if found) | vl53l1x | vl53l0x | off
OBSTACLE_BUZZ_M = 1.0          # buzz the front motors when something is closer than this
OBSTACLE_STOP_M = 0.5          # ...and say "Stop" when closer than this
OBSTACLE_BUZZ_EVERY_S = 0.8
OBSTACLE_SAY_EVERY_S = 5
APPROACH_NOTIFY_M = 0.8        # walking up to a chair to move: "it's right in front of you" here
BLOCKER_QUIET_S = 30           # ...then don't also say "Stop" about it while they move it

# --- Vibration: 4 motors, left to right across the body ---------------------------
MOTORS = ["left", "front_left", "front_right", "right"]
# BCM pins. Not 18/19/20 (the microphone's I2S pins) and not 16: the microphone driver
# (googlevoicehat) reserves GPIO16 for itself.
MOTOR_PINS = {"left": 12, "front_left": 13, "front_right": 6, "right": 26}
HAPTICS_BACKEND = "auto"       # auto (gpio on a Pi, else sim) | gpio | sim | off
HAPTIC_INTENSITY = 1.0         # 0-1 PWM duty

# --- Button (GPIO17 to GND) ---------------------------------------------------------
BUTTON_PIN = 17                # hold = speak (release to send); short press = next step
PTT_HOLD_S = 0.4               # held this long = speaking (shorter = a press)
PTT_MAX_S = 12                 # stop recording after this long even if still held

# --- Speech recognition ---------------------------------------------------------------
# auto: ElevenLabs speech-to-text when online (much more accurate), Vosk offline otherwise.
STT_BACKEND = "auto"           # auto | elevenlabs | vosk
STT_TIMEOUT_S = 6
VOSK_ALTERNATIVES = 3          # offline: Claude gets the top guesses, not just one
CONTEXT_KEEP_S = 300           # follow-ups within 5 min continue the same conversation
MAX_HISTORY_MESSAGES = 30      # conversation sent to Claude (older turns dropped)

# --- Microphone (INMP441) + offline speech recognition (Vosk) -----------------------
# INMP441 -> Pi 5: VDD 3.3V (pin 1), GND (pin 6), L/R to GND (= left channel),
#                  SCK GPIO18 (pin 12), WS GPIO19 (pin 35), SD GPIO20 (pin 38)
VOSK_MODEL_DIR = _p("models", "vosk-model-small-en-us-0.15")
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MIC_DEVICE = "auto"            # auto = the I2S mic if present, else the default input
MIC_CHANNEL = 0                # INMP441 with L/R tied to GND sends on the left channel
MIC_GAIN = None                # None = auto (I2S_MIC_GAIN for the INMP441, 1 for other mics)
I2S_MIC_GAIN = 16.0            # raise if it hears nothing, lower if distorted (pi/test_mic.sh)

# --- Speech: ElevenLabs voice cached on the device, local voice as backup ----------
TTS_BACKEND = "auto"           # auto (espeak-ng on the Pi, Windows voice on a laptop) | print
ESPEAK_SPEED = 170
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "") or "JBFqnCBsd6RMkjVDRZzb"
ELEVENLABS_MODEL = "eleven_flash_v2_5"
VOICE_CACHE_DIR = _p("voices", "cache")
# False: ElevenLabs only for the fixed sentences (recorded once by tools/prewarm_voices.py);
# Claude's new sentences use the local voice. True: record those too (natural voice, but the free
# plan's 10,000 characters a month run out quickly).
CLOUD_VOICE_NEW_SENTENCES = False
CLOUD_VOICE_TIMEOUT_S = 4
