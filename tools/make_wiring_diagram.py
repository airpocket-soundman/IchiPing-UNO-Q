"""Draw the UNO Ping wiring diagram (SVG for the docs, PNG for Hackster).

usage: python tools/make_wiring_diagram.py
Writes docs/img/unoq_wiring_en.svg and docs/img/unoq_wiring_en.png.
Pin assignments follow docs/uno_q/hardware.md (verified on the test board).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "docs" / "img"

C_MCU = "#1f6feb"     # 3.3 V MCU signals
C_AUDIO = "#d9480f"   # 1.8 V MI2S0 signals
C_PWR = "#2b8a3e"     # 5 V supply
C_TXT = "#212529"
C_NOTE = "#495057"
LINE_H = 0.34         # text line pitch inside boxes
TITLE_GAP = 0.72      # box top -> first text line


def box_height(n_lines: int) -> float:
    return TITLE_GAP + (n_lines - 1) * LINE_H + 0.35


def box(ax, x, top, w, title, color, lines, title_size=12.5):
    """Rounded box whose height fits its title and text lines; returns the bottom y."""
    h = box_height(len(lines))
    ax.add_patch(FancyBboxPatch((x, top - h), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc="white", ec=color, lw=2.2))
    ax.text(x + w / 2, top - 0.3, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color=color)
    for i, text in enumerate(lines):
        ax.text(x + 0.16, line_y(top, i), text, ha="left", va="center",
                fontsize=9.2, color=C_TXT, family="monospace")
    return top - h


def line_y(top: float, index: int) -> float:
    return top - TITLE_GAP - index * LINE_H


def dot(ax, x, y, color):
    ax.plot([x], [y], "o", color=color, ms=4.5, zorder=5)


def link(ax, x0, y0, x1, y1, color, lw=1.8, via_x=None):
    """Orthogonal wire from (x0, y0) to (x1, y1), bending at via_x."""
    if via_x is None or abs(y0 - y1) < 1e-6:
        ax.plot([x0, x1], [y0, y0] if abs(y0 - y1) < 1e-6 else [y0, y1], color=color, lw=lw)
    else:
        ax.plot([x0, via_x, via_x, x1], [y0, y0, y1, y1], color=color, lw=lw)
    dot(ax, x0, y0, color)
    dot(ax, x1, y1, color)


def main() -> None:
    fig, ax = plt.subplots(figsize=(17, 11))
    ax.set_xlim(0, 17)
    ax.set_ylim(0, 11)
    ax.axis("off")
    ax.text(8.5, 10.65, "UNO Ping — wiring", ha="center", fontsize=19, fontweight="bold")
    ax.text(8.5, 10.25, "blue = 3.3 V UNO header (STM32U585)     orange = 1.8 V MI2S0 audio (QRB2210, JMISC / "
            "UNO Breakout Carrier)     green = 5 V supply     all grounds common",
            ha="center", fontsize=10, color=C_NOTE)

    # ---------------- left column: external MCU devices ----------------
    lx, lw = 0.2, 3.9
    sw_top = 9.8
    sw = ["D3 window a    D4 window b", "D5 window c    D6 door AB", "D7 door BC",
          "D8 EXEC push button", "other side of each: GND", "GND = CLOSE (0), open = OPEN (1)"]
    sw_bottom = box(ax, lx, sw_top, lw, "State switches + EXEC", C_MCU, sw)

    pca_top = sw_bottom - 0.3
    pca = ["SDA ← D20     SCL ← D21", "VCC ← 3V3     V+  ← 5 V", "ch0..4 → SG90 a, b, c, AB, BC",
           "0° = OPEN, 180° = CLOSE"]
    pca_bottom = box(ax, lx, pca_top, lw, "PCA9685  (I²C 0x40)", C_MCU, pca)

    tft_top = pca_bottom - 0.3
    tft = ["MOSI ← D11    SCK ← D13", "CS ← A2   RST ← A3", "DC ← A4   BL  ← A5", "VCC ← 3V3  (MISO n.c.)"]
    tft_bottom = box(ax, lx, tft_top, lw, "ILI9341 2.4\" TFT (SPI)", C_MCU, tft)

    # ---------------- UNO Q board ----------------
    bx0, bx1, by0, by1 = 5.3, 11.0, tft_bottom, 9.8
    ax.add_patch(FancyBboxPatch((bx0, by0), bx1 - bx0, by1 - by0,
                                boxstyle="round,pad=0.02,rounding_size=0.15", fc="#f8f9fa", ec=C_TXT, lw=2.4))
    ax.text((bx0 + bx1) / 2, by1 - 0.35, "Arduino UNO Q", ha="center", fontsize=16, fontweight="bold")
    ax.text(bx0 + 0.15, by1 - 0.8, "UNO header, 3.3 V", fontsize=9.5, color=C_MCU, fontweight="bold")
    ax.text(bx1 - 0.15, by1 - 0.8, "MI2S0, 1.8 V", fontsize=9.5, color=C_AUDIO, fontweight="bold", ha="right")
    ax.text((bx0 + bx1) / 2, by0 + 0.25, "D9 reserved / unused     onboard LED matrix unused",
            ha="center", fontsize=8.5, color=C_NOTE)

    # MCU pins on the board edge: fixed rows (below the heading), grouped per device;
    # each wire bends once at its own x so no two wires overlap.
    mcu_rows = [  # (label on the board, board y, device line y)
        ("D3–D7", 8.5, line_y(sw_top, 0)),
        ("D8  EXEC", 8.1, line_y(sw_top, 3)),
        ("D20 SDA", 6.9, line_y(pca_top, 0)),
        ("D21 SCL", 6.5, line_y(pca_top, 0)),
        ("D11 MOSI", 5.3, line_y(tft_top, 0)),
        ("D13 SCK", 4.9, line_y(tft_top, 0)),
        ("A2 CS   A3 RST", 4.5, line_y(tft_top, 1)),
        ("A4 DC   A5 BL", 4.1, line_y(tft_top, 2)),
        ("3V3", 3.7, line_y(tft_top, 3)),
    ]
    for i, (text, py, dy) in enumerate(mcu_rows):
        ax.text(bx0 + 0.15, py, text, fontsize=9, color=C_MCU, family="monospace", va="center")
        link(ax, lx + lw, dy, bx0, py, C_MCU, lw=1.8, via_x=4.35 + 0.1 * (i % 9))

    # ---------------- right column: audio ----------------
    rx, rw = 13.0, 3.8
    amp_top = 9.8
    amp = ["BCLK ← GPIO98", "LRC  ← GPIO99", "DIN  ← GPIO101", "SD   ← GPIO28",
           "     + 10 kΩ from SD to GND", "GAIN → GND (12 dB)", "VIN  ← 5 V",
           "OUT± → speaker (bridge-tied,", "     no grounded probe)"]
    amp_bottom = box(ax, rx, amp_top, rw, "MAX98357A amplifier", C_AUDIO, amp)
    mic_top = amp_bottom - 0.5
    mic = ["SCK  ← GPIO98", "WS   ← GPIO99", "SD   → GPIO100", "L/R  → GND (left slot)", "VDD  ← 1.8 V",
           "GND  common"]
    box(ax, rx, mic_top, rw, "INMP441 microphone", C_AUDIO, mic)

    audio_rows = [("GPIO98  BCLK   J15-32 JMISC-46", 7.9, [(amp_top, 0), (mic_top, 0)], 11.45),
                  ("GPIO99  WS     J15-34 JMISC-48", 7.45, [(amp_top, 1), (mic_top, 1)], 11.75),
                  ("GPIO100 DATA0  J15-36 JMISC-50", 7.0, [(mic_top, 2)], 12.05),
                  ("GPIO101 DATA1  J15-38 JMISC-52", 6.55, [(amp_top, 2)], 12.3),
                  ("GPIO28  SD_MODE        JMISC-51", 6.1, [(amp_top, 3)], 12.55)]
    for text, y, targets, bus_x in audio_rows:
        ax.text(bx1 - 0.15, y, text, fontsize=9, color=C_AUDIO, family="monospace", va="center", ha="right")
        ys = [line_y(top, i) for top, i in targets]
        ax.plot([bx1, bus_x], [y, y], color=C_AUDIO, lw=1.8)
        ax.plot([bus_x, bus_x], [min(ys + [y]), max(ys + [y])], color=C_AUDIO, lw=1.8)
        dot(ax, bx1, y, C_AUDIO)
        for ty in ys:
            ax.plot([bus_x, rx], [ty, ty], color=C_AUDIO, lw=1.8)
            dot(ax, rx, ty, C_AUDIO)
    ax.text(rx + rw / 2, 1.15, "MI2S0 is 1.8 V logic only:\nnever connect 3.3 V or 5 V signals",
            ha="center", fontsize=9.5, color=C_AUDIO, fontweight="bold")

    # ---------------- bottom: 5 V supply ----------------
    ax.add_patch(FancyBboxPatch((0.2, 0.3), 10.8, 1.0, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc="white", ec=C_PWR, lw=2.2))
    ax.text(0.45, 1.0, "External 5 V supply", fontsize=12, fontweight="bold", color=C_PWR, va="center")
    ax.text(0.45, 0.6, "→ PCA9685 V+ (servos)   → MAX98357A VIN   GND common with the UNO Q   "
            "(never power the servos from 3V3)", fontsize=9.2, color=C_TXT, va="center", family="monospace")

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "unoq_wiring_en.svg", bbox_inches="tight")
    fig.savefig(OUT / "unoq_wiring_en.png", dpi=130, bbox_inches="tight", facecolor="white")
    print("wrote", OUT / "unoq_wiring_en.svg", OUT / "unoq_wiring_en.png")


if __name__ == "__main__":
    main()
