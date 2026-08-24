"""Generate the two IchiPing UNO Q shield PCBs and import schematics.

Run with KiCad 8's bundled Python so the pcbnew module is available.
The generated KiCad files are intentionally conservative and use only stock
KiCad libraries that EasyEDA Pro's KiCad importer understands.
"""

from __future__ import annotations

import json
import math
import shutil
import uuid
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
KICAD_ROOT = Path(r"C:\Program Files\KiCad\8.0\share\kicad")
FP_ROOT = KICAD_ROOT / "footprints"
UNO_TEMPLATE = KICAD_ROOT / "template" / "Arduino_Uno" / "Arduino_Uno.kicad_pcb"


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def vec(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def ensure_net(board: pcbnew.BOARD, name: str) -> pcbnew.NETINFO_ITEM:
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def find_pad(footprint: pcbnew.FOOTPRINT, number: str) -> pcbnew.PAD:
    for pad in footprint.Pads():
        if pad.GetNumber() == str(number):
            return pad
    raise KeyError(f"{footprint.GetReference()} pad {number}")


def set_pad_net(board: pcbnew.BOARD, footprint: pcbnew.FOOTPRINT, number: str, name: str) -> pcbnew.PAD:
    pad = find_pad(footprint, number)
    pad.SetNet(ensure_net(board, name))
    return pad


def load_footprint(
    board: pcbnew.BOARD,
    library: str,
    name: str,
    reference: str,
    value: str,
    x: float,
    y: float,
    rotation: float = 0,
) -> pcbnew.FOOTPRINT:
    footprint = pcbnew.FootprintLoad(str(FP_ROOT / f"{library}.pretty"), name)
    if footprint is None:
        raise FileNotFoundError(f"{library}:{name}")
    footprint.SetReference(reference)
    footprint.SetValue(value)
    footprint.SetPosition(vec(x, y))
    footprint.SetOrientationDegrees(rotation)
    footprint.Reference().SetVisible(False)
    footprint.Value().SetVisible(False)
    board.Add(footprint)
    return footprint


def remove_footprint_layers(footprint: pcbnew.FOOTPRINT, layers: set[int]) -> None:
    for item in list(footprint.GraphicalItems()):
        if item.GetLayer() in layers:
            item.SetLayer(pcbnew.Dwgs_User)


def strip_footprint_silks(board: pcbnew.BOARD) -> None:
    for footprint in board.GetFootprints():
        is_custom_xh = footprint.GetValue().startswith("XH2.54_")
        footprint.Reference().SetVisible(False)
        footprint.Value().SetVisible(False)
        remove_footprint_layers(footprint, {pcbnew.F_SilkS, pcbnew.B_SilkS})
        if is_custom_xh:
            remove_footprint_layers(footprint, {pcbnew.F_CrtYd, pcbnew.B_CrtYd})


def add_text(
    board: pcbnew.BOARD,
    text: str,
    x: float,
    y: float,
    size: float = 1.0,
    rotation: float = 0,
    layer: int = pcbnew.F_SilkS,
    bold: bool = False,
) -> pcbnew.PCB_TEXT:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(vec(x, y))
    item.SetLayer(layer)
    item.SetTextSize(vec(size, size))
    item.SetTextThickness(mm(0.18 if bold else 0.15))
    item.SetTextAngleDegrees(rotation)
    board.Add(item)
    return item


def add_track(
    board: pcbnew.BOARD,
    net_name: str,
    points: list[tuple[float, float]],
    layer: int,
    width: float = 0.25,
) -> None:
    net = ensure_net(board, net_name)
    for start, end in zip(points, points[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vec(*start))
        track.SetEnd(vec(*end))
        track.SetWidth(mm(width))
        track.SetLayer(layer)
        track.SetNetCode(net.GetNetCode())
        board.Add(track)


def pad_xy(pad: pcbnew.PAD) -> tuple[float, float]:
    position = pad.GetPosition()
    return pcbnew.ToMM(position.x), pcbnew.ToMM(position.y)


def route_direct(board: pcbnew.BOARD, net: str, a: pcbnew.PAD, b: pcbnew.PAD, layer: int, width: float = 0.25) -> None:
    add_track(board, net, [pad_xy(a), pad_xy(b)], layer, width)


def route_dogleg(
    board: pcbnew.BOARD,
    net: str,
    a: pcbnew.PAD,
    b: pcbnew.PAD,
    layer: int,
    bend_y: float,
    width: float = 0.25,
) -> None:
    ax, ay = pad_xy(a)
    bx, by = pad_xy(b)
    add_track(board, net, [(ax, ay), (ax, bend_y), (bx, bend_y), (bx, by)], layer, width)


def add_zone(board: pcbnew.BOARD, net_name: str, layer: int, polygon: list[tuple[float, float]]) -> None:
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(ensure_net(board, net_name))
    zone.SetLocalClearance(mm(0.30))
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in polygon:
        outline.Append(mm(x), mm(y))
    board.Add(zone)


def board_footprints(board: pcbnew.BOARD) -> dict[str, pcbnew.FOOTPRINT]:
    return {item.GetReference(): item for item in board.GetFootprints()}


def prepare_for_autorouter(board: pcbnew.BOARD) -> None:
    """Keep verified placement/netlist and discard the geometry-only draft."""
    for item in list(board.GetTracks()):
        board.Remove(item)
    for zone in list(board.Zones()):
        board.Remove(zone)


def configure_netclasses(board: pcbnew.BOARD) -> None:
    settings = board.GetDesignSettings().m_NetSettings
    board.GetDesignSettings().m_CopperEdgeClearance = mm(0.25)
    default = settings.m_DefaultNetClass
    default.SetClearance(mm(0.25))
    default.SetTrackWidth(mm(0.25))
    default.SetViaDiameter(mm(0.90))
    default.SetViaDrill(mm(0.50))
    classes = [
        ("Ground", 0.50, ["GND"]),
        ("Power", 0.50, ["+3V3", "+1V8"]),
        ("Power5V", 1.00, ["+5V"]),
    ]
    for name, width, nets in classes:
        netclass = pcbnew.NETCLASS(name)
        netclass.SetClearance(mm(0.25))
        netclass.SetTrackWidth(mm(width))
        netclass.SetViaDiameter(mm(0.90 if width <= 0.50 else 1.20))
        netclass.SetViaDrill(mm(0.50 if width <= 0.50 else 0.60))
        settings.m_NetClasses[name] = netclass
        for net_name in nets:
            settings.m_NetClassPatternAssignmentCache[net_name] = name


def assign_uno_header_nets(board: pcbnew.BOARD) -> dict[str, pcbnew.PAD]:
    """Assign UNO Q net names without tying A4/A5 to D20/D21."""
    refs = board_footprints(board)
    mapping = {
        "J1": {
            "2": "IOREF",
            "3": "RESET",
            "4": "+3V3",
            "5": "+5V",
            "6": "GND",
            "7": "GND",
            "8": "VIN",
        },
        "J3": {"1": "A0", "2": "A1", "3": "A2", "4": "A3", "5": "A4", "6": "A5"},
        "J2": {
            "1": "D21_SCL",
            "2": "D20_SDA",
            "3": "AREF",
            "4": "GND",
            "5": "D13_SCK",
            "6": "D12_MISO",
            "7": "D11_MOSI",
            "8": "D10",
            "9": "D9_RAIN",
            "10": "D8_EXEC",
        },
        "J4": {
            "1": "D7_DOOR_BC",
            "2": "D6_DOOR_AB",
            "3": "D5_WIN_C",
            "4": "D4_WIN_B",
            "5": "D3_WIN_A",
            "6": "D2",
            "7": "D1_TX",
            "8": "D0_RX",
        },
    }
    pads: dict[str, pcbnew.PAD] = {}
    for reference, pad_map in mapping.items():
        for number, net_name in pad_map.items():
            pads[net_name] = set_pad_net(board, refs[reference], number, net_name)
    for hole in ("MH1", "MH2", "MH3", "MH4"):
        refs[hole].SetValue("UNO mounting hole")
    return pads


def add_xh(
    board: pcbnew.BOARD,
    reference: str,
    pin_names: list[str],
    x: float,
    y: float,
    rotation: float = 0,
) -> tuple[pcbnew.FOOTPRINT, dict[str, pcbnew.PAD]]:
    count = len(pin_names)
    name = f"JST_XH_B{count}B-XH-A_1x{count:02d}_P2.50mm_Vertical"
    footprint = load_footprint(
        board,
        "Connector_JST",
        name,
        reference,
        f"XH2.54_Vertical_1x{count:02d}:" + "/".join(pin_names),
        x,
        y,
        rotation,
    )
    # The requested XH-compatible harness parts use 2.54 mm pitch. KiCad's
    # stock JST XH body is the closest vertical housing outline but is 2.50 mm,
    # so move every copper/drill pad onto the specified 2.54 mm grid. The BOM
    # deliberately calls these XH2.54-compatible, not genuine JST B?B-XH-A.
    angle = math.radians(rotation)
    for index in range(1, count + 1):
        offset = (index - 1) * 2.54
        pad = find_pad(footprint, str(index))
        pad.SetPosition(vec(x + offset * math.cos(angle), y + offset * math.sin(angle)))
    pads: dict[str, pcbnew.PAD] = {}
    for index, net_name in enumerate(pin_names, start=1):
        pads[net_name] = set_pad_net(board, footprint, str(index), net_name)
    return footprint, pads


def generate_uno_board() -> Path:
    out_dir = ROOT / "uno_shield"
    out_dir.mkdir(parents=True, exist_ok=True)
    board = pcbnew.LoadBoard(str(UNO_TEMPLATE))
    board.SetFileName(str(out_dir / "ichiping_uno_q_shield.kicad_pcb"))
    header = assign_uno_header_nets(board)

    xh: dict[str, dict[str, pcbnew.PAD]] = {}
    placements = [
        ("J_EXEC", ["D8_EXEC", "GND"], 120, 62, 0),
        ("J_DOOR_BC", ["D7_DOOR_BC", "GND"], 128, 62, 0),
        ("J_DOOR_AB", ["D6_DOOR_AB", "GND"], 136, 62, 0),
        ("J_WIN_C", ["D5_WIN_C", "GND"], 144, 62, 0),
        ("J_WIN_B", ["D4_WIN_B", "GND"], 152, 62, 0),
        ("J_WIN_A", ["D3_WIN_A", "GND"], 158, 70, 0),
        ("J_SERVO_CTRL", ["GND", "D21_SCL", "D20_SDA", "+3V3"], 102, 62, 0),
        ("J_RAIN", ["+3V3", "GND", "D9_RAIN"], 102, 75, 0),
        ("J_PWR_IN", ["+5V", "GND"], 145, 88, 0),
        ("J_SERVO_5V_OUT", ["+5V", "GND"], 154, 88, 0),
        ("J_TFT_SIG", ["D12_MISO", "A5", "D13_SCK", "D11_MOSI", "A4"], 114, 88, 180),
        ("J_TFT_PWR", ["A3", "A2", "GND", "+3V3"], 128, 88, 180),
    ]
    for reference, names, x, y, rotation in placements:
        _, xh[reference] = add_xh(board, reference, names, x, y, rotation)

    # GPIO inputs and I2C: order-preserving direct routes on the front layer.
    for net, reference in [
        ("D8_EXEC", "J_EXEC"),
        ("D7_DOOR_BC", "J_DOOR_BC"),
        ("D6_DOOR_AB", "J_DOOR_AB"),
        ("D5_WIN_C", "J_WIN_C"),
        ("D4_WIN_B", "J_WIN_B"),
        ("D3_WIN_A", "J_WIN_A"),
        ("D21_SCL", "J_SERVO_CTRL"),
        ("D20_SDA", "J_SERVO_CTRL"),
        ("D9_RAIN", "J_RAIN"),
    ]:
        route_direct(board, net, header[net], xh[reference][net], pcbnew.F_Cu)

    # TFT SPI and control paths use opposite layers where ordering would cross.
    route_direct(board, "D12_MISO", header["D12_MISO"], xh["J_TFT_SIG"]["D12_MISO"], pcbnew.B_Cu)
    route_direct(board, "D13_SCK", header["D13_SCK"], xh["J_TFT_SIG"]["D13_SCK"], pcbnew.B_Cu)
    route_direct(board, "D11_MOSI", header["D11_MOSI"], xh["J_TFT_SIG"]["D11_MOSI"], pcbnew.F_Cu)
    for net, reference in [("A5", "J_TFT_SIG"), ("A4", "J_TFT_SIG"), ("A3", "J_TFT_PWR"), ("A2", "J_TFT_PWR")]:
        route_direct(board, net, header[net], xh[reference][net], pcbnew.F_Cu)

    # 3.3 V trunk and branches. Servo VIN is deliberately the logic 3.3 V rail.
    pwr = header["+3V3"]
    px, py = pad_xy(pwr)
    add_track(board, "+3V3", [(px, py), (px, 94), (116, 94), (116, 84)], pcbnew.B_Cu, 0.50)
    for target, branch_y in [
        (xh["J_TFT_PWR"]["+3V3"], 90.5),
        (xh["J_RAIN"]["+3V3"], 82.5),
        (xh["J_SERVO_CTRL"]["+3V3"], 80.0),
    ]:
        tx, ty = pad_xy(target)
        add_track(board, "+3V3", [(116, 84), (116, branch_y), (tx, branch_y), (tx, ty)], pcbnew.B_Cu, 0.50)

    # A regulated external 5 V source feeds the UNO Q +5V header, never VIN.
    # The same rail branches directly to the separate PCA9685 servo V+ cable.
    for target in (xh["J_PWR_IN"]["+5V"], xh["J_SERVO_5V_OUT"]["+5V"]):
        route_direct(board, "+5V", header["+5V"], target, pcbnew.B_Cu, 1.50)

    power_caps = [
        ("C_PWR_BULK", "470u 10V LOW ESR", "+5V", 137.0, 79.0, "CP_Radial_D8.0mm_P3.50mm"),
        ("C_PWR_HF", "100n", "+5V", 145.0, 79.0, "C_0805_2012Metric"),
        ("C_SERVO_BULK", "1000u LOW ESR", "+5V", 126.0, 73.0, "CP_Radial_D10.0mm_P5.00mm"),
    ]
    for reference, value, supply, x, y, footprint_name in power_caps:
        library = "Capacitor_THT" if footprint_name.startswith("CP_") else "Capacitor_SMD"
        capacitor = load_footprint(board, library, footprint_name, reference, value, x, y)
        set_pad_net(board, capacitor, "1", supply)
        set_pad_net(board, capacitor, "2", "GND")

    uno_parts = board_footprints(board)
    for reference, target in [
        ("C_PWR_BULK", xh["J_PWR_IN"]["+5V"]),
        ("C_PWR_HF", xh["J_PWR_IN"]["+5V"]),
        ("C_SERVO_BULK", xh["J_SERVO_5V_OUT"]["+5V"]),
    ]:
        route_direct(board, "+5V", find_pad(uno_parts[reference], "1"), target, pcbnew.B_Cu, 1.00)

    # Ground fills are inset from the UNO outline to leave a clean edge margin.
    polygon = [(100.6, 47.2), (168.0, 47.2), (168.0, 99.4), (100.6, 99.4)]
    add_zone(board, "GND", pcbnew.F_Cu, polygon)
    add_zone(board, "GND", pcbnew.B_Cu, polygon)

    add_text(board, "IchiPing UNO Q SHIELD", 134, 70.5, 1.35, bold=True)
    add_text(board, "A2 CS  A3 RST  A4 DC  A5 LED", 136, 82.0, 0.85)
    add_text(board, "SERVO VIN=3V3 LOGIC ONLY", 117, 79.0, 0.8)
    add_text(board, "5V IN -> UNO +5V (NOT VIN)", 145, 84.0, 0.80)
    add_text(board, "PIN 1 >", 103, 72.0, 0.8)
    add_text(board, "REV A  2026-08-24", 135, 95.0, 0.8, layer=pcbnew.B_SilkS)

    prepare_for_autorouter(board)
    configure_netclasses(board)
    strip_footprint_silks(board)
    pcbnew.SaveBoard(str(out_dir / "ichiping_uno_q_shield.kicad_pcb"), board)
    write_legacy_schematic(
        out_dir / "ichiping_uno_q_shield.sch",
        "IchiPing UNO Q Shield",
        [
            ("J_WIN_A", ["D3_WIN_A", "GND"]),
            ("J_WIN_B", ["D4_WIN_B", "GND"]),
            ("J_WIN_C", ["D5_WIN_C", "GND"]),
            ("J_DOOR_AB", ["D6_DOOR_AB", "GND"]),
            ("J_DOOR_BC", ["D7_DOOR_BC", "GND"]),
            ("J_EXEC", ["D8_EXEC", "GND"]),
            ("J_TFT_SIG", ["D12_MISO", "A5_LED", "D13_SCK", "D11_MOSI", "A4_DC"]),
            ("J_TFT_PWR", ["A3_RST", "A2_CS", "GND", "+3V3"]),
            ("J_RAIN", ["+3V3", "GND", "D9_RAIN"]),
            ("J_SERVO_CTRL", ["GND", "D21_SCL", "D20_SDA", "+3V3"]),
            ("J_PWR_IN", ["+5V", "GND"]),
            ("J_SERVO_5V_OUT", ["+5V", "GND"]),
        ],
        "A4/A5 are TFT GPIO; D20/D21 are the separate UNO Q I2C header pins.",
    )
    write_project_file(out_dir / "ichiping_uno_q_shield.kicad_pro")
    return out_dir


def new_board(width: float, height: float) -> pcbnew.BOARD:
    board = pcbnew.BOARD()
    for start, end in [((0, 0), (width, 0)), ((width, 0), (width, height)), ((width, height), (0, height)), ((0, height), (0, 0))]:
        edge = pcbnew.PCB_SHAPE(board)
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetStart(vec(*start))
        edge.SetEnd(vec(*end))
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetWidth(mm(0.05))
        board.Add(edge)
    return board


def generate_audio_board() -> Path:
    print("audio: start", flush=True)
    out_dir = ROOT / "audio_shield"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Keep the carrier header coordinates fixed and extend the PCB to the
    # right, so every cable connector sits beyond J15 rather than underneath
    # the carrier body on the left side.
    board = new_board(79.0, 53.34)
    print("audio: board", flush=True)
    board.SetFileName(str(out_dir / "ichiping_uno_q_audio_shield.kicad_pcb"))

    # Carrier coordinates translated by -61.60 mm from the official drawing.
    # Header center lines: J14=86.04 mm, J15=101.28 mm on the 107.60 mm carrier.
    j14 = load_footprint(
        board,
        "Connector_PinSocket_2.54mm",
        "PinSocket_2x20_P2.54mm_Vertical",
        "J14",
        "UNO Breakout Carrier J14",
        23.17,
        2.54,
    )
    j15 = load_footprint(
        board,
        "Connector_PinSocket_2.54mm",
        "PinSocket_2x20_P2.54mm_Vertical",
        "J15",
        "UNO Breakout Carrier J15",
        38.41,
        2.54,
    )
    print("audio: carrier headers", flush=True)

    carrier_nets = [
        ((j14, "5"), "GND"),
        ((j14, "6"), "GND"),
        ((j14, "7"), "+5V"),
        ((j14, "9"), "+5V"),
        ((j14, "13"), "+3V3"),
        ((j14, "15"), "+3V3"),
        ((j14, "19"), "+1V8"),
        ((j14, "21"), "+1V8"),
        ((j15, "23"), "GND"),
        ((j15, "30"), "GND"),
        ((j15, "32"), "MI2S0_CLK"),
        ((j15, "34"), "MI2S0_WS"),
        ((j15, "36"), "MI2S0_DATA0"),
        ((j15, "38"), "MI2S0_DATA1"),
        ((j15, "40"), "GND"),
    ]
    header: dict[str, pcbnew.PAD] = {}
    for (footprint, number), net_name in carrier_nets:
        pad = set_pad_net(board, footprint, number, net_name)
        header.setdefault(net_name, pad)

    # Join duplicated carrier power pins so every assigned pad is electrically
    # connected and no unused power-pin ratsnest remains after import.
    for footprint, first, second, net_name, width in [
        (j14, "5", "6", "GND", 0.50),
        (j14, "7", "9", "+5V", 0.80),
        (j14, "13", "15", "+3V3", 0.50),
        (j14, "19", "21", "+1V8", 0.50),
        (j15, "23", "30", "GND", 0.50),
        (j15, "30", "40", "GND", 0.50),
    ]:
        route_direct(board, net_name, find_pad(footprint, first), find_pad(footprint, second), pcbnew.B_Cu, width)

    _, amp_sig = add_xh(board, "J_AMP_SIG", ["MI2S0_WS", "MI2S0_CLK", "MI2S0_DATA1", "AMP_GAIN"], 61.0, 10.0)
    _, amp_pwr = add_xh(board, "J_AMP_PWR", ["AMP_SD", "GND", "+5V"], 61.0, 23.5)
    _, mic = add_xh(board, "J_MIC", ["GND", "+1V8", "MI2S0_DATA0", "MI2S0_CLK", "MI2S0_WS", "MIC_LR"], 61.0, 36.5)
    print("audio: xh", flush=True)

    # All configurable and decoupling parts are through-hole for hand
    # assembly. Fixed defaults are GAIN=GND, MIC L/R=GND, and SD pulled up.
    resistor_fp = "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
    r_gain = load_footprint(board, "Resistor_THT", resistor_fp, "R_GAIN", "0R GAIN=GND", 44.0, 16.0, 90)
    set_pad_net(board, r_gain, "1", "AMP_GAIN")
    set_pad_net(board, r_gain, "2", "GND")
    r_lr = load_footprint(board, "Resistor_THT", resistor_fp, "R_LR", "0R MIC_LR=GND", 48.0, 49.0, 90)
    set_pad_net(board, r_lr, "1", "MIC_LR")
    set_pad_net(board, r_lr, "2", "GND")
    r_sd = load_footprint(board, "Resistor_THT", resistor_fp, "R_SD", "100k SD pull-up", 49.0, 23.5, 90)
    set_pad_net(board, r_sd, "1", "AMP_SD")
    set_pad_net(board, r_sd, "2", "+3V3")
    jp_mute = load_footprint(
        board,
        "Connector_PinHeader_2.54mm",
        "PinHeader_1x02_P2.54mm_Vertical",
        "JP_MUTE",
        "AMP SD MUTE (OPEN)",
        55.0,
        25.0,
    )
    set_pad_net(board, jp_mute, "1", "AMP_SD")
    set_pad_net(board, jp_mute, "2", "GND")

    # Local rail decoupling at the cable connectors.
    caps = [
        ("C1", "10u 10V", "+5V", 48.0, 33.0, "CP_Radial_D5.0mm_P2.00mm"),
        ("C2", "100n", "+5V", 54.0, 33.0, "C_Disc_D5.0mm_W2.5mm_P5.00mm"),
        ("C3", "100n", "+1V8", 54.0, 47.5, "C_Disc_D5.0mm_W2.5mm_P5.00mm"),
    ]
    for reference, value, supply, x, y, footprint_name in caps:
        capacitor = load_footprint(board, "Capacitor_THT", footprint_name, reference, value, x, y)
        set_pad_net(board, capacitor, "1", supply)
        set_pad_net(board, capacitor, "2", "GND")
    print("audio: parts", flush=True)

    # Shared clock and word-select buses, then short branches to both XH headers.
    for net, y_bus in [("MI2S0_CLK", 34.0), ("MI2S0_WS", 36.0)]:
        hx, hy = pad_xy(header[net])
        add_track(board, net, [(hx, hy), (44.0, hy), (44.0, y_bus), (57.0, y_bus)], pcbnew.F_Cu)
        for target in (amp_sig[net], mic[net]):
            tx, ty = pad_xy(target)
            add_track(board, net, [(57.0, y_bus), (tx, y_bus), (tx, ty)], pcbnew.F_Cu)

    route_direct(board, "MI2S0_DATA1", header["MI2S0_DATA1"], amp_sig["MI2S0_DATA1"], pcbnew.B_Cu)
    route_direct(board, "MI2S0_DATA0", header["MI2S0_DATA0"], mic["MI2S0_DATA0"], pcbnew.B_Cu)
    route_direct(board, "AMP_GAIN", amp_sig["AMP_GAIN"], find_pad(r_gain, "1"), pcbnew.F_Cu)
    route_direct(board, "MIC_LR", mic["MIC_LR"], find_pad(r_lr, "1"), pcbnew.F_Cu)

    # Power distribution.
    route_dogleg(board, "+5V", header["+5V"], amp_pwr["+5V"], pcbnew.B_Cu, 31.5, 0.50)
    route_dogleg(board, "+1V8", header["+1V8"], mic["+1V8"], pcbnew.B_Cu, 46.5, 0.50)
    route_direct(board, "AMP_SD", find_pad(r_sd, "1"), amp_pwr["AMP_SD"], pcbnew.F_Cu)
    route_direct(board, "+3V3", find_pad(r_sd, "2"), header["+3V3"], pcbnew.B_Cu, 0.50)
    route_direct(board, "AMP_SD", find_pad(jp_mute, "1"), amp_pwr["AMP_SD"], pcbnew.F_Cu)

    for reference, _, supply, _, _, _ in caps:
        cap = board_footprints(board)[reference]
        route_direct(board, supply, find_pad(cap, "1"), header[supply], pcbnew.B_Cu, 0.50)

    polygon = [(0.6, 0.6), (78.4, 0.6), (78.4, 52.74), (0.6, 52.74)]
    add_zone(board, "GND", pcbnew.F_Cu, polygon)
    add_zone(board, "GND", pcbnew.B_Cu, polygon)
    print("audio: routes", flush=True)

    add_text(board, "IchiPing AUDIO", 9.0, 4.0, 1.0, bold=True)
    add_text(board, "I2S=1V8  ALL PARTS THT", 12.0, 7.0, 0.8)
    add_text(board, "AMP SIG: LRC BCLK DIN GAIN", 60.0, 6.0, 0.80)
    add_text(board, "AMP PWR: SD GND VIN(5V)", 60.0, 20.0, 0.80)
    add_text(board, "MIC: G 1V8 SD CK WS LR", 65.0, 41.5, 0.80)
    add_text(board, "MUTE", 55.0, 21.5, 0.80)
    add_text(board, "REV B 2026-08-25", 12.0, 52.0, 0.80, layer=pcbnew.B_SilkS)

    prepare_for_autorouter(board)
    configure_netclasses(board)
    strip_footprint_silks(board)
    print("audio: save for autorouter", flush=True)
    pcbnew.SaveBoard(str(out_dir / "ichiping_uno_q_audio_shield.kicad_pcb"), board)
    write_audio_schematic(out_dir / "ichiping_uno_q_audio_shield.sch")
    write_audio_cache_library(out_dir / "ichiping_uno_q_audio_shield-cache.lib")
    write_project_file(out_dir / "ichiping_uno_q_audio_shield.kicad_pro")
    return out_dir


def write_audio_schematic(path: Path) -> None:
    """Write the complete audio-shield circuit as a KiCad legacy schematic."""
    lines = [
        "EESchema Schematic File Version 4",
        "LIBS:ichiping_uno_q_audio_shield-cache",
        "LIBS:power",
        "LIBS:device",
        "LIBS:Connector_Generic",
        "EELAYER 29 0",
        "EELAYER END",
        "$Descr A4 11693 8268",
        "Sheet 1 1",
        'Title "IchiPing UNO Q Audio Shield"',
        'Date "2026-08-25"',
        'Rev "B"',
        'Comp "IchiPing UNO Q"',
        'Comment1 "Complete circuit; all discrete parts are through-hole"',
        "$EndDescr",
        "Text Notes 700 650 0    100  ~ 20",
        "IchiPing UNO Q Audio Shield - complete circuit",
        "Text Notes 700 900 0    55   ~ 11",
        "QRB2210 MI2S0 is 1.8 V logic. Confirm Device Tree and ALSA direction before fitting modules.",
    ]

    def component(
        library_id: str,
        reference: str,
        value: str,
        footprint: str,
        x: int,
        y: int,
        orientation: str = "1 0 0 -1",
    ) -> None:
        component_id = uuid.uuid4().int & 0xFFFFFFFF
        lines.extend(
            [
                "$Comp",
                f"L {library_id} {reference}",
                f"U 1 1 {component_id:08X}",
                f"P {x} {y}",
                f'F 0 "{reference}" H {x+200} {y+150} 50  0000 C CNN',
                f'F 1 "{value}" H {x+350} {y-150} 50  0000 C CNN',
                f'F 2 "{footprint}" H {x} {y} 50  0001 C CNN',
                f'F 3 "~" H {x} {y} 50  0001 C CNN',
                f"\t1    {x} {y}",
                f"\t{orientation}",
                "$EndComp",
            ]
        )

    def label_wire(x1: int, y1: int, x2: int, y2: int, net: str) -> None:
        lines.extend(
            [
                f"Wire Wire Line\n\t{x1} {y1} {x2} {y2}",
                f"Text Label {x2} {y2} 0    45   ~ 0\n{net}",
            ]
        )

    # Breakout Carrier sockets retain their physical pin numbers. Every
    # unused pin is explicitly marked no-connect so the schematic is useful
    # for both wiring review and ERC.
    carrier_connectors = [
        (
            "J14",
            1700,
            3000,
            {
                5: "GND",
                6: "GND",
                7: "+5V",
                9: "+5V",
                13: "+3V3",
                15: "+3V3",
                19: "+1V8",
                21: "+1V8",
            },
        ),
        (
            "J15",
            4000,
            3000,
            {
                23: "GND",
                30: "GND",
                32: "MI2S0_CLK",
                34: "MI2S0_WS",
                36: "MI2S0_DATA0",
                38: "MI2S0_DATA1",
                40: "GND",
            },
        ),
    ]
    socket_fp = "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical"
    for reference, x, y, used_pins in carrier_connectors:
        component("Connector_Generic:Conn_02x20_Odd_Even", reference, "UNO Breakout Carrier", socket_fp, x, y)
        for pin in range(1, 41):
            row_y = y - 900 + ((pin - 1) // 2) * 100
            pin_x = x - 200 if pin % 2 else x + 300
            if pin in used_pins:
                end_x = pin_x - 450 if pin % 2 else pin_x + 450
                label_wire(pin_x, row_y, end_x, row_y, used_pins[pin])
            else:
                lines.append(f"NoConn ~ {pin_x} {row_y}")

    def xh(reference: str, count: int, x: int, y: int, nets: list[str]) -> None:
        component(
            f"Connector_Generic:Conn_01x{count:02d}",
            reference,
            f"XH2.54_VERTICAL_{count}",
            f"Connector_PinHeader_2.54mm:PinHeader_1x{count:02d}_P2.54mm_Vertical",
            x,
            y,
            "-1 0 0 1",
        )
        first_y = y + ((count - 1) // 2) * 100
        for index, net in enumerate(nets):
            pin_y = first_y - index * 100
            label_wire(x + 200, pin_y, x + 650, pin_y, net)
            lines.extend([f"Text Notes {x-850} {pin_y+15} 0    40   ~ 0", f"{index+1}: {net}"])

    xh("J_AMP_SIG", 4, 6700, 1650, ["MI2S0_WS", "MI2S0_CLK", "MI2S0_DATA1", "AMP_GAIN"])
    xh("J_AMP_PWR", 3, 6700, 2850, ["AMP_SD", "GND", "+5V"])
    xh("J_MIC", 6, 6700, 4300, ["GND", "+1V8", "MI2S0_DATA0", "MI2S0_CLK", "MI2S0_WS", "MIC_LR"])

    resistor_fp = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
    for reference, value, y, left_net, right_net in [
        ("R_GAIN", "0R GAIN=GND", 1700, "AMP_GAIN", "GND"),
        ("R_SD", "100k SD pull-up", 2500, "AMP_SD", "+3V3"),
        ("R_LR", "0R MIC_LR=GND", 4700, "MIC_LR", "GND"),
    ]:
        component("Device:R", reference, value, resistor_fp, 9000, y, "0 -1 -1 0")
        label_wire(8850, y, 8500, y, left_net)
        label_wire(9150, y, 9500, y, right_net)

    component(
        "Connector_Generic:Conn_01x02",
        "JP_MUTE",
        "AMP SD MUTE (OPEN)",
        "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        9000,
        3200,
        "-1 0 0 1",
    )
    label_wire(9200, 3200, 9500, 3200, "AMP_SD")
    label_wire(9200, 3100, 9500, 3100, "GND")

    for library_id, reference, value, footprint, x, y, supply in [
        ("Device:C_Polarized", "C1", "10u 10V", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", 8400, 3900, "+5V"),
        ("Device:C", "C2", "100n", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm", 9300, 3900, "+5V"),
        ("Device:C", "C3", "100n", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm", 10200, 3900, "+1V8"),
    ]:
        component(library_id, reference, value, footprint, x, y)
        label_wire(x, y - 150, x, y - 350, supply)
        label_wire(x, y + 150, x, y + 350, "GND")

    lines.extend(
        [
            "Text Notes 8050 1250 0    60   ~ 12",
            "Configuration and decoupling (THT)",
            "Text Notes 8050 5200 0    50   ~ 10",
            "JP_MUTE open: amplifier enabled by R_SD. Fit shunt: SD forced Low / mute.",
            "Text Notes 700 5600 0    50   ~ 10",
            "J14: 5/6=GND, 7/9=+5V, 13/15=+3V3, 19/21=+1V8",
            "Text Notes 700 5850 0    50   ~ 10",
            "J15: 23/30/40=GND, 32=CLK, 34=WS, 36=DATA0(mic), 38=DATA1(amp)",
            "$EndSCHEMATC",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_audio_cache_library(path: Path) -> None:
    """Embed the small symbol set needed by legacy KiCad/EasyEDA import."""
    lines = ["EESchema-LIBRARY Version 2.4", "#encoding utf-8"]

    def connector(name: str, count: int) -> None:
        first_y = ((count - 1) // 2) * 100
        last_y = first_y - (count - 1) * 100
        lines.extend(
            [
                "#",
                f"# {name}",
                "#",
                f"DEF {name} J 0 40 Y N 1 F N",
                'F0 "J" 50 0 50 H V L CNN',
                f'F1 "{name}" 50 -100 50 H V L CNN',
                "DRAW",
                f"S -50 {first_y + 50} 0 {last_y - 50} 1 1 10 f",
            ]
        )
        for pin in range(1, count + 1):
            pin_y = first_y - (pin - 1) * 100
            lines.append(f"X Pin_{pin} {pin} -200 {pin_y} 150 R 50 50 1 1 P")
        lines.extend(["ENDDRAW", "ENDDEF"])

    def connector_2x20() -> None:
        lines.extend(
            [
                "#",
                "# Conn_02x20_Odd_Even",
                "#",
                "DEF Conn_02x20_Odd_Even J 0 40 Y N 1 F N",
                'F0 "J" 50 1050 50 H V C CNN',
                'F1 "Conn_02x20_Odd_Even" 50 -1050 50 H V C CNN',
                "DRAW",
                "S -50 950 150 -1050 1 1 10 f",
            ]
        )
        for row in range(20):
            pin_y = 900 - row * 100
            odd = row * 2 + 1
            even = odd + 1
            lines.append(f"X Pin_{odd} {odd} -200 {pin_y} 150 R 50 50 1 1 P")
            lines.append(f"X Pin_{even} {even} 300 {pin_y} 150 L 50 50 1 1 P")
        lines.extend(["ENDDRAW", "ENDDEF"])

    connector_2x20()
    for count in (2, 3, 4, 6):
        connector(f"Conn_01x{count:02d}", count)

    lines.extend(
        [
            "#",
            "# R",
            "#",
            "DEF R R 0 0 N Y 1 F N",
            'F0 "R" 80 0 50 V V C CNN',
            'F1 "R" 0 0 50 V V C CNN',
            "DRAW",
            "S -40 -100 40 100 0 1 12 N",
            "X ~ 1 0 150 50 D 50 50 1 1 P",
            "X ~ 2 0 -150 50 U 50 50 1 1 P",
            "ENDDRAW",
            "ENDDEF",
            "#",
            "# C",
            "#",
            "DEF C C 0 10 N Y 1 F N",
            'F0 "C" 25 100 50 H V L CNN',
            'F1 "C" 25 -100 50 H V L CNN',
            "DRAW",
            "P 2 0 1 20 -80 -30 80 -30 N",
            "P 2 0 1 20 -80 30 80 30 N",
            "X ~ 1 0 150 120 D 50 50 1 1 P",
            "X ~ 2 0 -150 120 U 50 50 1 1 P",
            "ENDDRAW",
            "ENDDEF",
            "#",
            "# C_Polarized",
            "#",
            "DEF C_Polarized C 0 10 N Y 1 F N",
            'F0 "C" 25 100 50 H V L CNN',
            'F1 "C_Polarized" 25 -100 50 H V L CNN',
            "DRAW",
            "P 2 0 1 20 -80 -30 80 -30 N",
            "P 2 0 1 20 -80 30 80 30 N",
            "P 2 0 1 0 -50 60 -10 60 N",
            "P 2 0 1 0 -30 40 -30 80 N",
            "X ~ 1 0 150 120 D 50 50 1 1 P",
            "X ~ 2 0 -150 120 U 50 50 1 1 P",
            "ENDDRAW",
            "ENDDEF",
            "#End Library",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_project_file(path: Path) -> None:
    project = {
        "board": {},
        "boards": [],
        "cvpcb": {},
        "erc": {},
        "libraries": {},
        "meta": {"filename": path.name, "version": 1},
        "net_settings": {"classes": [{"name": "Default", "clearance": 0.25, "track_width": 0.25, "via_diameter": 0.9, "via_drill": 0.5}]},
        "pcbnew": {},
        "schematic": {},
        "text_variables": {},
    }
    path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")


def write_legacy_schematic(path: Path, title: str, connectors: list[tuple[str, list[str]]], note: str) -> None:
    """Write an import-friendly KiCad legacy schematic with explicit pin labels."""
    lines = [
        "EESchema Schematic File Version 4",
        "LIBS:power",
        "LIBS:device",
        "LIBS:Connector_Generic",
        "EELAYER 29 0",
        "EELAYER END",
        "$Descr A4 11693 8268",
        "Sheet 1 1",
        f'Title "{title}"',
        'Date "2026-08-24"',
        'Rev "A"',
        'Comp "IchiPing UNO Q"',
        'Comment1 "XH2.54 vertical pin order is top-view pin 1 to pin N"',
        "$EndDescr",
        f"Text Notes 900 800 0    100  ~ 20\n{title}",
        f"Text Notes 900 1050 0    60   ~ 12\n{note}",
    ]
    x_positions = [1700, 4300, 6900]
    for index, (reference, pin_names) in enumerate(connectors):
        column = index % 3
        row = index // 3
        x = x_positions[column]
        y = 1700 + row * 1700
        count = len(pin_names)
        unit_uuid = uuid.uuid4().int & 0xFFFFFFFF
        lines.extend(
            [
                "$Comp",
                f"L Connector_Generic:Conn_01x{count:02d} {reference}",
                f"U 1 1 {unit_uuid:08X}",
                f"P {x} {y}",
                f'F 0 "{reference}" H {x-120} {y+350} 50  0000 C CNN',
                f'F 1 "XH2.54_VERTICAL_{count}" H {x-120} {y-350} 50  0000 C CNN',
                f'F 2 "Connector_PinHeader_2.54mm:PinHeader_1x{count:02d}_P2.54mm_Vertical" H {x} {y} 50  0001 C CNN',
                'F 3 "~" H {x} {y} 50  0001 C CNN'.format(x=x, y=y),
                f"\t1    {x} {y}",
                "\t-1   0    0    1",
                "$EndComp",
            ]
        )
        first_y = y - (count - 1) * 50
        for pin_index, net_name in enumerate(pin_names, start=1):
            pin_y = first_y + (pin_index - 1) * 100
            lines.extend(
                [
                    f"Wire Wire Line\n\t{x+100} {pin_y} {x+650} {pin_y}",
                    f"Text Label {x+300} {pin_y} 0    45   ~ 0\n{net_name}",
                    f"Text Notes {x-900} {pin_y+15} 0    45   ~ 0\n{pin_index}: {net_name}",
                ]
            )
    lines.extend(["$EndSCHEMATC", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    for path in (ROOT / "uno_shield", ROOT / "audio_shield"):
        if path.exists():
            shutil.rmtree(path)
    uno = generate_uno_board()
    audio = generate_audio_board()
    print(uno)
    print(audio)


if __name__ == "__main__":
    main()
