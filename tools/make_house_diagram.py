"""Draw the model-house floor plan in English (SVG for the docs, PNG for Hackster).

usage: python tools/make_house_diagram.py
Writes docs/img/house_en.svg and docs/img/house_en.png.
Layout: rooms C | B | A from left to right, speaker and microphone in room A,
windows c, b, a on the bottom wall, doors BC and AB in the inner walls.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parents[1] / "docs" / "img"

GREEN, ORANGE, BLUE, RED, WALL = "#2b8a3e", "#e8590c", "#1c5fb8", "#b02a37", "#495057"
FILL = {"A": "#e3f4e1", "B": "#fdf1d6", "C": "#dde9f7"}
TEXT = {"A": GREEN, "B": ORANGE, "C": BLUE}


def callout(ax, x, y, w, h, num, text, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.18",
                                fc="white", ec=color, lw=2))
    ax.add_patch(Circle((x + 0.38, y + h - 0.38), 0.25, color=color))
    ax.text(x + 0.38, y + h - 0.38, str(num), color="white", ha="center", va="center",
            fontsize=13, fontweight="bold")
    ax.text(x + 0.75, y + h / 2, text, ha="left", va="center", fontsize=11.5, color="#212529",
            linespacing=1.35)


def arrow(ax, start, end, color, rad=0.0):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, lw=1.6,
                                 color=color, linestyle=(0, (4, 3)),
                                 connectionstyle=f"arc3,rad={rad}"))


def label(ax, x, y, text, color):
    ax.text(x, y, text, ha="center", va="center", fontsize=13, fontweight="bold", color=color,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, lw=1.6))


def main() -> None:
    fig, ax = plt.subplots(figsize=(14, 11))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 11)
    ax.set_aspect("equal")
    ax.axis("off")

    # ---------------- floor plan: C | B | A ----------------
    x0, y0, y1 = 1.9, 4.15, 8.95
    xs = [x0, 5.25, 8.25, 11.4]            # outer and inner wall positions
    for name, left, right in zip("CBA", xs[:-1], xs[1:]):
        ax.add_patch(Rectangle((left, y0), right - left, y1 - y0, fc=FILL[name], ec="none"))
    ax.add_patch(Rectangle((x0, y0), xs[-1] - x0, y1 - y0, fill=False, ec=WALL, lw=9))
    for x in xs[1:-1]:
        ax.plot([x, x], [y0, y1], color=WALL, lw=6)
    ax.text(3.55, 5.9, "Room C", ha="center", fontsize=22, fontweight="bold", color=TEXT["C"])
    ax.text(6.75, 5.9, "Room B", ha="center", fontsize=22, fontweight="bold", color=TEXT["B"])
    ax.text(9.95, 5.3, "Room A", ha="center", fontsize=22, fontweight="bold", color=TEXT["A"])

    # doors in the inner walls
    ax.add_patch(Rectangle((xs[1] - 0.11, 6.4), 0.22, 1.3, fc=RED, ec="#6d1a22", lw=1.2, zorder=4))
    ax.add_patch(Rectangle((xs[2] - 0.11, 4.9), 0.22, 1.3, fc=RED, ec="#6d1a22", lw=1.2, zorder=4))
    label(ax, 4.55, 6.9, "Door BC", RED)
    label(ax, 7.35, 5.35, "Door AB", RED)

    # windows in the bottom wall
    for cx, name, color in ((3.55, "c", BLUE), (6.75, "b", ORANGE), (9.95, "a", GREEN)):
        ax.add_patch(Rectangle((cx - 0.75, y0 - 0.14), 1.5, 0.28, fc="#a5d8ff", ec="#1864ab", lw=1.5,
                               zorder=4))
        ax.plot([cx, cx], [y0 - 0.14, y0 + 0.14], color="#1864ab", lw=1.2, zorder=5)
        label(ax, cx, y0 - 0.65, f"Window {name}", color)

    # speaker and microphone in room A
    ax.add_patch(FancyBboxPatch((10.15, 7.75), 0.62, 0.62, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="#343a40", ec="black", zorder=5))
    ax.add_patch(Circle((10.46, 8.06), 0.19, fc="#adb5bd", ec="white", lw=1.5, zorder=6))
    ax.text(10.46, 7.45, "Speaker", ha="center", fontsize=11.5, fontweight="bold")
    for r in (0.35, 0.55, 0.75):
        ax.add_patch(matplotlib.patches.Arc((10.1, 8.06), r, r * 1.5, theta1=120, theta2=240,
                                            color=BLUE, lw=2))
    ax.add_patch(Circle((10.46, 6.55), 0.2, fc=GREEN, ec="#1e5e2b", zorder=5))
    ax.plot([10.46, 10.46], [6.1, 6.35], color=WALL, lw=2.5)
    ax.plot([10.25, 10.67], [6.1, 6.1], color=WALL, lw=2.5)
    ax.text(10.46, 5.8, "Microphone", ha="center", fontsize=11.5, fontweight="bold")
    # the ping travels from room A through the doors
    arrow(ax, (9.7, 8.06), (7.2, 8.06), BLUE)
    arrow(ax, (7.2, 8.06), (4.4, 8.06), BLUE)
    arrow(ax, (4.4, 8.06), (2.3, 8.06), BLUE)

    # ---------------- numbered callouts ----------------
    callout(ax, 4.5, 9.35, 4.4, 1.2, 2, "Three rooms in a row:\nRoom A · Room B · Room C", ORANGE)
    for tx in (3.5, 6.75, 9.9):
        arrow(ax, (6.7, 9.35), (tx, y1 + 0.1), ORANGE, rad=0.0)
    callout(ax, 9.3, 9.35, 4.4, 1.2, 1, "Speaker and microphone\nin Room A", GREEN)
    arrow(ax, (12.0, 9.35), (10.9, 8.1), GREEN, rad=-0.2)
    callout(ax, 11.75, 6.1, 2.2, 1.55, 5, "One ping,\none mic:\nstate of\nthe house", BLUE)
    arrow(ax, (11.75, 6.7), (10.75, 6.55), BLUE)
    callout(ax, 0.1, 2.35, 4.3, 0.95, 3, "One observed window per\nroom (a / b / c)", BLUE)
    arrow(ax, (1.6, 3.3), (2.7, 3.85), BLUE, rad=-0.2)
    callout(ax, 7.6, 2.35, 3.9, 0.95, 4, "Rooms connected by\ndoors AB and BC", RED)
    arrow(ax, (7.75, 3.0), (4.6, 6.55), RED, rad=-0.35)
    arrow(ax, (8.6, 3.3), (7.85, 5.0), RED, rad=0.1)

    # ---------------- summary panel ----------------
    ax.add_patch(FancyBboxPatch((0.4, 0.1), 13.2, 1.95, boxstyle="round,pad=0.02,rounding_size=0.2",
                                fc="#fff8ec", ec="#8c6d46", lw=2))
    ax.text(0.8, 1.35, "Model house", fontsize=19, fontweight="bold", color="#343a40")
    ax.text(0.8, 0.75, "structure", fontsize=19, fontweight="bold", color="#343a40")
    items = [(GREEN, "Three rooms connected in series"), (ORANGE, "Three windows: a, b, c"),
             (RED, "Two inner doors: AB, BC"), (BLUE, "5 open/closed openings = 32 states")]
    for i, (color, text) in enumerate(items):
        y = 1.72 - i * 0.43
        ax.add_patch(Circle((4.15, y), 0.09, color=color))
        ax.text(4.4, y, text, va="center", fontsize=12)
    ax.plot([3.85, 3.85], [0.3, 1.85], color="#ced4da", lw=1.2, linestyle="--")
    ax.plot([9.3, 9.3], [0.3, 1.85], color="#ced4da", lw=1.2, linestyle="--")
    for i, name in enumerate("cba"):
        cx = 9.75 + i * 0.85
        ax.add_patch(Rectangle((cx - 0.3, 1.35), 0.6, 0.45, fc="#a5d8ff", ec="#1864ab", lw=1.4))
        ax.text(cx, 1.12, name, ha="center", fontsize=13, fontweight="bold",
                color={"a": GREEN, "b": ORANGE, "c": BLUE}[name])
    for i, name in enumerate(("BC", "AB")):
        cx = 10.15 + i * 0.95
        ax.add_patch(Rectangle((cx - 0.18, 0.55), 0.36, 0.5, fc=RED, ec="#6d1a22", lw=1.2))
        ax.text(cx, 0.3, name, ha="center", fontsize=12, fontweight="bold", color=RED)
    ax.add_patch(Circle((12.85, 1.05), 0.72, fc="#ebfbee", ec=GREEN, lw=2))
    ax.text(12.85, 1.25, "Total", ha="center", va="center", fontsize=11, color=GREEN, fontweight="bold")
    ax.text(12.85, 0.85, "5 openings", ha="center", va="center", fontsize=9, color=GREEN,
            fontweight="bold")

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "house_en.svg", bbox_inches="tight")
    fig.savefig(OUT / "house_en.png", dpi=120, bbox_inches="tight", facecolor="white")
    print("wrote", OUT / "house_en.svg", OUT / "house_en.png")


if __name__ == "__main__":
    main()
