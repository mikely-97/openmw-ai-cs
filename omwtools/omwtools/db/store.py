"""ModStore — the main API class for loading mods into SQLite and querying them.

Usage:
    import sqlite3
    from omwtools.db.connection import make_db
    from omwtools.db.store import ModStore

    conn = make_db("my.db")
    store = ModStore(conn)
    mod_id = store.load_file("Morrowind.esm")
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Iterator, Optional

from omwtools.io.reader import ESMReader
from omwtools.io.refid import refid_to_db_text
from omwtools.records import parse_record, RECORD_REGISTRY
from omwtools.records.base import BaseRecord, RawRecord
from omwtools.records.unknown import UnknownRecord
from omwtools.records.tes3 import TES3Header, FILE_TYPE_GAME
from omwtools.records.npc_ import NPC
from omwtools.records.cell import Cell
from omwtools.records.scpt import Script
from omwtools.records.lual import LUALRecord
from omwtools.records.dial import Dialogue, DialogueInfo
from omwtools.omwscripts.parser import parse_omwscripts, ScriptEntry

log = logging.getLogger(__name__)


class ModStore:
    """Loads ESM/ESP/omwgame/omwaddon files into a SQLite database."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._current_dial_topic: str = ""  # tracks last seen DIAL for INFO linking

    # ------------------------------------------------------------------
    # High-level file loading
    # ------------------------------------------------------------------

    def load_file(
        self,
        path: str | Path,
        encoding: str = "cp1252",
        lenient: bool = False,
    ) -> int:
        """Load a binary ESM-format file and return its mod_id."""
        path = Path(path)
        log.info("Loading %s", path)

        with ESMReader(path, encoding=encoding, lenient=lenient) as reader:
            raw_header = reader.read_header()
            header = TES3Header.from_raw(
                _adapt_raw(raw_header), reader.format_version
            )

            # Insert mod record
            cur = self.conn.execute(
                """INSERT INTO mods (filename, file_type, format_version,
                                     author, description, record_count)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(filename) DO UPDATE SET
                       format_version=excluded.format_version,
                       author=excluded.author,
                       description=excluded.description,
                       record_count=excluded.record_count
                """,
                (
                    path.name,
                    header.file_type,
                    header.format_version,
                    header.author,
                    header.description,
                    header.record_count,
                ),
            )
            mod_id = cur.lastrowid
            assert mod_id is not None

            # Insert master file references
            for sort_i, mf in enumerate(header.masters):
                self.conn.execute(
                    "INSERT INTO master_files (mod_id, master_name, master_size, sort_order)"
                    " VALUES (?, ?, ?, ?)",
                    (mod_id, mf.filename, mf.file_size, sort_i),
                )

            # Load all records
            sort_order = 0
            for raw in reader.iter_records():
                adapted = _adapt_raw(raw)
                record = parse_record(adapted, reader.format_version)
                self._insert_record(mod_id, record, sort_order)
                sort_order += 1

        self.conn.commit()
        log.info("Loaded %s as mod_id=%d (%d records)", path.name, mod_id, sort_order)
        return mod_id

    def load_omwscripts_file(self, path: str | Path) -> int:
        """Load a .omwscripts text file and return its file_id."""
        path = Path(path)
        log.info("Loading omwscripts: %s", path)

        text = path.read_text(encoding="utf-8")
        entries = parse_omwscripts(text)

        cur = self.conn.execute(
            "INSERT INTO omwscripts_files (filename) VALUES (?)"
            " ON CONFLICT(filename) DO UPDATE SET loaded_at=datetime('now')",
            (path.name,),
        )
        file_id = cur.lastrowid
        assert file_id is not None

        self.conn.execute(
            "DELETE FROM omwscripts_entries WHERE file_id=?", (file_id,)
        )

        for sort_i, entry in enumerate(entries):
            self.conn.execute(
                "INSERT INTO omwscripts_entries (file_id, script_path, flags, types_json, sort_order)"
                " VALUES (?, ?, ?, ?, ?)",
                (file_id, entry.script_path, entry.flags,
                 json.dumps(entry.types), sort_i),
            )

        self.conn.commit()
        log.info("Loaded %d script entries from %s", len(entries), path.name)
        return file_id

    # ------------------------------------------------------------------
    # Record insertion dispatch
    # ------------------------------------------------------------------

    def _insert_record(
        self, mod_id: int, record: BaseRecord, sort_order: int
    ) -> None:
        """Insert a parsed record into the appropriate tables."""
        if isinstance(record, UnknownRecord):
            self._insert_unknown(mod_id, record, sort_order)
        elif isinstance(record, NPC):
            self._insert_npc(mod_id, record, sort_order)
        elif isinstance(record, Cell):
            self._insert_cell(mod_id, record, sort_order)
        elif isinstance(record, Script):
            self._insert_script(mod_id, record, sort_order)
        elif isinstance(record, LUALRecord):
            self._insert_lual(mod_id, record, sort_order)
        elif isinstance(record, Dialogue):
            self._insert_dialogue(mod_id, record, sort_order)
        elif isinstance(record, DialogueInfo):
            self._insert_info(mod_id, record, sort_order)
        else:
            self._insert_typed(mod_id, record, sort_order)

    def _upsert_record(
        self,
        mod_id: int,
        rec_type: str,
        record_id_text: str,
        flags: int,
        is_deleted: int,
        sort_order: int,
        raw_blob: Optional[bytes] = None,
    ) -> int:
        """Insert or update the universal records table row.  Returns record id."""
        cur = self.conn.execute(
            """INSERT INTO records
               (mod_id, rec_type, record_id_text, flags, is_deleted, sort_order, raw_blob)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(mod_id, rec_type, record_id_text) DO UPDATE SET
                   flags=excluded.flags,
                   is_deleted=excluded.is_deleted,
                   sort_order=excluded.sort_order,
                   raw_blob=excluded.raw_blob
            """,
            (mod_id, rec_type, record_id_text, flags, is_deleted, sort_order, raw_blob),
        )
        row_id = cur.lastrowid
        # Fetch the real id (might differ if updated)
        row = self.conn.execute(
            "SELECT id FROM records WHERE mod_id=? AND rec_type=? AND record_id_text=?",
            (mod_id, rec_type, record_id_text),
        ).fetchone()
        return row[0] if row else (row_id or 0)

    def _insert_unknown(
        self, mod_id: int, record: UnknownRecord, sort_order: int
    ) -> None:
        rt = record.actual_rec_type.decode("ascii", errors="replace")
        self._upsert_record(
            mod_id, rt, f"__unknown_{sort_order}__",
            record.flags, int(record.is_deleted), sort_order,
            raw_blob=record.encode_subrecords(0),
        )

    def _insert_npc(self, mod_id: int, record: NPC, sort_order: int) -> None:
        rid_text = refid_to_db_text(record.record_id)
        rec_id = self._upsert_record(
            mod_id, "NPC_", rid_text, record.flags,
            int(record.is_deleted), sort_order,
        )

        full = record.npdt_full
        ac   = record.npdt_autocalc

        level       = (full.level if full else (ac.level if ac else 0))
        health      = full.health      if full else 0
        mana        = full.mana        if full else 0
        fatigue     = full.fatigue     if full else 0
        disposition = full.disposition if full else (ac.disposition if ac else 50)
        reputation  = full.reputation  if full else (ac.reputation if ac else 0)
        rank        = full.rank        if full else (ac.rank if ac else 0)
        gold        = full.gold        if full else (ac.gold if ac else 0)
        is_autocalc = 1 if ac else 0
        attrs_json  = json.dumps(full.attributes if full else [])
        skills_json = json.dumps(full.skills     if full else [])

        ai = record.ai_data
        self.conn.execute(
            """INSERT INTO npcs
               (record_id, mesh, name, race, class_id, faction, head, hair, script,
                npc_flags, level, health, mana, fatigue, disposition, reputation, rank, gold,
                is_autocalc, attributes_json, skills_json,
                ai_hello, ai_fight, ai_flee, ai_alarm, ai_services)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(record_id) DO UPDATE SET
                   mesh=excluded.mesh, name=excluded.name,
                   race=excluded.race, class_id=excluded.class_id,
                   faction=excluded.faction, npc_flags=excluded.npc_flags,
                   level=excluded.level, health=excluded.health,
                   gold=excluded.gold, is_autocalc=excluded.is_autocalc
            """,
            (
                rec_id,
                record.mesh, record.name,
                refid_to_db_text(record.race),
                refid_to_db_text(record.class_id),
                refid_to_db_text(record.faction),
                refid_to_db_text(record.head),
                refid_to_db_text(record.hair),
                refid_to_db_text(record.script),
                record.npc_flags,
                level, health, mana, fatigue,
                disposition, reputation, rank, gold,
                is_autocalc, attrs_json, skills_json,
                ai.hello if ai else 0,
                ai.fight if ai else 0,
                ai.flee  if ai else 0,
                ai.alarm if ai else 0,
                ai.services if ai else 0,
            ),
        )

        # Clear and reinsert child rows
        self.conn.execute("DELETE FROM npc_inventory WHERE npc_id=?", (rec_id,))
        for i, item in enumerate(record.inventory):
            self.conn.execute(
                "INSERT INTO npc_inventory (npc_id, item_id, count, sort_order)"
                " VALUES (?, ?, ?, ?)",
                (rec_id, refid_to_db_text(item.item_id), item.count, i),
            )

        self.conn.execute("DELETE FROM npc_spells WHERE npc_id=?", (rec_id,))
        for i, spell in enumerate(record.spells):
            self.conn.execute(
                "INSERT INTO npc_spells (npc_id, spell_id, sort_order) VALUES (?, ?, ?)",
                (rec_id, refid_to_db_text(spell), i),
            )

        self.conn.execute("DELETE FROM npc_ai_packages WHERE npc_id=?", (rec_id,))
        for i, pkg in enumerate(record.ai_packages):
            self.conn.execute(
                "INSERT INTO npc_ai_packages (npc_id, package_type, raw_hex, sort_order)"
                " VALUES (?, ?, ?, ?)",
                (rec_id,
                 pkg.package_type.decode("ascii", errors="replace"),
                 pkg.raw_data.hex(),
                 i),
            )

        self.conn.execute("DELETE FROM npc_transport WHERE npc_id=?", (rec_id,))
        for i, dest in enumerate(record.transport):
            self.conn.execute(
                "INSERT INTO npc_transport"
                " (npc_id, pos_x, pos_y, pos_z, rot_x, rot_y, rot_z, cell_name, sort_order)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rec_id,
                 dest.pos_x, dest.pos_y, dest.pos_z,
                 dest.rot_x, dest.rot_y, dest.rot_z,
                 dest.cell_name, i),
            )

    def _insert_cell(self, mod_id: int, record: Cell, sort_order: int) -> None:
        from omwtools.io.refid import refid_to_db_text
        rid_text = f"cell:{record.cell_name}:{record.grid_x}:{record.grid_y}"
        rec_id = self._upsert_record(
            mod_id, "CELL", rid_text, record.flags,
            int(record.is_deleted), sort_order,
        )

        amb = record.ambient
        self.conn.execute(
            """INSERT INTO cells
               (record_id, cell_name, cell_flags, grid_x, grid_y, region,
                ref_num_counter, water_height,
                ambient, sunlight, fog, fog_density, map_color)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(record_id) DO UPDATE SET
                   cell_flags=excluded.cell_flags, region=excluded.region,
                   ref_num_counter=excluded.ref_num_counter,
                   water_height=excluded.water_height,
                   ambient=excluded.ambient, sunlight=excluded.sunlight,
                   fog=excluded.fog, fog_density=excluded.fog_density,
                   map_color=excluded.map_color
            """,
            (
                rec_id, record.cell_name, record.cell_flags,
                record.grid_x, record.grid_y,
                refid_to_db_text(record.region),
                record.ref_num_counter, record.water_height,
                amb.ambient if amb else None,
                amb.sunlight if amb else None,
                amb.fog if amb else None,
                amb.fog_density if amb else None,
                record.map_color,
            ),
        )

        self.conn.execute("DELETE FROM cell_refs WHERE cell_id=?", (rec_id,))
        for i, ref in enumerate(record.refs):
            dp = ref.dest_pos
            dr = ref.dest_rot
            self.conn.execute(
                """INSERT INTO cell_refs
                   (cell_id, ref_num, object_id, scale,
                    pos_x, pos_y, pos_z, rot_x, rot_y, rot_z,
                    owner, owner_rank, owner_global, soul,
                    key_id, trap_id, enchant_charge, charge_int, lock_level,
                    dest_pos_x, dest_pos_y, dest_pos_z,
                    dest_rot_x, dest_rot_y, dest_rot_z,
                    dest_cell, is_blocked, is_deleted, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec_id, ref.ref_num,
                    refid_to_db_text(ref.object_id),
                    ref.scale,
                    ref.pos_x, ref.pos_y, ref.pos_z,
                    ref.rot_x, ref.rot_y, ref.rot_z,
                    refid_to_db_text(ref.owner),
                    ref.owner_rank,
                    refid_to_db_text(ref.owner_global),
                    refid_to_db_text(ref.soul),
                    refid_to_db_text(ref.key_id),
                    refid_to_db_text(ref.trap_id),
                    ref.enchant_charge,
                    ref.charge_int,
                    ref.lock_level,
                    dp[0] if dp else None, dp[1] if dp else None, dp[2] if dp else None,
                    dr[0] if dr else None, dr[1] if dr else None, dr[2] if dr else None,
                    ref.dest_cell,
                    int(ref.is_blocked),
                    int(ref.is_deleted), i,
                ),
            )

    def _insert_script(self, mod_id: int, record: Script, sort_order: int) -> None:
        rid_text = record.script_name.lower()
        rec_id = self._upsert_record(
            mod_id, "SCPT", rid_text, record.flags,
            int(record.is_deleted), sort_order,
        )
        self.conn.execute(
            """INSERT INTO scripts
               (record_id, script_name, num_shorts, num_longs, num_floats,
                local_vars_json, bytecode_hex, source_text, has_scdt)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(record_id) DO UPDATE SET
                   source_text=excluded.source_text,
                   bytecode_hex=excluded.bytecode_hex,
                   has_scdt=excluded.has_scdt
            """,
            (
                rec_id,
                record.script_name,
                record.num_shorts, record.num_longs, record.num_floats,
                json.dumps(record.local_vars),
                record.bytecode.hex(),
                record.source_text,
                int(record.has_scdt),
            ),
        )

    def _insert_lual(self, mod_id: int, record: LUALRecord, sort_order: int) -> None:
        rid_text = f"lual_{sort_order}"
        rec_id = self._upsert_record(
            mod_id, "LUAL", rid_text, record.flags,
            int(record.is_deleted), sort_order,
        )
        self.conn.execute(
            "INSERT INTO lua_script_cfgs (record_id) VALUES (?)"
            " ON CONFLICT(record_id) DO NOTHING",
            (rec_id,),
        )
        self.conn.execute(
            "DELETE FROM lua_script_entries WHERE lual_id=?", (rec_id,)
        )
        for i, entry in enumerate(record.scripts):
            self.conn.execute(
                """INSERT INTO lua_script_entries
                   (lual_id, script_path, lua_flags, types_json, init_data_hex, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rec_id,
                    entry.script_path,
                    entry.flags,
                    json.dumps(entry.types),
                    entry.init_data.hex(),
                    i,
                ),
            )

    def _insert_typed(self, mod_id: int, record: BaseRecord, sort_order: int) -> None:
        """Insert a Phase 2 typed record into typed_records using to_dict()."""
        d = record.to_dict()
        rid_text = d.get("record_id", "") or d.get("script_name", "") or f"__idx_{sort_order}__"
        rec_type = record.REC_TYPE.decode("ascii", errors="replace")

        rec_id = self._upsert_record(
            mod_id, rec_type, rid_text,
            record.flags, int(record.is_deleted), sort_order,
        )
        self.conn.execute(
            """INSERT INTO typed_records (record_id, name, script, data_json)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(record_id) DO UPDATE SET
                   name=excluded.name, script=excluded.script,
                   data_json=excluded.data_json
            """,
            (
                rec_id,
                d.get("name", ""),
                d.get("script", ""),
                json.dumps(d),
            ),
        )

    def _insert_dialogue(self, mod_id: int, record: Dialogue, sort_order: int) -> None:
        """Insert a DIAL record and update the current topic tracker."""
        self._current_dial_topic = record.topic
        rec_id = self._upsert_record(
            mod_id, "DIAL", record.topic,
            record.flags, int(record.is_deleted), sort_order,
        )
        self.conn.execute(
            """INSERT INTO typed_records (record_id, name, script, data_json)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(record_id) DO UPDATE SET
                   name=excluded.name, data_json=excluded.data_json
            """,
            (rec_id, record.topic, "", json.dumps(record.to_dict())),
        )

    def _insert_info(self, mod_id: int, record: DialogueInfo, sort_order: int) -> None:
        """Insert an INFO record linked to its parent DIAL topic."""
        rid_text = record.record_id or f"__info_{sort_order}__"
        rec_id = self._upsert_record(
            mod_id, "INFO", rid_text,
            record.flags, int(record.is_deleted), sort_order,
        )
        self.conn.execute(
            """INSERT INTO dialogue_infos
               (record_id, dial_topic, prev_id, next_id, data_json)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(record_id) DO UPDATE SET
                   dial_topic=excluded.dial_topic,
                   prev_id=excluded.prev_id,
                   next_id=excluded.next_id,
                   data_json=excluded.data_json
            """,
            (
                rec_id,
                self._current_dial_topic,
                record.prev_id,
                record.next_id,
                json.dumps(record.to_dict()),
            ),
        )

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_mods(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM mods ORDER BY id").fetchall()

    def get_mod(self, mod_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM mods WHERE id=?", (mod_id,)
        ).fetchone()

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def iter_records_ordered(self, mod_id: int) -> Iterator[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM records WHERE mod_id=? ORDER BY sort_order",
            (mod_id,),
        )

    def get_omwscripts_entries(
        self, file_id: Optional[int] = None
    ) -> list[sqlite3.Row]:
        if file_id is not None:
            return self.conn.execute(
                "SELECT * FROM omwscripts_entries WHERE file_id=? ORDER BY sort_order",
                (file_id,),
            ).fetchall()
        return self.conn.execute(
            "SELECT e.*, f.filename FROM omwscripts_entries e"
            " JOIN omwscripts_files f ON e.file_id=f.id ORDER BY e.id"
        ).fetchall()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _adapt_raw(raw: object) -> RawRecord:
    """Convert the lightweight _RawRecord from reader to the full RawRecord dataclass."""
    from omwtools.records.base import RawSubrecord
    from omwtools.io.reader import _RawRecord as _R, _RawSubrecord as _S

    if isinstance(raw, RawRecord):
        return raw

    # It's the internal _RawRecord from reader
    subs = [
        RawSubrecord(sub_type=s.sub_type, data=s.data)
        for s in raw.subrecords
    ]
    return RawRecord(
        rec_type=raw.rec_type,
        flags=raw.flags,
        unknown=raw.unknown,
        raw_data=raw.raw_data,
        subrecords=subs,
    )


def _make_raw_for(record: BaseRecord) -> RawRecord:
    """Build a minimal RawRecord for an already-parsed typed record."""
    from omwtools.records.base import RawSubrecord
    raw_data = record.encode_subrecords(0)
    return RawRecord(
        rec_type=record.REC_TYPE,
        flags=record.flags,
        unknown=record.unknown,
        raw_data=raw_data,
        subrecords=[],
    )
