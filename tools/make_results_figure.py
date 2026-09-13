"""Render the headline results table as an image (Hackster has no tables).

usage: python tools/make_results_figure.py
Writes docs/img/hackster_results_en.png and .svg from the numbers in
pc/runs/model_comparison_20260912.md (held-out UNO Q evaluation sessions).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / "docs" / "img"

COLUMNS = ["09:00\nstable", "19:35\n−2.15 % drift", "20:44\n−1.05 % drift", "21:28\ncrowd noise", "Mean\n32-state"]
ROWS = [
    ("Original FRDM model", ["20.8 / 59.4", "35.9 / 68.8", "9.1 / 49.7", "11.6 / 50.0", "19.3"]),
    ("UNO Q, 4 sessions", ["86.5 / 100", "43.1 / 84.1", "69.1 / 99.7", "76.9 / 100", "68.9"]),
    ("+ frequency warp", ["89.6 / 100", "56.9 / 93.8", "82.8 / 100", "80.9 / 100", "77.6"]),
    ("8 sessions + warp + ambient\n(deployed)", ["91.7 / 100", "81.9 / 100", "74.7 / 100", "81.9 / 100", "82.5"]),
]


def main() -> None:
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.axis("off")
    ax.set_title("UNO Ping — accuracy on held-out evaluation sessions (32-state / 14-class, %)",
                 fontsize=13, fontweight="bold", pad=12)
    table = ax.table(cellText=[r[1] for r in ROWS], rowLabels=[r[0] for r in ROWS], colLabels=COLUMNS,
                     cellLoc="center", rowLoc="left", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.6)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#ced4da")
        if row == 0:
            cell.set_facecolor("#e7f1ff")
            cell.set_text_props(fontweight="bold")
        if col == -1:
            cell.set_text_props(ha="left")
        if row == len(ROWS):
            cell.set_facecolor("#e6fcf5")
            cell.set_text_props(fontweight="bold")
    fig.text(0.5, 0.02, "14-class = observable classes (a closed door AB hides b, c, BC). "
             "Evaluation sessions were never used for training.", ha="center", fontsize=9.5, color="#495057")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "hackster_results_en.svg", bbox_inches="tight")
    fig.savefig(OUT / "hackster_results_en.png", dpi=140, bbox_inches="tight", facecolor="white")
    print("wrote", OUT / "hackster_results_en.png")


if __name__ == "__main__":
    main()
