"""Is the device online? Says when the internet is lost and when it's back, and tries to reconnect.

Every NET_CHECK_EVERY_S seconds it opens a connection to Claude's server (no API call, no cost).
After NET_FAILS_TO_DROP failures in a row it reports "offline" (one slow check isn't enough), and
while offline it asks the Pi's network manager to reconnect the Wi-Fi every RECONNECT_EVERY_S.
"""

import shutil
import socket
import subprocess
import threading
import time

import config


def can_reach(host: str = config.NET_CHECK_HOST, port: int = 443, timeout: float = 3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def reconnect_wifi() -> bool:
    """Ask NetworkManager (Raspberry Pi OS) to bring the Wi-Fi back. False if it can't."""
    if not shutil.which("nmcli"):
        return False
    for prefix in ([], ["sudo", "-n"]):                # as the user first, then without a password prompt
        try:
            subprocess.run(prefix + ["nmcli", "device", "wifi", "rescan"], capture_output=True, timeout=20)
            done = subprocess.run(prefix + ["nmcli", "device", "connect", config.WIFI_INTERFACE],
                                  capture_output=True, timeout=30)
            if done.returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass
    return False


class Network:
    def __init__(self, on_change, check=can_reach, reconnect=reconnect_wifi, start: bool = True):
        self.on_change = on_change          # on_change(online: bool)
        self.check, self.reconnect = check, reconnect
        self.online: bool | None = None     # None until the first check
        self._fails = 0
        self._offline_since = 0.0
        self._last_reconnect = 0.0
        if start:
            threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            self.tick(time.monotonic())
            time.sleep(config.NET_CHECK_EVERY_S)

    def tick(self, now: float):
        """One check (the background thread calls this; tests call it directly)."""
        if self.check():
            self._fails = 0
            if self.online is not True:
                self.online = True
                self.on_change(True)
            return
        self._fails += 1
        if self.online is not False and (self._fails >= config.NET_FAILS_TO_DROP or self.online is None):
            self.online = False
            self._offline_since = now
            self.on_change(False)
        if self.online is False and now - self._last_reconnect >= config.RECONNECT_EVERY_S:
            self._last_reconnect = now
            ok = self.reconnect()
            print(f"[net] offline: reconnecting the Wi-Fi {'requested' if ok else 'not possible here'}")
