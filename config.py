"""Settings for SENSE Wayfinder: hold the button, say where you want to go, get guided there."""

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

# --- Camera (Pi Camera 3 on the chest) ------------------------------------------
FRAME_SIZE = (1280, 720)       # webcams; the Pi Camera keeps width 1280 at its own shape (16:9)
PICAM_ROTATE_180 = False       # True if the camera is mounted upside down (check: pi/camera_check.py)
PICAM_FRAME_US = 33333         # 30 fps; also the longest exposure, so walking doesn't blur
CAMERA_HFOV_DEG = 66           # Pi Camera 3: 66, Pi Camera 3 Wide: 102
CAMERA_MOUNT = "chest"         # chest | head: "turn your body" vs "turn your head"
YAW_MIN_RESPONSE = 0.05        # turn measurement skips frames it can't match (blur, blank)

# --- Claude: sees the camera picture and plans the route ----------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_WORKSPACE_ID = os.environ.get("ANTHROPIC_WORKSPACE_ID", "")  # needed if the key isn't workspace-scoped
CLAUDE_MODEL = "claude-sonnet-5-5"   # later: "claude-opus-5-5" (more accurate, slower, costlier)
CLAUDE_EFFORT = "medium"
CLAUDE_TIMEOUT_S = 25
CLAUDE_MAX_IMAGE_SIDE = 1280   # larger pictures are scaled down
CLAUDE_KEEP_IMAGES = 3         # only the latest pictures are re-sent (a survey: left, ahead, right)
MAX_LOOKS = 6                  # survey looks (turn / tilt / step aside) at most this many per request
RECHECK_EVERY_STEPS = 2        # after this many steps, take a new picture and update the route
OFFLINE_RETRY_S = 30           # after a network failure, wait this long before trying again

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
# BCM pins. Not 18/19/20: those are the INMP441 microphone's I2S pins.
MOTOR_PINS = {"left": 12, "front_left": 13, "front_right": 16, "right": 26}
HAPTICS_BACKEND = "auto"       # auto (gpio on a Pi, else sim) | gpio | sim | off
HAPTIC_INTENSITY = 1.0         # 0-1 PWM duty

# --- Button (GPIO17 to GND) ---------------------------------------------------------
BUTTON_PIN = 17                # hold = speak (release to send); short press = next step
PTT_HOLD_S = 0.4               # held this long = speaking (shorter = a press)
PTT_MAX_S = 12                 # stop recording after this long even if still held

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
CLOUD_VOICE_TIMEOUT_S = 4
