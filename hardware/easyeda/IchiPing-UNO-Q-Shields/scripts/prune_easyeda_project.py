"""Keep only the two canonical schematic/PCB Boards in the EasyEDA project tree.

Historical snapshots remain in the project database for recovery. The current
structure and preview images are pruned to the canonical UNO and audio Boards.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[4] / "board" / "Ichiping uno q.eprj2"
CANONICAL_BOARDS = {"ichiping_uno_q_shield", "ichiping_uno_q_audio_shield"}
CANONICAL_SCHEMATICS = {
    "ichiping_uno_q_shield_schematic",
    "ichiping_uno_q_audio_shield_schematic",
}


def item_name(item: dict) -> str | None:
    return item.get("title") or item.get("name")


def main() -> None:
    if not PROJECT.is_file():
        raise FileNotFoundError(PROJECT)
    connection = sqlite3.connect(PROJECT)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row_id, raw = connection.execute(
            "SELECT id, structure FROM project_structures ORDER BY id DESC LIMIT 1"
        ).fetchone()
        structure = json.loads(raw)
        structure["boards"] = {
            uuid: item for uuid, item in structure.get("boards", {}).items()
            if item_name(item) in CANONICAL_BOARDS
        }
        board_uuids = set(structure["boards"])
        structure["pcbs"] = {
            uuid: item for uuid, item in structure.get("pcbs", {}).items()
            if item_name(item) in CANONICAL_BOARDS
            and item.get("board") in board_uuids
        }
        structure["schematics"] = {
            uuid: item for uuid, item in structure.get("schematics", {}).items()
            if item_name(item) in CANONICAL_SCHEMATICS
            and item.get("board") in board_uuids
        }
        schematic_uuids = set(structure["schematics"])
        structure["sheets"] = {
            uuid: item for uuid, item in structure.get("sheets", {}).items()
            if item.get("schematic_uuid") in schematic_uuids
        }
        structure["panels"] = {}
        connection.execute(
            "UPDATE project_structures SET structure = ? WHERE id = ?",
            (json.dumps(structure, ensure_ascii=False, separators=(",", ":")), row_id),
        )
        document_uuids = tuple(
            set(structure["pcbs"]) | set(structure["sheets"])
        )
        placeholders = ",".join("?" for _ in document_uuids)
        connection.execute(
            f"DELETE FROM project_images WHERE uuid NOT IN ({placeholders})",
            document_uuids,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    verify = sqlite3.connect(f"file:{PROJECT}?mode=ro", uri=True)
    latest = json.loads(verify.execute(
        "SELECT structure FROM project_structures ORDER BY id DESC LIMIT 1"
    ).fetchone()[0])
    verify.close()
    result = {section: [item_name(item) for item in latest[section].values()]
              for section in ("boards", "schematics", "sheets", "pcbs")}
    if (set(result["boards"]) != CANONICAL_BOARDS
            or set(result["pcbs"]) != CANONICAL_BOARDS):
        raise AssertionError(result)
    if set(result["schematics"]) != CANONICAL_SCHEMATICS:
        raise AssertionError(result)
    if len(result["sheets"]) != 2 or set(result["sheets"]) != {"Main"}:
        raise AssertionError(result)
    print(result)


if __name__ == "__main__":
    main()
