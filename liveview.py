"""Live view: watch what the camera sees, and what SEE SENSE is doing, in a web browser.

    python main.py --stream             then open  http://<PI_IP>:8000  on a laptop or phone
                                        (same Wi-Fi as the Pi)

The picture shows how far the wearer has turned, the goal and step, the distance ahead, the
4 motors (filled = vibrating), the last thing said and what Claude saw. Python's built-in web
server only: no extra package. Pictures are only prepared while someone is watching, so it costs
nothing otherwise. Anyone on the same network can open it: use it on a private network only.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time

import config

PAGE = b"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>SEE SENSE live view</title>
<style>body{margin:0;background:#111;color:#eee;font:16px system-ui,sans-serif;text-align:center}
img{width:100%;max-width:1024px;display:block;margin:0 auto}p{margin:8px}</style></head>
<body><img src="/stream" alt="Live camera view from SEE SENSE"><p>SEE SENSE: live camera view</p>
</body></html>"""


class LiveView:
    def __init__(self, port: int = config.LIVE_VIEW_PORT):
        self._jpeg: bytes | None = None
        self._cv = threading.Condition()
        self._last = 0.0
        self.viewers = 0
        view = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):          # keep the terminal quiet
                pass

            def do_GET(self):
                if self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(PAGE)
                elif self.path == "/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    view.viewers += 1
                    try:
                        while True:
                            jpeg = view.wait_frame()
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                             + f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                                             + jpeg + b"\r\n")
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass                       # the browser closed the page
                    finally:
                        view.viewers -= 1
                else:
                    self.send_error(404)

        self.server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        print(f"[live view] open http://<this Pi's IP>:{port} in a browser on the same Wi-Fi "
              f"(find the IP with: hostname -I)")

    def wait_frame(self) -> bytes:
        with self._cv:
            self._cv.wait(timeout=2)
            if self._jpeg is None:
                raise OSError("no picture yet")
            return self._jpeg

    def update(self, frame, draw):
        """Called every camera frame; prepares a picture only if someone is watching (and at
        most LIVE_VIEW_FPS times a second). draw(img) adds the overlay."""
        now = time.monotonic()
        if not self.viewers or now - self._last < 1 / config.LIVE_VIEW_FPS:
            return
        self._last = now
        import cv2

        h, w = frame.shape[:2]
        width = config.LIVE_VIEW_WIDTH
        img = cv2.resize(frame, (width, int(h * width / w)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", draw(img), [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            with self._cv:
                self._jpeg = buf.tobytes()
                self._cv.notify_all()
