"""Export KiCad PCBs to Specctra DSN or import Freerouting SES results."""

from __future__ import annotations

import argparse
from pathlib import Path
import math

import pcbnew


def nudge_uno_edge_vias(board: pcbnew.BOARD) -> None:
    """Keep routed vias at least 0.5 mm copper-clear of the UNO lower edge."""
    if "uno_q_shield" not in Path(board.GetFileName()).stem:
        return
    for item in list(board.GetTracks()):
        if not isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() != "A5":
            continue
        old = item.GetPosition()
        if pcbnew.ToMM(old.y) <= 99.0:
            continue
        new = pcbnew.VECTOR2I(old.x, pcbnew.FromMM(98.8))
        for track in list(board.GetTracks()):
            if isinstance(track, pcbnew.PCB_VIA):
                continue
            start = track.GetStart()
            end = track.GetEnd()
            if start.x == old.x and start.y == old.y:
                track.SetStart(new)
            if end.x == old.x and end.y == old.y:
                track.SetEnd(new)
        item.SetPosition(new)


def add_ground_zones(board: pcbnew.BOARD) -> None:
    net = board.FindNet("GND")
    if net is None:
        return
    is_uno = "uno_q_shield" in Path(board.GetFileName()).stem
    if is_uno:
        # Keep the pour inside the four mounting-hole clearance envelopes.
        # This avoids relying on importer-specific zone-hole serialization.
        polygon = [(118.0, 52.0), (163.5, 52.0), (163.5, 89.8), (118.0, 89.8)]
        holes = []
    else:
        polygon = [(0.6, 0.6), (45.4, 0.6), (45.4, 52.74), (0.6, 52.74)]
        holes = []
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(net)
        # 0.30 mm leaves margin above EasyEDA Pro's 10 mil default after
        # KiCad-to-EasyEDA coordinate rounding.
        zone.SetLocalClearance(pcbnew.FromMM(0.30))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        outline = zone.Outline()
        outline.NewOutline()
        for x, y in polygon:
            outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        for cx, cy in holes:
            outline.NewHole()
            for index in range(24):
                angle = -2.0 * math.pi * index / 24
                outline.Append(
                    pcbnew.FromMM(cx + 2.2 * math.cos(angle)),
                    pcbnew.FromMM(cy + 2.2 * math.sin(angle)),
                )
        board.Add(zone)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("export", "import"))
    parser.add_argument("board", type=Path)
    parser.add_argument("route_file", type=Path)
    args = parser.parse_args()

    board = pcbnew.LoadBoard(str(args.board.resolve()))
    if args.mode == "export":
        if not pcbnew.ExportSpecctraDSN(board, str(args.route_file.resolve())):
            raise SystemExit("Specctra DSN export failed")
        return

    if not pcbnew.ImportSpecctraSES(board, str(args.route_file.resolve())):
        raise SystemExit("Specctra SES import failed")
    # Keep the router geometry intact. Moving a via after routing can make the
    # two attached segments cross an adjacent trace; the generated placement
    # already keeps pads and vias inside the UNO outline.
    add_ground_zones(board)
    # The generated PCB is self-contained and includes deliberately customized
    # XH2.54 footprints. Detach library links only after SES import, because
    # KiCad uses them while resolving the Specctra component images.
    for footprint in board.GetFootprints():
        footprint.SetFPID(pcbnew.LIB_ID())
    pcbnew.SaveBoard(str(args.board.resolve()), board)


if __name__ == "__main__":
    main()
