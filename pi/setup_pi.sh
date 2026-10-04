#!/usr/bin/env bash
# One-time setup of SENSE Wayfinder on a Raspberry Pi 5 (Raspberry Pi OS Bookworm, 64-bit).
#
#   cd ~/wayfinder && bash pi/setup_pi.sh
#
# Safe to re-run: every step skips work that is already done. Installs only what Wayfinder uses:
# no AI models on the Pi (Claude does the seeing), so no PyTorch or YOLO.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"
step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

if [[ "$(uname -m)" != "aarch64" ]]; then
    echo "This script is for a 64-bit Raspberry Pi OS (aarch64). Found: $(uname -m)" >&2
    exit 1
fi

step "System packages"
# camera + OpenCV | Bluetooth earbuds | mic tools (arecord) | backup voice | sounddevice | motors + button | I2C check
sudo apt-get update
sudo apt-get install -y \
    python3-venv python3-picamera2 python3-opencv python3-numpy \
    pipewire-audio wireplumber libspa-0.2-bluetooth bluez \
    alsa-utils espeak-ng libportaudio2 \
    python3-gpiozero python3-lgpio i2c-tools

step "Enable the INMP441 I2S microphone and I2C (distance sensor)"
BOOTCFG=/boot/firmware/config.txt
reboot_needed=0
for line in "dtparam=i2s=on" "dtoverlay=googlevoicehat-soundcard" "dtparam=i2c_arm=on"; do
    if ! grep -qxF "$line" "$BOOTCFG"; then
        echo "$line" | sudo tee -a "$BOOTCFG" >/dev/null
        echo "added: $line"
        reboot_needed=1
    fi
done

step "Python packages (.venv, sharing the system's picamera2/OpenCV/gpiozero)"
if [[ ! -d .venv ]]; then
    python3 -m venv --system-site-packages .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install anthropic typesafe-sdk vosk sounddevice smbus2

step "Distance sensor driver (only the one for the chip that's connected)"
chip="$(python -c "from distance import detect_tof; print(detect_tof() or 'none')" 2>/dev/null || echo none)"
case "$chip" in
    vl53l1x) pip install vl53l1x && echo "VL53L1X found: driver installed" ;;
    vl53l0x) pip install adafruit-circuitpython-vl53l0x adafruit-blinka && echo "VL53L0X found: driver installed" ;;
    *)       echo "-- No distance sensor found (or I2C not enabled yet). Connect it, reboot, and run this again." ;;
esac

step "Offline speech model (Vosk, ~40 MB; the upload folder already has it)"
python -c "from voice import ensure_model; print(ensure_model())" \
    || echo "Download failed -- it will try again at first use"

step "Checks"
ok=1
python -c "import picamera2, cv2, anthropic, typesafe_sdk, vosk, sounddevice; print('python packages OK')" || {
    ok=0
    echo "!! Import failed. If the error mentions numpy, run:  source .venv/bin/activate && pip install 'numpy<2'"
}
if python -c "from picamera2 import Picamera2; import sys; sys.exit(0 if Picamera2.global_camera_info() else 1)" 2>/dev/null; then
    echo "camera OK"
else
    ok=0
    echo "!! No camera found. Check the ribbon cable (Pi 5 needs the 22-pin end in the CAM port)."
fi
if [[ ! -f .env ]] || ! grep -q "ANTHROPIC_API_KEY=." .env; then
    ok=0
    echo "!! No Claude key: put ANTHROPIC_API_KEY=... in $APP_DIR/.env (route planning is off until then)."
fi
if [[ ! -f .env ]] || ! grep -q "TYPESAFE_API_KEY=." .env; then
    echo "-- No JEV key (TYPESAFE_API_KEY in .env): optional; speech goes straight to Claude without it."
fi
if arecord -l 2>/dev/null | grep -qi "voicehat"; then
    echo "INMP441 microphone OK"
elif [[ $reboot_needed == 1 ]]; then
    echo "-- Microphone driver added: reboot, then run: bash pi/test_mic.sh"
else
    echo "!! INMP441 not found. Check wiring (see README.md), then: bash pi/test_mic.sh"
fi

echo
if [[ $ok == 1 ]]; then
    echo "Setup complete. Next:"
else
    echo "Setup finished with problems (see !! above). After fixing them:"
fi
[[ $reboot_needed == 1 ]] && echo "  0. Reboot (new mic/I2C settings), then run this script once more:  sudo reboot"
echo "  1. Pair the earbuds:   bash pi/pair_earbuds.sh"
echo "  2. Test the parts:     bash pi/test_mic.sh ; python pi/test_tof.py ; python pi/camera_check.py"
echo "  3. Test run:           source .venv/bin/activate && python main.py"
echo "  4. Start on boot:      bash pi/install_autostart.sh"
