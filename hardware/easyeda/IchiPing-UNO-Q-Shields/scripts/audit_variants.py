"""Audit assembly technology and critical nets in all six PCB variants."""

from __future__ import annotations

import math
from pathlib import Path

import pcbnew

from generate_variants import FAMILIES, VARIANT_ROOT, VARIANTS, output_suffix


EXPECTED_NETS = {
    "uno": {
        "J_TFT_SIG": ["D12_MISO", "A5", "D13_SCK", "D11_MOSI", "A4"],
        "J_TFT_PWR": ["A3", "A2", "GND", "+3V3"],
        "J_PWR_IN": ["+5V", "GND"],
        "J_SERVO_5V_OUT": ["+5V", "GND"],
    },
    "audio": {
        "J_AMP_SIG": ["MI2S0_WS", "MI2S0_CLK", "MI2S0_DATA1", "AMP_GAIN"],
        "J_AMP_PWR": ["AMP_SD", "GND", "+5V"],
        "J_MIC": ["GND", "+1V8", "MI2S0_DATA0", "MI2S0_CLK", "MI2S0_WS", "MIC_LR"],
    },
}


def audit() -> None:
    for variant, (smd_connectors, smd_passives, _) in VARIANTS.items():
        expected_connector_attr = pcbnew.PAD_ATTRIB_SMD if smd_connectors else pcbnew.PAD_ATTRIB_PTH
        expected_passive_attr = pcbnew.PAD_ATTRIB_SMD if smd_passives else pcbnew.PAD_ATTRIB_PTH
        for family in FAMILIES:
            stem = f"{family.stem}_{output_suffix(variant)}"
            path = VARIANT_ROOT / variant / f"{family.key}_shield" / f"{stem}.kicad_pcb"
            board = pcbnew.LoadBoard(str(path))
            footprints = {item.GetReference(): item for item in board.GetFootprints()}
            for refs, expected_attr in (
                (family.connector_refs, expected_connector_attr),
                (family.passive_refs, expected_passive_attr),
            ):
                for reference in refs:
                    for pad in footprints[reference].Pads():
                        if pad.GetAttribute() != expected_attr:
                            raise AssertionError(f"{variant}/{family.key}/{reference}/{pad.GetNumber()}: wrong technology")
            for reference, expected_nets in EXPECTED_NETS[family.key].items():
                pads = sorted(footprints[reference].Pads(), key=lambda pad: int(pad.GetNumber()))
                actual = [pad.GetNetname() for pad in pads]
                if actual != expected_nets:
                    raise AssertionError(f"{variant}/{family.key}/{reference}: {actual} != {expected_nets}")
                for first, second in zip(pads, pads[1:]):
                    delta = first.GetPosition() - second.GetPosition()
                    pitch = math.hypot(pcbnew.ToMM(delta.x), pcbnew.ToMM(delta.y))
                    if not math.isclose(pitch, 2.54, abs_tol=0.001):
                        raise AssertionError(f"{variant}/{family.key}/{reference}: pitch={pitch}")
            if family.key == "uno":
                if footprints["J1"].FindPadByNumber("8").GetNetname() != "VIN":
                    raise AssertionError(f"{variant}/uno: VIN identity lost")
                if footprints["J_PWR_IN"].FindPadByNumber("1").GetNetname() == "VIN":
                    raise AssertionError(f"{variant}/uno: regulated 5 V connected to VIN")
            print(f"PASS {variant}/{family.key}: technology, pin order, pitch, and power nets")


if __name__ == "__main__":
    audit()
