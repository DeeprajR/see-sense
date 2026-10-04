#!/usr/bin/env bash
# Check the INMP441 microphone: record 4 s, play it back in the earbuds, show the level.
#
#   bash pi/test_mic.sh
set -uo pipefail

echo "Capture devices:"
arecord -l
CARD="$(arecord -l | sed -n 's/^card \([0-9]*\):.*voicehat.*/\1/Ip' | head -1)"
if [[ -z "$CARD" ]]; then
    echo "!! INMP441 (googlevoicehat) not listed. Check:"
    echo "   - /boot/firmware/config.txt has: dtparam=i2s=on  and  dtoverlay=googlevoicehat-soundcard"
    echo "   - wiring: VDD->3.3V, GND->GND, L/R->GND, SCK->GPIO18, WS->GPIO19, SD->GPIO20"
    echo "   - you rebooted after setup_pi.sh"
    exit 1
fi

echo
echo "Speak now for 4 seconds..."
arecord -D "plughw:${CARD},0" -c 2 -r 48000 -f S32_LE -d 4 /tmp/mic_test.wav -q
python3 - <<'EOF'
import wave, numpy as np
with wave.open("/tmp/mic_test.wav") as w:
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int32).reshape(-1, 2)
for ch, name in ((0, "left"), (1, "right")):
    peak = np.abs(a[:, ch].astype(np.float64)).max() / 2**31
    print(f"{name:5} channel peak: {peak:.4f}" + ("   <- the mic" if peak > 0.001 else ""))
peak = np.abs(a.astype(np.float64)).max() / 2**31
if peak < 0.0005:
    print("!! Almost silent: check the SD wire (GPIO20) and that L/R is tied to GND or 3.3V.")
else:
    print(f"Suggested I2S_MIC_GAIN in config.py: about {min(64, max(1, round(0.3 / peak)))}")
EOF
echo "Playing it back (should be in the earbuds)..."
aplay -q /tmp/mic_test.wav
