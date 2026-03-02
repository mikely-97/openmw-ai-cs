"""Export records from SQLite to JSON.

Usage:
    from omwtools.json_io.export_ import export_records_to_json
    json_str = export_records_to_json(conn, mod_id=1)
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from omwtools.io.refid import refid_from_db_text
from omwtools.records import parse_record, RECORD_REGISTRY
from omwtools.records.base import RawRecord, RawSubrecord
from omwtools.records.unknown import UnknownRecord


def export_records_to_json(
    conn: sqlite3.Connection,
    mod_id: Optional[int] = None,
    rec_type: Optional[str] = None,
    record_id: Optional[str] = None,
    indent: int = 2,
) -> str:
    """Export records from the database as a JSON string.

    Parameters
    ----------
    conn:        SQLite connection.
    mod_id:      If given, only export records from that mod.
    rec_type:    If given, only export records of that type (e.g. "NPC_").
    record_id:   If given, only export the record with that ID text.
    indent:      JSON indentation level.

    Returns
    -------
    str — JSON array of record dicts.
    """
    conditions = []
    params: list[Any] = []

    if mod_id is not None:
        conditions.append("mod_id=?")
        params.append(mod_id)
    if rec_type is not None:
        conditions.append("rec_type=?")
        params.append(rec_type)
    if record_id is not None:
        conditions.append("record_id_text=?")
        params.append(record_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM records {where} ORDER BY sort_order",
        params,
    ).fetchall()

    records: list[dict[str, Any]] = []
    for row in rows:
        # Try to reconstruct typed record from raw_blob
        raw_blob = row["raw_blob"]
        rt = row["rec_type"].encode("ascii")[:4]
        if raw_blob is not None:
            raw = _blob_to_raw(rt, raw_blob, row["flags"], row["raw_blob"] or b"")
            record = parse_record(raw, 0)
            d = record.to_dict()
        else:
            # Pull from satellite table by record type
            d = _export_from_satellite(conn, row)

        d["_record_id"] = row["record_id_text"]
        d["_sort_order"] = row["sort_order"]
        d["_mod_id"] = row["mod_id"]
        records.append(d)

    return json.dumps(records, indent=indent, ensure_ascii=False)


def _blob_to_raw(
    rec_type: bytes, raw_data: bytes, flags: int, raw_blob: bytes
) -> RawRecord:
    from omwtools.io.codec import unpack_subrec_header, SUBREC_HEADER_SIZE
    subs: list[RawSubrecord] = []
    pos = 0
    while pos + SUBREC_HEADER_SIZE <= len(raw_data):
        sub_type, size = unpack_subrec_header(raw_data, pos)
        pos += SUBREC_HEADER_SIZE
        sub_data = raw_data[pos: pos + size]
        pos += size
        subs.append(RawSubrecord(sub_type, sub_data))
    return RawRecord(rec_type, flags, 0, raw_data, subs)


def _export_from_satellite(
    conn: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, Any]:
    """Export record fields from satellite tables (typed records)."""
    rec_type = row["rec_type"]
    rec_id = row["id"]

    if rec_type == "NPC_":
        npc = conn.execute("SELECT * FROM npcs WHERE record_id=?", (rec_id,)).fetchone()
        if npc:
            attrs = json.loads(npc["attributes_json"]) if npc["attributes_json"] else []
            skills = json.loads(npc["skills_json"]) if npc["skills_json"] else []
            d: dict[str, Any] = {
                "rec_type": "NPC_",
                "record_id": row["record_id_text"],
                "mesh": npc["mesh"],
                "name": npc["name"],
                "race": npc["race"],
                "class_id": npc["class_id"],
                "faction": npc["faction"],
                "head": npc["head"],
                "hair": npc["hair"],
                "script": npc["script"],
                "npc_flags": npc["npc_flags"],
                "flags": row["flags"],
            }
            if npc["is_autocalc"]:
                d["npdt_autocalc"] = {
                    "level": npc["level"], "disposition": npc["disposition"],
                    "reputation": npc["reputation"], "rank": npc["rank"],
                    "gold": npc["gold"],
                }
            else:
                d["npdt_full"] = {
                    "level": npc["level"], "attributes": attrs, "skills": skills,
                    "health": npc["health"], "mana": npc["mana"],
                    "fatigue": npc["fatigue"], "disposition": npc["disposition"],
                    "reputation": npc["reputation"], "rank": npc["rank"],
                    "gold": npc["gold"],
                }
            inv = conn.execute(
                "SELECT * FROM npc_inventory WHERE npc_id=? ORDER BY sort_order",
                (rec_id,),
            ).fetchall()
            d["inventory"] = [{"count": r["count"], "item_id": r["item_id"]} for r in inv]
            spells = conn.execute(
                "SELECT * FROM npc_spells WHERE npc_id=? ORDER BY sort_order",
                (rec_id,),
            ).fetchall()
            d["spells"] = [r["spell_id"] for r in spells]
            d["ai_data"] = {
                "hello": npc["ai_hello"], "fight": npc["ai_fight"],
                "flee": npc["ai_flee"], "alarm": npc["ai_alarm"],
                "services": npc["ai_services"],
            }
            pkgs = conn.execute(
                "SELECT * FROM npc_ai_packages WHERE npc_id=? ORDER BY sort_order",
                (rec_id,),
            ).fetchall()
            d["ai_packages"] = [{"type": r["package_type"], "raw_hex": r["raw_hex"]}
                                 for r in pkgs]
            trans = conn.execute(
                "SELECT * FROM npc_transport WHERE npc_id=? ORDER BY sort_order",
                (rec_id,),
            ).fetchall()
            d["transport"] = [{"pos_x": r["pos_x"], "pos_y": r["pos_y"], "pos_z": r["pos_z"],
                                "rot_x": r["rot_x"], "rot_y": r["rot_y"], "rot_z": r["rot_z"],
                                "cell_name": r["cell_name"]}
                               for r in trans]
            return d

    if rec_type == "CELL":
        cell = conn.execute("SELECT * FROM cells WHERE record_id=?", (rec_id,)).fetchone()
        if cell:
            d = {
                "rec_type": "CELL",
                "cell_name": cell["cell_name"],
                "cell_flags": cell["cell_flags"],
                "grid_x": cell["grid_x"],
                "grid_y": cell["grid_y"],
                "region": cell["region"],
                "ref_num_counter": cell["ref_num_counter"],
                "water_height": cell["water_height"],
                "flags": row["flags"],
            }
            if cell["ambient"] is not None:
                d["ambient"] = {
                    "ambient": cell["ambient"],
                    "sunlight": cell["sunlight"],
                    "fog": cell["fog"],
                    "fog_density": cell["fog_density"],
                }
            refs = conn.execute(
                "SELECT * FROM cell_refs WHERE cell_id=? ORDER BY sort_order",
                (rec_id,),
            ).fetchall()
            def _ref_dict(r: sqlite3.Row) -> dict:
                d2: dict = {
                    "ref_num": r["ref_num"],
                    "object_id": r["object_id"],
                    "scale": r["scale"],
                    "pos": [r["pos_x"], r["pos_y"], r["pos_z"]],
                    "rot": [r["rot_x"], r["rot_y"], r["rot_z"]],
                    "is_deleted": bool(r["is_deleted"]),
                    "is_blocked": bool(r["is_blocked"]),
                    "soul": r["soul"],
                    "owner": r["owner"],
                    "owner_rank": r["owner_rank"],
                    "owner_global": r["owner_global"],
                    "key_id": r["key_id"],
                    "trap_id": r["trap_id"],
                    "enchant_charge": r["enchant_charge"],
                    "charge_int": r["charge_int"],
                    "lock_level": r["lock_level"],
                    "dest_cell": r["dest_cell"],
                }
                if r["dest_pos_x"] is not None:
                    d2["dest_pos"] = [r["dest_pos_x"], r["dest_pos_y"], r["dest_pos_z"]]
                    d2["dest_rot"] = [r["dest_rot_x"], r["dest_rot_y"], r["dest_rot_z"]]
                return d2
            d["refs"] = [_ref_dict(r) for r in refs]
            return d

    if rec_type == "SCPT":
        scpt = conn.execute("SELECT * FROM scripts WHERE record_id=?", (rec_id,)).fetchone()
        if scpt:
            return {
                "rec_type": "SCPT",
                "script_name": scpt["script_name"],
                "num_shorts": scpt["num_shorts"],
                "num_longs": scpt["num_longs"],
                "num_floats": scpt["num_floats"],
                "local_vars": json.loads(scpt["local_vars_json"]),
                "bytecode_hex": scpt["bytecode_hex"],
                "source_text": scpt["source_text"],
                "has_scdt": bool(scpt["has_scdt"]),
                "flags": row["flags"],
            }

    if rec_type == "INFO":
        info = conn.execute(
            "SELECT data_json FROM dialogue_infos WHERE record_id=?", (rec_id,)
        ).fetchone()
        if info:
            return json.loads(info["data_json"])

    # Generic Phase 2 typed records stored in typed_records.data_json
    typed = conn.execute(
        "SELECT data_json FROM typed_records WHERE record_id=?", (rec_id,)
    ).fetchone()
    if typed:
        return json.loads(typed["data_json"])

    return {
        "rec_type": rec_type,
        "record_id": row["record_id_text"],
        "flags": row["flags"],
    }
