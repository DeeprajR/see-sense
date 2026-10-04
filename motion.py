"""How far the wearer has turned, measured from the camera image alone (no compass/IMU).

When the camera turns, the whole picture slides sideways. Phase correlation between
consecutive small grey frames gives that slide in pixels; pixels -> degrees via the
camera's field of view. Used to guide "turn right about 60 degrees" and to tell Claude how far
the wearer really turned.
"""

import config

SIZE = (160, 120)


class YawEstimator:
    def __init__(self, hfov: float = config.CAMERA_HFOV_DEG):
        self.deg_per_px = hfov / SIZE[0]
        self.yaw = 0.0          # degrees since start; positive = turned to the right
        self.rate = 0.0         # degrees per second (recent)
        self._prev = None
        self._prev_t = None
        self._window = None

    def update(self, frame, now: float) -> float:
        import cv2
        import numpy as np

        g = cv2.cvtColor(cv2.resize(frame, SIZE), cv2.COLOR_BGR2GRAY).astype(np.float32)
        if self._prev is None:
            self._prev, self._prev_t = g, now
            return self.yaw
        if self._window is None:
            self._window = cv2.createHanningWindow(SIZE, cv2.CV_32F)
        (dx, _dy), response = cv2.phaseCorrelate(self._prev, g, self._window)
        dt = max(now - self._prev_t, 1e-3)
        self._prev, self._prev_t = g, now
        if response < config.YAW_MIN_RESPONSE:      # blurred / blank / mostly moving things
            return self.yaw
        # Turning right makes the scene slide left (negative dx).
        step = -dx * self.deg_per_px
        self.yaw += step
        self.rate = 0.7 * self.rate + 0.3 * (step / dt)
        return self.yaw
