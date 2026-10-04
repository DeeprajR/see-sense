"""Check the time-of-flight distance sensor: which chip it is, and live readings.

    python pi/test_tof.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from distance import DistanceSensor, detect_tof  # noqa: E402

try:
    model = detect_tof()
except Exception as exc:
    sys.exit(f"!! No I2C bus ({exc}). Run setup_pi.sh (it enables I2C), then reboot.")
if model is None:
    sys.exit("!! Nothing at address 0x29. Check wiring: VIN->3.3V, GND->GND, SDA->GPIO2 (pin 3), "
             "SCL->GPIO3 (pin 5). Also try: i2cdetect -y 1")
print(f"Chip: {model.upper()}")
s = DistanceSensor("auto")
if not s.available:
    sys.exit("!! Found the chip but the driver didn't start (see the message above).")
print("Point it at a wall and move closer/further (Ctrl+C to stop):")
while True:
    d = s.read()
    print(f"  {d:.2f} m" if d is not None else "  (nothing in range)")
    time.sleep(0.5)
