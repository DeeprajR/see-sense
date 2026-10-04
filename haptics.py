"""4 vibration motors across the body (left | front_left | front_right | right).

  turn      slow pulses on the left or right motor   -> keep turning that way
  obstacle  long buzz on both front motors           -> something close ahead (distance sensor)
  stop      fast pulses on both front motors         -> very close: stop
  notice    one short pulse on one side              -> something worth knowing on that side
  ready / arrived / listening                        -> short confirmations on all motors

On a Pi the motors are driven through transistors on GPIO PWM pins. Anywhere else a simulator
keeps the state so the preview window can draw it.
"""

import threading
import time

import config

# (on_seconds, off_seconds) pulses
PATTERNS = {
    "stop":      [(0.08, 0.06)] * 6,
    "obstacle":  [(0.5, 0.0)],
    "turn":      [(0.25, 0.25), (0.25, 0.0)],
    "arrived":   [(0.15, 0.10), (0.15, 0.10), (0.5, 0.0)],
    "ready":     [(0.10, 0.10)],
    "listening": [(0.06, 0.0)],
    "notice":    [(0.15, 0.0)],
}
RANK = {"stop": 3, "obstacle": 2, "arrived": 2, "turn": 1, "notice": 1, "ready": 0, "listening": 0}
WHERE = {
    "left": ["left"],
    "right": ["right"],
    "ahead": ["front_left", "front_right"],
    "all": list(config.MOTORS),
}


def _on_a_pi() -> bool:
    try:
        with open("/proc/device-tree/model") as f:
            return "Raspberry Pi" in f.read()
    except OSError:
        return False


class SimMotors:
    name = "sim"

    def __init__(self):
        self.state = {m: 0.0 for m in config.MOTORS}

    def set(self, motor: str, value: float):
        self.state[motor] = value


class GpioMotors:
    name = "gpio"

    def __init__(self):
        from gpiozero import PWMOutputDevice

        self.devs = {}
        for m in config.MOTORS:                 # one unusable pin mustn't turn off the others
            try:
                self.devs[m] = PWMOutputDevice(config.MOTOR_PINS[m], frequency=1000)
            except Exception as exc:
                print(f"[haptics] {m} motor on GPIO{config.MOTOR_PINS[m]} unavailable: {exc}")
        if not self.devs:
            raise RuntimeError("no motor pin available")
        self.state = {m: 0.0 for m in config.MOTORS}

    def set(self, motor: str, value: float):
        if motor in self.devs:
            self.devs[motor].value = value
        self.state[motor] = value


class Haptics:
    def __init__(self, backend: str = config.HAPTICS_BACKEND):
        if backend == "auto":
            backend = "gpio" if _on_a_pi() else "sim"
        self.enabled = backend != "off"
        self.motors = None
        if backend == "gpio":
            try:
                self.motors = GpioMotors()
            except Exception as exc:
                print(f"[haptics] GPIO unavailable ({exc}); simulating")
        if self.motors is None:
            self.motors = SimMotors()
        self.name = self.motors.name if self.enabled else "off"
        self._lock = threading.Lock()
        # Per motor: (generation, rank, busy_until). A newer pattern takes over a motor
        # unless a more urgent one is still playing there.
        self._owner = {m: (0, -1, 0.0) for m in config.MOTORS}

    @property
    def state(self) -> dict[str, float]:
        return self.motors.state

    def play(self, pattern: str, where: str = "all"):
        if not self.enabled:
            return
        steps, rank = PATTERNS[pattern], RANK[pattern]
        now = time.monotonic()
        duration = sum(on + off for on, off in steps)
        with self._lock:
            mine = []
            for m in WHERE[where]:
                gen, r, until = self._owner[m]
                if now < until and r > rank:
                    continue          # don't interrupt something more urgent
                self._owner[m] = (gen + 1, rank, now + duration)
                mine.append((m, gen + 1))
        if mine:
            threading.Thread(target=self._run, args=(mine, steps), daemon=True).start()

    def _run(self, mine: list[tuple[str, int]], steps):
        for on, off in steps:
            live = [(m, g) for m, g in mine if self._owner[m][0] == g]
            if not live:
                return
            for m, _ in live:
                self.motors.set(m, config.HAPTIC_INTENSITY)
            time.sleep(on)
            for m, g in live:
                if self._owner[m][0] == g:
                    self.motors.set(m, 0.0)
            time.sleep(off)

    def off(self):
        for m in config.MOTORS:
            self.motors.set(m, 0.0)
