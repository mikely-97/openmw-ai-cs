"""LEVC and LEVI — Levelled Creature and Levelled Item lists.

LEVC (levelled creature list):
  NAME  → record_id (RefId)
  DATA  → flags (int32): 0x1=calc_from_all_levels, 0x2=each_item_chance
  NNAM  → chance_none (uint8)
  INDX  → entry count (int32)
  CNAM  → creature RefId (paired with INTV)
  INTV  → level for preceding CNAM (int16)

LEVI (levelled item list):
  Same but uses INAM instead of CNAM.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import pack_subrec_header, pack_i32, pack_u8, unpack_i32, unpack_u8
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord


@dataclass
class LevelledEntry:
    item: RefId = field(default_factory=EmptyRefId)
    level: int = 0


def _parse_levelled(raw: RawRecord, format_version: int, entry_tag: bytes) -> tuple:
    """Return (lev_flags, chance_none, entries)."""
    lev_flags = 0
    chance_none = 0
    entries: list[LevelledEntry] = []

    data_sub = raw.get_subrecord(b"DATA")
    if data_sub and len(data_sub.data) >= 4:
        lev_flags = unpack_i32(data_sub.data)

    nnam = raw.get_subrecord(b"NNAM")
    if nnam and nnam.data:
        chance_none = unpack_u8(nnam.data)

    subs = raw.subrecords
    i = 0
    while i < len(subs):
        if subs[i].sub_type == entry_tag:
            item = decode_refid_from_subrecord(subs[i].data, format_version)
            level = 0
            if i + 1 < len(subs) and subs[i + 1].sub_type == b"INTV":
                if len(subs[i + 1].data) >= 2:
                    level = struct.unpack_from("<h", subs[i + 1].data)[0]
                i += 1
            entries.append(LevelledEntry(item, level))
        i += 1

    return lev_flags, chance_none, entries


def _encode_levelled(record_id: RefId, lev_flags: int, chance_none: int,
                     entries: list[LevelledEntry], entry_tag: bytes,
                     format_version: int) -> bytes:
    out = bytearray()

    id_data = encode_refid_to_subrecord(record_id, format_version)
    out += pack_subrec_header(b"NAME", len(id_data)) + id_data
    out += pack_subrec_header(b"DATA", 4) + pack_i32(lev_flags)
    out += pack_subrec_header(b"NNAM", 1) + pack_u8(chance_none)
    out += pack_subrec_header(b"INDX", 4) + pack_i32(len(entries))

    for entry in entries:
        item_data = encode_refid_to_subrecord(entry.item, format_version)
        out += pack_subrec_header(entry_tag, len(item_data)) + item_data
        out += pack_subrec_header(b"INTV", 2) + struct.pack("<h", entry.level)

    return bytes(out)


@dataclass
class LevelledCreature(BaseRecord):
    """LEVC record — levelled creature list."""

    REC_TYPE = b"LEVC"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    lev_flags: int = 0
    chance_none: int = 0
    entries: list[LevelledEntry] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "LevelledCreature":
        obj = cls(flags=raw.flags, unknown=raw.unknown)
        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)
        obj.lev_flags, obj.chance_none, obj.entries = _parse_levelled(raw, format_version, b"CNAM")
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        return _encode_levelled(self.record_id, self.lev_flags, self.chance_none,
                                self.entries, b"CNAM", format_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "LEVC",
            "record_id": refid_to_db_text(self.record_id),
            "lev_flags": self.lev_flags,
            "chance_none": self.chance_none,
            "entries": [{"item": refid_to_db_text(e.item), "level": e.level}
                        for e in self.entries],
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LevelledCreature":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.lev_flags   = d.get("lev_flags", 0)
        obj.chance_none = d.get("chance_none", 0)
        obj.entries     = [LevelledEntry(refid_from_db_text(e["item"]), e["level"])
                           for e in d.get("entries", [])]
        obj.flags       = d.get("flags", 0)
        return obj


@dataclass
class LevelledItem(BaseRecord):
    """LEVI record — levelled item list."""

    REC_TYPE = b"LEVI"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    lev_flags: int = 0
    chance_none: int = 0
    entries: list[LevelledEntry] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "LevelledItem":
        obj = cls(flags=raw.flags, unknown=raw.unknown)
        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)
        obj.lev_flags, obj.chance_none, obj.entries = _parse_levelled(raw, format_version, b"INAM")
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        return _encode_levelled(self.record_id, self.lev_flags, self.chance_none,
                                self.entries, b"INAM", format_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "LEVI",
            "record_id": refid_to_db_text(self.record_id),
            "lev_flags": self.lev_flags,
            "chance_none": self.chance_none,
            "entries": [{"item": refid_to_db_text(e.item), "level": e.level}
                        for e in self.entries],
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LevelledItem":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.lev_flags   = d.get("lev_flags", 0)
        obj.chance_none = d.get("chance_none", 0)
        obj.entries     = [LevelledEntry(refid_from_db_text(e["item"]), e["level"])
                           for e in d.get("entries", [])]
        obj.flags       = d.get("flags", 0)
        return obj
