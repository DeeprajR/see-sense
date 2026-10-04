"""Build the folder to copy to the Raspberry Pi: exactly what SEE SENSE needs there.

    python tools/make_pi_upload.py              # -> dist/seesense/  (not committed)
    python tools/make_pi_upload.py --no-env     # leave the API keys (.env) out

The folder is rebuilt from scratch every run, so edit the files here, never in dist/.
Left out: tests, these tools, caches.
"""

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(APP, "dist", "seesense")

MODULES = ["main.py", "config.py", "camera.py", "controls.py", "distance.py", "haptics.py",
           "jev.py", "liveview.py", "motion.py", "planner.py", "speech.py", "voice.py", "voices.py"]
FOLDERS = ["pi", "voices/cache"]
OPTIONAL = ["models/vosk-model-small-en-us-0.15"]    # setup_pi.sh downloads it if missing
SKIP = ("__pycache__", ".pyc", "camera_check.jpg")


def copy(rel: str, sizes: dict):
    src = os.path.join(APP, rel)
    if os.path.isdir(src):
        for name in sorted(os.listdir(src)):
            if not name.endswith(SKIP):
                copy(os.path.join(rel, name), sizes)
        return
    out = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copy2(src, out)
    group = rel.replace(os.sep, "/").split("/")[0]
    if group.endswith(".py") or group == ".env":
        group = "app code + .env"
    sizes[group] = sizes.get(group, 0) + os.path.getsize(src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-env", action="store_true", help="don't include .env (API keys)")
    args = ap.parse_args()

    missing = [f for f in MODULES + FOLDERS if not os.path.exists(os.path.join(APP, f))]
    if missing:
        sys.exit("Missing:\n  " + "\n  ".join(missing))
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)                         # rebuilt every time: no stale files

    with_env = not args.no_env and os.path.exists(os.path.join(APP, ".env"))
    extra = [f for f in OPTIONAL if os.path.exists(os.path.join(APP, f))]
    sizes: dict = {}
    for rel in MODULES + FOLDERS + extra + ([".env"] if with_env else []):
        copy(rel, sizes)

    files = sum(len(f) for _, _, f in os.walk(OUT))
    print(f"Upload folder: {OUT}")
    print(f"  {files} files, {sum(sizes.values()) / 1e6:.0f} MB")
    for name, size in sorted(sizes.items(), key=lambda x: -x[1]):
        print(f"  {size / 1e6:7.1f} MB  {name}")
    if not extra:
        print("  (no speech model: setup_pi.sh downloads it)")
    if with_env:
        print("  includes .env with your API keys: keep this folder private")
    print("\nCopy to the Pi, then set it up once:\n"
          f"  scp -r \"{OUT}\" <user>@<PI_IP>:~/\n"
          "  ssh <user>@<PI_IP> \"cd seesense && bash pi/setup_pi.sh\"")


if __name__ == "__main__":
    main()
