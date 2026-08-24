"""Create THT, SMD, and connector-THT assembly variants of both shields.

The routed, reviewed boards are the geometry source.  Component pad technology
is changed in place so connector pin order, board outline, and the proven net
topology cannot drift between variants.  The SMD connector landing patterns
are deliberately project-local 2.54 mm vertical-header patterns; see DESIGN.md
for the XH mechanical limitation.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
VARIANT_ROOT = ROOT / "variants"


@dataclass(frozen=True)
class BoardFamily:
    key: str
    source_dir: str
    stem: str
    connector_refs: frozenset[str]
    passive_refs: frozenset[str]


FAMILIES = (
    BoardFamily(
        "uno",
        "uno_shield",
        "ichiping_uno_q_shield",
        frozenset(
            {
                "J1", "J2", "J3", "J4", "J_EXEC", "J_DOOR_BC",
                "J_DOOR_AB", "J_WIN_C", "J_WIN_B", "J_WIN_A",
                "J_SERVO_CTRL", "J_RAIN", "J_PWR_IN",
                "J_SERVO_5V_OUT", "J_TFT_SIG", "J_TFT_PWR",
            }
        ),
        frozenset({"C_PWR_BULK", "C_PWR_HF", "C_SERVO_BULK"}),
    ),
    BoardFamily(
        "audio",
        "audio_shield",
        "ichiping_uno_q_audio_shield",
        frozenset({"J14", "J15", "J_AMP_SIG", "J_AMP_PWR", "J_MIC", "JP_MUTE"}),
        frozenset({"R_GAIN", "R_SD", "R_LR", "C1", "C2", "C3"}),
    ),
)

VARIANTS = {
    "tht": (False, False, "ALL PARTS THT"),
    "smd": (True, True, "ALL SMD"),
    "hybrid": (False, True, "CONN THT/SMD"),
}


def output_suffix(variant: str) -> str:
    # Avoid collision with an incomplete EasyEDA import group created during
    # the first SMD importer trial.  The explicit name is clearer in both the
    # project tree and generated manufacturing archives.
    return "smd_full" if variant == "smd" else variant


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def vec(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def pad_layers(attribute: int) -> pcbnew.LSET:
    library = Path(r"C:\Program Files\KiCad\8.0\share\kicad\footprints")
    if attribute == pcbnew.PAD_ATTRIB_SMD:
        fp = pcbnew.FootprintLoad(str(library / "Resistor_SMD.pretty"), "R_0805_2012Metric")
    else:
        fp = pcbnew.FootprintLoad(
            str(library / "Resistor_THT.pretty"),
            "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
        )
    if fp is None:
        raise FileNotFoundError("KiCad stock footprint library")
    return next(iter(fp.Pads())).GetLayerSet()


SMD_LAYERS = pad_layers(pcbnew.PAD_ATTRIB_SMD)
PTH_LAYERS = pad_layers(pcbnew.PAD_ATTRIB_PTH)


def set_smd(footprint: pcbnew.FOOTPRINT, connector: bool) -> None:
    for pad in footprint.Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            continue
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            continue
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetLayerSet(SMD_LAYERS)
        pad.SetDrillSize(vec(0, 0))
        pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
        pad.SetRoundRectRadiusRatio(0.20)
        # Keep the copper conservative around the already DRC-clean routed
        # geometry.  The long axis provides a hand-solderable toe without
        # approaching the adjacent 2.54 mm pin row.
        pad.SetSize(vec(0.80, 1.20) if connector else vec(1.20, 1.60))
    # The complete customized land pattern is embedded in the board.  Detach
    # the library link so KiCad and EasyEDA do not try to resolve a local-only
    # library during DRC/import.
    footprint.SetFPID(pcbnew.LIB_ID())


def set_tht(footprint: pcbnew.FOOTPRINT, connector: bool) -> None:
    for pad in footprint.Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            continue
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            continue
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetLayerSet(PTH_LAYERS)
        pad.SetDrillSize(vec(1.00 if connector else 0.60, 1.00 if connector else 0.60))
        pad.SetShape(pcbnew.PAD_SHAPE_OVAL)
        pad.SetSize(vec(1.80 if connector else 1.20, 2.20 if connector else 1.20))
    footprint.SetFPID(pcbnew.LIB_ID())


def add_via_in_pad_for_back_routes(board: pcbnew.BOARD, footprint: pcbnew.FOOTPRINT) -> None:
    """Connect front SMD pads to existing back-layer route endpoints."""
    back_points = {
        (item.GetStart().x, item.GetStart().y, item.GetNetCode())
        for item in board.GetTracks()
        if not isinstance(item, pcbnew.PCB_VIA) and item.GetLayer() == pcbnew.B_Cu
    }
    back_points.update(
        (item.GetEnd().x, item.GetEnd().y, item.GetNetCode())
        for item in board.GetTracks()
        if not isinstance(item, pcbnew.PCB_VIA) and item.GetLayer() == pcbnew.B_Cu
    )
    existing = {
        (item.GetPosition().x, item.GetPosition().y, item.GetNetCode())
        for item in board.GetTracks()
        if isinstance(item, pcbnew.PCB_VIA)
    }
    for pad in footprint.Pads():
        pos = pad.GetPosition()
        key = (pos.x, pos.y, pad.GetNetCode())
        if key not in back_points or key in existing:
            continue
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pos)
        # Match the repository/EasyEDA manufacturing default.  Microvias are
        # intentionally avoided so the SMD option remains a standard 2-layer
        # process despite using via-in-pad transitions at connector lands.
        via.SetWidth(mm(0.90))
        via.SetDrill(mm(0.50))
        via.SetNetCode(pad.GetNetCode())
        board.Add(via)
        existing.add(key)


def update_board_text(board: pcbnew.BOARD, label: str) -> None:
    for drawing in board.GetDrawings():
        if not isinstance(drawing, pcbnew.PCB_TEXT):
            continue
        text = drawing.GetText()
        if "I2S=1V8" in text:
            drawing.SetText(f"I2S=1V8  {label}")
    title = board.GetTitleBlock()
    title.SetTitle(f"IchiPing UNO Q {label}")


def change_symbol_footprints(text: str, mapping: dict[str, str]) -> str:
    """Replace instance Footprint properties in a modern KiCad schematic."""
    for reference, footprint in mapping.items():
        ref_token = f'(property "Reference" "{reference}"'
        start = text.find(ref_token)
        if start < 0:
            raise ValueError(f"schematic reference not found: {reference}")
        fp_start = text.find('(property "Footprint" "', start)
        instances = text.find("(instances", start)
        if fp_start < 0 or (instances >= 0 and fp_start > instances):
            raise ValueError(f"schematic footprint not found: {reference}")
        value_start = fp_start + len('(property "Footprint" "')
        value_end = text.find('"', value_start)
        text = text[:value_start] + footprint + text[value_end:]
    return text


def change_legacy_footprints(text: str, mapping: dict[str, str]) -> str:
    blocks = text.split("$Comp")
    for index in range(1, len(blocks)):
        block = blocks[index]
        match = re.search(r"^F 0 \"([^\"]+)\"", block, re.MULTILINE)
        if not match or match.group(1) not in mapping:
            continue
        footprint = mapping[match.group(1)]
        block, count = re.subn(r'^F 2 "[^"]*"', f'F 2 "{footprint}"', block, count=1, flags=re.MULTILINE)
        if count != 1:
            raise ValueError(f"legacy footprint not found: {match.group(1)}")
        blocks[index] = block
    return "$Comp".join(blocks)


def schematic_mapping(family: BoardFamily, smd_connectors: bool, smd_passives: bool) -> dict[str, str]:
    """Return valid stock-library properties for EasyEDA's KiCad importer."""

    def one_row(kind: str, count: int) -> str:
        suffix = "_SMD_Pin1Left" if smd_connectors else ""
        library = "Connector_PinSocket_2.54mm" if kind == "socket" else "Connector_PinHeader_2.54mm"
        name = "PinSocket" if kind == "socket" else "PinHeader"
        return f"{library}:{name}_1x{count:02d}_P2.54mm_Vertical{suffix}"

    mapping: dict[str, str] = {}
    if family.key == "uno":
        mapping.update({
            "J1": one_row("socket", 8),
            "J2": one_row("socket", 10),
            "J3": one_row("socket", 6),
            "J4": one_row("socket", 8),
            "J_EXEC": one_row("header", 2),
            "J_DOOR_BC": one_row("header", 2),
            "J_DOOR_AB": one_row("header", 2),
            "J_WIN_C": one_row("header", 2),
            "J_WIN_B": one_row("header", 2),
            "J_WIN_A": one_row("header", 2),
            "J_SERVO_CTRL": one_row("header", 4),
            "J_RAIN": one_row("header", 3),
            "J_PWR_IN": one_row("header", 2),
            "J_SERVO_5V_OUT": one_row("header", 2),
            "J_TFT_SIG": one_row("header", 5),
            "J_TFT_PWR": one_row("header", 4),
        })
        if smd_passives:
            mapping.update({
                "C_PWR_BULK": "Capacitor_SMD:CP_Elec_8x10.5",
                "C_PWR_HF": "Capacitor_SMD:C_0805_2012Metric",
                "C_SERVO_BULK": "Capacitor_SMD:CP_Elec_10x10.5",
            })
        else:
            mapping.update({
                "C_PWR_BULK": "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
                "C_PWR_HF": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
                "C_SERVO_BULK": "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
            })
    else:
        socket_suffix = "_SMD" if smd_connectors else ""
        mapping.update({
            "J14": f"Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical{socket_suffix}",
            "J15": f"Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical{socket_suffix}",
            "J_AMP_SIG": one_row("header", 4),
            "J_AMP_PWR": one_row("header", 3),
            "J_MIC": one_row("header", 6),
            "JP_MUTE": one_row("header", 2),
        })
        if smd_passives:
            mapping.update({
                "R_GAIN": "Resistor_SMD:R_0805_2012Metric",
                "R_SD": "Resistor_SMD:R_0805_2012Metric",
                "R_LR": "Resistor_SMD:R_0805_2012Metric",
                "C1": "Capacitor_SMD:CP_Elec_5x5.8",
                "C2": "Capacitor_SMD:C_0805_2012Metric",
                "C3": "Capacitor_SMD:C_0805_2012Metric",
            })
        else:
            mapping.update({
                "R_GAIN": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                "R_SD": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                "R_LR": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                "C1": "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
                "C2": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
                "C3": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
            })
    return mapping


