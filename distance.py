"""Real distance straight ahead from a time-of-flight sensor on I2C (address 0x29).

Detects which chip is connected from its model ID:
  * VL53L1X -- up to ~4 m (Pimoroni driver: pip install vl53l1x)
  * VL53L0X -- up to ~2 m (Adafruit driver: pip install adafruit-circuitpython-vl53l0x)
Mount it next to the camera, pointing forward. It catches walls, poles and glass doors, with no
AI and no internet. Without a sensor this module does nothing.
Check the wiring and chip with:  python pi/test_tof.py
"""

from collections import deque
import statistics
import threading
import time

import config

ADDRESS = 0x29
MAX_RANGE_M = {"vl53l1x": 4.0, "vl53l0x": 2.0}


def detect_tof(bus_no: int = 1, address: int = ADDRESS) -> str | None:
    """"vl53l0x" / "vl53l1x" / "unknown" (something at 0x29) / None (nothing found).

    VL53L0X keeps its model ID 0xEE at 8-bit register 0xC0; VL53L1X keeps 0xEA at 16-bit
    register 0x010F. The 8-bit check runs first: it only reads, so it's harmless on either chip."""
    from smbus2 import SMBus, i2c_msg

    with SMBus(bus_no) as bus:
        try:
            if bus.read_byte_data(address, 0xC0) == 0xEE:
                return "vl53l0x"
        except OSError:
            return None                      # no device answering at 0x29
        try:
            write, read = i2c_msg.write(address, [0x01, 0x0F]), i2c_msg.read(address, 1)
            bus.i2c_rdwr(write, read)
            if list(read)[0] == 0xEA:
                return "vl53l1x"
        except OSError:
            pass
    return "unknown"


class DistanceSensor:
    def __init__(self, backend: str = config.DISTANCE_BACKEND):
        self.available = False
        self.model: str | None = None
        self._readings: deque = deque(maxlen=3)
        self._time = 0.0
        if backend == "off":
            return
        try:
            model = detect_tof() if backend == "auto" else backend
        except Exception:                      # no I2C bus (e.g. a laptop)
            return
        if model is None:
            return
        try:
            if model == "vl53l1x":
                import VL53L1X

                tof = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=ADDRESS)
                tof.open()
                tof.start_ranging(3)               # 3 = long range mode
                self._read_mm = tof.get_distance
            elif model == "vl53l0x":
                import adafruit_vl53l0x
                import board
                import busio

                tof = adafruit_vl53l0x.VL53L0X(busio.I2C(board.SCL, board.SDA))
                tof.measurement_timing_budget = 33000  # ~30 readings/s
                self._read_mm = lambda: tof.range
            else:
                print(f"[distance] a device answers at 0x{ADDRESS:02x} but isn't a VL53L0X/VL53L1X")
                return
        except Exception as exc:
            print(f"[distance] {model} found but couldn't start: {exc}")
            return
        self.model = model
        self.available = True
        print(f"[distance] {model.upper()} ready (up to {MAX_RANGE_M[model]:g} m)")
        threading.Thread(target=self._poll, daemon=True).start()

    def _poll(self):
        limit = MAX_RANGE_M[self.model] * 1000
        while True:
            try:
                mm = self._read_mm()
            except Exception:
                mm = 0
            if 0 < mm <= limit:
                self._readings.append(mm / 1000)
                self._time = time.monotonic()
            time.sleep(0.05)

    def read(self) -> float | None:
        """Median of the last few readings in metres, or None (no sensor / nothing in range)."""
        if not self.available or not self._readings or time.monotonic() - self._time > 0.5:
            return None
        return statistics.median(self._readings)
