"""Frame sources: Pi Camera (picamera2), a webcam index, a phone stream or a video file."""

import re
import threading

import config


class PiCamera:
    def __init__(self):
        from libcamera import Transform
        from picamera2 import Picamera2

        self.cam = Picamera2()
        # Keep the sensor's own shape (Camera Module 3 is 16:9): asking for 4:3 would crop the sides.
        sw, sh = self.cam.sensor_resolution
        w = config.FRAME_SIZE[0]
        size = (w, round(w * sh / sw / 2) * 2)
        # "RGB888" in picamera2 is BGR byte order in memory -- what OpenCV expects.
        # FrameDurationLimits caps the exposure, so walking doesn't blur the picture.
        cfg = self.cam.create_video_configuration(
            main={"size": size, "format": "RGB888"},
            transform=Transform(hflip=1, vflip=1) if config.PICAM_ROTATE_180 else Transform(),
            controls={"FrameDurationLimits": (config.PICAM_FRAME_US, config.PICAM_FRAME_US)})
        self.cam.configure(cfg)
        self.cam.start()
        if "AfMode" in self.cam.camera_controls:      # Camera Module 3: focus is fixed unless set
            try:
                from libcamera import controls

                self.cam.set_controls({"AfMode": controls.AfModeEnum.Continuous,
                                       "AfSpeed": controls.AfSpeedEnum.Fast})
            except Exception as exc:                    # never stop over focus
                print(f"[camera] autofocus not set: {exc}")

    def read(self):
        return self.cam.capture_array()

    def close(self):
        try:
            self.cam.stop()
            self.cam.close()
        except Exception:
            pass


class CvCamera:
    def __init__(self, source):
        import cv2

        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video source {source!r}")
        if isinstance(source, int):
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_SIZE[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_SIZE[1])

    def read(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def close(self):
        self.cap.release()


class StreamCamera(CvCamera):
    """Network stream (e.g. a phone with DroidCam): always the newest frame, no build-up of delay."""

    def __init__(self, url: str):
        super().__init__(url)
        self._frame = None
        self._ended = False
        self._cv = threading.Condition()
        threading.Thread(target=self._grab, daemon=True).start()

    def _grab(self):
        while True:
            ok, frame = self.cap.read()
            with self._cv:
                if ok:
                    self._frame = frame
                else:
                    self._ended = True
                self._cv.notify()
            if not ok:
                return

    def read(self):
        with self._cv:
            while self._frame is None and not self._ended:
                self._cv.wait()
            frame, self._frame = self._frame, None
            return frame


def is_live(source: str) -> bool:
    """A camera or stream (vs a video file, which simply ends)."""
    return source == "picam" or source.isdigit() or bool(re.match(r"(https?|rtsp|tcp|udp):", source))


def open_camera(source: str):
    if source == "picam":
        return PiCamera()
    source = re.sub(r"^(https?|rtsp|tcp|udp):/{0,2}(?!/)", r"\1://", source)
    if "://" in source:
        return StreamCamera(source)
    return CvCamera(int(source) if source.isdigit() else source)
