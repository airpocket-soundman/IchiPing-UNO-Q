"""Audit connector pin order, XH2.54 pitch, and critical power nets."""

from __future__ import annotations

from pathlib import Path
import math

import pcbnew


ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "uno_shield/ichiping_uno_q_shield.kicad_pcb": {
        "J_WIN_A": ["D3_WIN_A", "GND"],
        "J_WIN_B": ["D4_WIN_B", "GND"],
        "J_WIN_C": ["D5_WIN_C", "GND"],
        "J_DOOR_AB": ["D6_DOOR_AB", "GND"],
        "J_DOOR_BC": ["D7_DOOR_BC", "GND"],
        "J_EXEC": ["D8_EXEC", "GND"],
        "J_RAIN": ["+3V3", "GND", "D9_RAIN"],
        "J_SERVO_CTRL": ["GND", "D21_SCL", "D20_SDA", "+3V3"],
        "J_TFT_SIG": ["D12_MISO", "A5", "D13_SCK", "D11_MOSI", "A4"],
        "J_TFT_PWR": ["A3", "A2", "GND", "+3V3"],
        "J_PWR_IN": ["+5V", "GND"],
        "J_SERVO_5V_OUT": ["+5V", "GND"],
    },
    "audio_shield/ichiping_uno_q_audio_shield.kicad_pcb": {
        "J_AMP_SIG": ["MI2S0_WS", "MI2S0_CLK", "MI2S0_DATA1", "AMP_GAIN"],
        "J_AMP_PWR": ["AMP_SD", "GND", "+5V"],
        "J_MIC": ["GND", "+1V8", "MI2S0_DATA0", "MI2S0_CLK", "MI2S0_WS", "MIC_LR"],
    },
}


def audit_board(relative_path: str, expected: dict[str, list[str]]) -> None:
    board = pcbnew.LoadBoard(str(ROOT / relative_path))
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    for reference, expected_nets in expected.items():
        footprint = footprints[reference]
        pads = sorted(footprint.Pads(), key=lambda pad: int(pad.GetNumber()))
        actual_nets = [pad.GetNetname() for pad in pads]
        if actual_nets != expected_nets:
            raise AssertionError(f"{reference}: {actual_nets} != {expected_nets}")
        for first, second in zip(pads, pads[1:]):
            a = first.GetPosition()
            b = second.GetPosition()
            pitch = math.hypot(pcbnew.ToMM(a.x - b.x), pcbnew.ToMM(a.y - b.y))
            if not math.isclose(pitch, 2.54, abs_tol=0.001):
                raise AssertionError(f"{reference}: pad pitch {pitch:.4f} mm")

    if "uno_shield" in relative_path:
        power_header = footprints["J1"]
        if power_header.FindPadByNumber("5").GetNetname() != "+5V":
            raise AssertionError("UNO +5V header pad is not on +5V")
        if power_header.FindPadByNumber("8").GetNetname() != "VIN":
            raise AssertionError("UNO VIN identity was lost")
        if footprints["J_PWR_IN"].FindPadByNumber("1").GetNetname() == "VIN":
            raise AssertionError("External regulated 5 V must never feed VIN")
        input_bulk = footprints["C_PWR_BULK"]
        if input_bulk.GetValue() != "470u 10V LOW ESR":
            raise AssertionError("5 V input bulk capacitor is not 470 uF / 10 V")
        if input_bulk.FindPadByNumber("1").GetNetname() != "+5V":
            raise AssertionError("C_PWR_BULK positive pad is not on +5V")
        if input_bulk.FindPadByNumber("2").GetNetname() != "GND":
            raise AssertionError("C_PWR_BULK negative pad is not on GND")
        positive = input_bulk.FindPadByNumber("1").GetPosition()
        negative = input_bulk.FindPadByNumber("2").GetPosition()
        lead_pitch = math.hypot(
            pcbnew.ToMM(positive.x - negative.x), pcbnew.ToMM(positive.y - negative.y)
        )
        if not math.isclose(lead_pitch, 3.50, abs_tol=0.001):
            raise AssertionError(f"C_PWR_BULK lead pitch {lead_pitch:.4f} mm")

    if "audio_shield" in relative_path:
        j15_right = max(pad.GetPosition().x for pad in footprints["J15"].Pads())
        for reference in ("J_AMP_SIG", "J_AMP_PWR", "J_MIC"):
            connector_left = min(pad.GetPosition().x for pad in footprints[reference].Pads())
            if connector_left <= j15_right:
                raise AssertionError(f"{reference} is not to the right of J15")
        for reference in ("R_GAIN", "R_SD", "R_LR", "JP_MUTE", "C1", "C2", "C3"):
            for pad in footprints[reference].Pads():
                if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                    raise AssertionError(f"{reference} pad {pad.GetNumber()} is not through-hole")
        if footprints["C1"].FindPadByNumber("1").GetNetname() != "+5V":
            raise AssertionError("C1 positive pad is not on +5V")
        if footprints["C1"].FindPadByNumber("2").GetNetname() != "GND":
            raise AssertionError("C1 negative pad is not on GND")

    print(f"PASS {relative_path}: connector nets and 2.54 mm XH pitch")


def main() -> None:
    for relative_path, expected in EXPECTED.items():
        audit_board(relative_path, expected)


if __name__ == "__main__":
    main()
