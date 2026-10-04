"""Draw the SEE SENSE architecture diagram for the pitch deck.

    python docs/make_architecture.py      # -> docs/architecture.png (for slides) and .svg

Only what runs today: the wearer's hardware, the Raspberry Pi software and the cloud services.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

ZONES = {  # name: (x, width, fill, edge, title)
    "wearer": (0.25, 3.3, "#FFF4E5", "#E8A33D", "WEARER (and a helper)"),
    "pi": (3.8, 6.55, "#EAF6EC", "#4CAF50", "RASPBERRY PI 5 (on the device)"),
    "cloud": (11.65, 4.1, "#E8F1FB", "#3D7DD8", "CLOUD (internet)"),
}
INK = "#1F2933"
MUTED = "#52606D"
ORANGE, GREEN, BLUE = "#E8A33D", "#4CAF50", "#3D7DD8"


def zone(ax, key):
    x, w, fill, edge, title = ZONES[key]
    ax.add_patch(FancyBboxPatch((x, 0.35), w, 7.55, boxstyle="round,pad=0.02,rounding_size=0.25",
                                fc=fill, ec=edge, lw=2))
    ax.text(x + w / 2, 7.62, title, ha="center", va="center", fontsize=13, weight="bold", color=edge)


def box(ax, x, y, w, h, title, sub="", edge=GREEN, fill="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fill, ec=edge, lw=1.8))
    if sub:
        ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=11.5, weight="bold", color=INK)
        ax.text(x + w / 2, y + h - 0.55, sub, ha="center", va="top", fontsize=9.2, color=MUTED, linespacing=1.35)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=11.5, weight="bold", color=INK)
    return (x, y, w, h)


def side(b, where):
    x, y, w, h = b
    return {"l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}[where]


def arrow(ax, a, b, color=INK, both=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if both else "-|>", mutation_scale=15,
                                 lw=1.7, color=color, shrinkA=3, shrinkB=3, zorder=3))


def label(ax, x, y, text, color, va="bottom"):
    ax.text(x, y, text, ha="center", va=va, fontsize=8.8, color=color, linespacing=1.2, zorder=4,
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))


def badge(ax, x, y, n):
    ax.text(x, y, str(n), ha="center", va="center", fontsize=9, weight="bold", color="white", zorder=5,
            bbox=dict(boxstyle="circle,pad=0.2", fc=ORANGE, ec="none"))


def main():
    fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(0.3, 8.55, "SEE SENSE: how it works", fontsize=20, weight="bold", color=INK, va="center")
    ax.text(15.7, 8.55, "Hold the button · say where · get guided there", fontsize=12, color=MUTED,
            ha="right", va="center", style="italic")
    for k in ZONES:
        zone(ax, k)

    # Wearer (and a helper)
    button = box(ax, 0.5, 6.35, 2.8, 0.95, "Push button", "hold = speak · press = next step", ORANGE)
    mic = box(ax, 0.5, 5.15, 2.8, 0.9, "INMP441 microphone", "records while held", ORANGE)
    box(ax, 0.5, 3.15, 2.8, 1.6, "Pi Camera 3", "on the head\nautofocus, 30 fps", ORANGE)
    browser = box(ax, 0.5, 1.6, 2.8, 0.85, "Helper's phone / laptop", "live view in a browser", ORANGE, "#FFFBF5")
    ears = box(ax, 0.5, 0.55, 2.8, 0.85, "Bluetooth earbuds", "every instruction", ORANGE)

    # Raspberry Pi
    vosk = box(ax, 4.05, 5.1, 2.35, 1.0, "Vosk", "offline speech-to-text", GREEN)
    turn = box(ax, 4.05, 3.15, 2.35, 1.15, "Turn measurement", "OpenCV, frame to frame\n(~1° accuracy)", GREEN)
    live = box(ax, 4.05, 1.6, 2.35, 0.85, "Live view server", "port 8000 (--stream)", GREEN, "#F6FBF7")
    loop = box(ax, 7.0, 3.15, 3.1, 3.4, "Guide loop",
               "request → survey →\nnearest goal → walkway →\nsteps (button = next)\n\n"
               "\"Keep turning right\" …\n\"OK, stop.\"\n\nnew photo every 2 steps", GREEN)
    speech = box(ax, 7.0, 0.55, 3.1, 1.15, "Speech", "ElevenLabs voice cached on the Pi\nespeak-ng backup", GREEN)

    # Cloud
    box(ax, 11.85, 5.4, 3.7, 1.5, "JEV (TypeSafe) · 0.3 s",
        "A: request, command or misheard?\nB: which things need a warning?", BLUE)
    box(ax, 11.85, 2.85, 3.7, 2.05, "Claude Sonnet 5.5",
        "sees the photo · surveys · picks the\nnearest door · traces the walkway ·\n"
        "handles blockers · plans steps\n→ look / ask / plan / arrived", BLUE)
    eleven = box(ax, 11.85, 0.55, 3.7, 1.15, "ElevenLabs", "records new sentences", BLUE)

    # Wearer -> Pi
    arrow(ax, side(button, "r"), (7.0, 6.3), ORANGE)
    label(ax, 5.2, 6.62, "hold / press", ORANGE)
    badge(ax, 3.75, 6.98, 1)
    arrow(ax, side(mic, "r"), (4.05, 5.6), ORANGE)
    label(ax, 3.68, 5.66, "voice", ORANGE)
    arrow(ax, side(vosk, "r"), (7.0, 5.6), GREEN)
    label(ax, 6.7, 5.66, "text", GREEN)
    badge(ax, 6.7, 6.15, 2)
    arrow(ax, (3.3, 4.55), (7.0, 4.55), ORANGE)
    label(ax, 5.3, 4.6, "photo", ORANGE)
    arrow(ax, (3.3, 3.7), (4.05, 3.7), ORANGE)
    label(ax, 3.68, 3.76, "frames", ORANGE)
    arrow(ax, side(turn, "r"), (7.0, 3.72), GREEN)
    label(ax, 6.78, 3.8, "degrees\nturned", GREEN)

    # Pi <-> cloud
    arrow(ax, (10.1, 6.15), (11.85, 6.15), BLUE, both=True)
    label(ax, 10.97, 6.22, "what was heard\n→ verdict", BLUE)
    badge(ax, 10.97, 5.85, 3)
    arrow(ax, (10.1, 4.35), (11.85, 4.35), BLUE)
    label(ax, 10.97, 4.42, "photo + request\n+ turn", BLUE)
    arrow(ax, (11.85, 3.5), (10.1, 3.5), BLUE)
    label(ax, 10.97, 3.42, "next action\n+ things seen", BLUE, va="top")
    badge(ax, 10.97, 4.05, 4)
    arrow(ax, (13.7, 4.9), (13.7, 5.4), BLUE)
    ax.text(13.85, 5.15, "things seen", ha="left", va="center", fontsize=8.8, color=BLUE)
    arrow(ax, side(speech, "r"), side(eleven, "l"), BLUE, both=True)
    label(ax, 10.97, 1.2, "new sentence\n→ audio", BLUE)

    # Pi -> wearer and helper
    arrow(ax, side(loop, "b"), side(speech, "t"), GREEN)
    label(ax, 9.1, 2.3, "what to say", GREEN)
    badge(ax, 8.25, 2.42, 5)
    arrow(ax, (7.0, 0.97), side(ears, "r"), GREEN)
    label(ax, 5.3, 1.03, "audio", GREEN)
    arrow(ax, (7.2, 3.15), side(live, "r"), GREEN)
    label(ax, 6.95, 2.5, "picture +\nstatus", GREEN)
    arrow(ax, side(live, "l"), side(browser, "r"), GREEN)

    # Legend
    ax.text(0.3, 0.12, "1 hold the button and speak  ·  2 Vosk turns it into text on the Pi  ·  "
            "3 JEV checks what was heard  ·  4 Claude sees the photo and decides the next action  ·  "
            "5 spoken in the earbuds", fontsize=9.5, color=MUTED, va="center")

    for ext in ("png", "svg"):
        fig.savefig(os.path.join(HERE, f"architecture.{ext}"), bbox_inches="tight", facecolor="white")
    print("saved docs/architecture.png and docs/architecture.svg")


if __name__ == "__main__":
    main()
