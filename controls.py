"""Input -> actions on a queue the main loop reads.

  * Button (GPIO17 to GND): hold = speak (release to send); short press = next step
  * Preview window keys:    v = talk (v again to send), n/space = next step, l = look again,
                            r = repeat, s = stop, q = quit
  * Terminal (laptop tests): type a request ("take me to the door") and press Enter
"""

import queue
import sys
import threading

import config

HELP = ("Keys in the preview window: v = talk (v again to send), n/space = next step, l = look again, "
        "r = repeat, s = stop, q = quit.  Or type a request here and press Enter.")


class Controls:
    def __init__(self, use_terminal: bool = True):
        self.actions: queue.Queue = queue.Queue()
        self.button = None
        self._setup_button()
        if use_terminal and sys.stdin is not None and sys.stdin.isatty():
            threading.Thread(target=self._terminal, daemon=True).start()

    def _setup_button(self):
        try:
            from gpiozero import Button

            b = Button(config.BUTTON_PIN, hold_time=config.PTT_HOLD_S)
        except Exception:
            return      # not on a Pi, or no gpiozero: keyboard only
        held = {"flag": False}

        def on_held():                       # hold: talk (like a walkie-talkie)
            held["flag"] = True
            self.actions.put(("ptt_start",))

        def on_released():
            self.actions.put(("ptt_stop",) if held["flag"] else ("next",))
            held["flag"] = False

        b.when_held = on_held
        b.when_released = on_released
        self.button = b
        print(f"[controls] button on GPIO {config.BUTTON_PIN}: hold = speak, press = next step")

    def _terminal(self):
        for line in sys.stdin:
            if line.strip():
                self.actions.put(("text", line.strip()))
        # EOF (e.g. running as a service): just stop reading.

    def key(self, k: int):
        """Feed a cv2.waitKey() code from the preview window."""
        if k < 0:
            return
        c = chr(k & 0xFF).lower()
        action = {"v": "ptt_toggle", "n": "next", " ": "next", "l": "look", "r": "repeat",
                  "s": "stop", "q": "quit"}.get(c)
        if k == 27:
            action = "quit"
        if action:
            self.actions.put((action,))

    def poll(self) -> list:
        """All actions queued since the last call."""
        out = []
        while True:
            try:
                out.append(self.actions.get_nowait())
            except queue.Empty:
                return out
