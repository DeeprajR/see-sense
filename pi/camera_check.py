"""See what the camera sees, and optionally ask Claude about it.

    python pi/camera_check.py                                # Pi Camera: picture + focus/brightness
    python pi/camera_check.py --ask "where is the door?"     # ...and Claude's answer
    python pi/camera_check.py --source 0                     # a webcam (laptop)

Saves camera_check.jpg in the wayfinder folder. Copy it to the laptop to look at it:
    scp <user>@<PI_IP>:~/wayfinder/camera_check.jpg .
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import cv2  # noqa: E402

import config  # noqa: E402
from camera import open_camera  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="picam")
    ap.add_argument("--ask", help="also ask Claude this about the picture")
    args = ap.parse_args()

    cam = open_camera(args.source)
    frame = None
    for _ in range(30):                     # let exposure, white balance and focus settle
        f = cam.read()
        frame = f if f is not None else frame
    t = time.perf_counter()
    for _ in range(20):
        f = cam.read()
        frame = f if f is not None else frame
    fps = 20 / (time.perf_counter() - t)
    cam.close()
    if frame is None:
        sys.exit("No picture from the camera.")
    frame = frame[..., :3]

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharp = cv2.Laplacian(gray, cv2.CV_64F).var()
    h, w = frame.shape[:2]
    print(f"Picture: {w}x{h}, camera {fps:.0f} fps")
    print(f"Focus (sharpness): {sharp:.0f}   " + ("OK" if sharp >= 80 else
          "LOW: blurry. Check the lens film is removed and autofocus works (Camera Module 3)"))
    print(f"Brightness: {gray.mean():.0f} / 255   " + ("OK" if 60 <= gray.mean() <= 200 else
          "too dark" if gray.mean() < 60 else "too bright"))
    out = os.path.join(config.HERE, "camera_check.jpg")
    cv2.imwrite(out, frame)
    print(f"Saved {out}")
    print("Is it upside down? Set PICAM_ROTATE_180 = True in config.py.")

    if args.ask:
        from planner import Planner, PlannerError

        p = Planner()
        p.begin(args.ask, 0)
        try:
            turn = p.think(frame, 0, None)
            print(f"\nClaude ({turn.action}): {turn.say}")
            for s in turn.steps[1:]:
                print(f"  then: {s}")
        except PlannerError as exc:
            print(f"\nClaude: {exc}")


if __name__ == "__main__":
    main()