def write_bundle(output_dir: Path, stem: str, mapping: dict[str, str]) -> None:
    """Write an EasyEDA bundle whose PCB IDs match schematic properties.

    The canonical PCB intentionally embeds/detaches customized land patterns
    for strict KiCad physical DRC.  EasyEDA's importer instead requires the
    symbol and PCB Footprint identity strings to agree, so only the import copy
    receives the closest valid stock-library IDs.
    """
    archive = output_dir.parent / f"{stem}_easyeda_import.zip"
    with tempfile.TemporaryDirectory(prefix="ichiping-easyeda-") as temporary:
        temporary_board = Path(temporary) / f"{stem}.kicad_pcb"
        board = pcbnew.LoadBoard(str(output_dir / f"{stem}.kicad_pcb"))
        for footprint in board.GetFootprints():
            footprint_id = mapping.get(footprint.GetReference())
            if footprint_id:
                library, name = footprint_id.split(":", 1)
                footprint.SetFPID(pcbnew.LIB_ID(library, name))
        pcbnew.SaveBoard(str(temporary_board), board)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            schematic = output_dir / f"{stem}.kicad_sch"
            bundle.write(schematic, schematic.name)
            bundle.write(temporary_board, temporary_board.name)


def build_variant(family: BoardFamily, variant: str) -> Path:
    smd_connectors, smd_passives, label = VARIANTS[variant]
    source = ROOT / family.source_dir
    output = VARIANT_ROOT / variant / f"{family.key}_shield"
    output.mkdir(parents=True, exist_ok=True)
    stem = f"{family.stem}_{output_suffix(variant)}"

    board = pcbnew.LoadBoard(str(source / f"{family.stem}.kicad_pcb"))
    refs = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    for reference in family.connector_refs:
        (set_smd if smd_connectors else set_tht)(refs[reference], True)
    for reference in family.passive_refs:
        (set_smd if smd_passives else set_tht)(refs[reference], False)
    if smd_connectors or smd_passives:
        selected = family.connector_refs if smd_connectors else frozenset()
        selected |= family.passive_refs if smd_passives else frozenset()
        for reference in selected:
            add_via_in_pad_for_back_routes(board, refs[reference])
    update_board_text(board, label)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(output / f"{stem}.kicad_pcb"), board)

    mapping = schematic_mapping(family, smd_connectors, smd_passives)
    modern = (source / f"{family.stem}.kicad_sch").read_text(encoding="utf-8")
    (output / f"{stem}.kicad_sch").write_text(change_symbol_footprints(modern, mapping), encoding="utf-8")
    legacy = (source / f"{family.stem}.sch").read_text(encoding="utf-8")
    (output / f"{stem}.sch").write_text(change_legacy_footprints(legacy, mapping), encoding="utf-8")
    shutil.copy2(source / f"{family.stem}.kicad_pro", output / f"{stem}.kicad_pro")
    cache = source / f"{family.stem}-cache.lib"
    if cache.exists():
        shutil.copy2(cache, output / f"{stem}-cache.lib")
    write_bundle(output, stem, mapping)
    return output


def main() -> None:
    if VARIANT_ROOT.exists():
        shutil.rmtree(VARIANT_ROOT)
    for variant in VARIANTS:
        for family in FAMILIES:
            print(build_variant(family, variant))


if __name__ == "__main__":
    main()
