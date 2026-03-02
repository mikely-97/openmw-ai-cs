"""SPEL — Spell record.

Subrecords:
  NAME  → record_id (RefId)
  FNAM  → display name (C-string)
  SPDT  → spell data (12 bytes: int32 type + int32 cost + int32 flags)
  ENAM  → effect entries (24 bytes each, repeating)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, pack_subrec_header
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord
from omwtools.records._effects import EffectEntry, decode_effects, encode_effects, effects_to_dicts, effects_from_dicts

SPDT_FMT = "<iii"
SPDT_SIZE = struct.calcsize(SPDT_FMT)  # 12


@dataclass
class Spell(BaseRecord):
    """SPEL record — spell or ability."""

    REC_TYPE = b"SPEL"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    name: str = ""
    spell_type: int = 0   # 0=Spell, 1=Ability, 2=Blight, 3=Disease, 4=Curse, 5=Power
    cost: int = 0
    spell_flags: int = 0  # 0x1=auto-calc, 0x2=player start, 0x4=always succeeds
    effects: list[EffectEntry] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Spell":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        spdt = raw.get_subrecord(b"SPDT")
        if spdt and len(spdt.data) >= SPDT_SIZE:
            obj.spell_type, obj.cost, obj.spell_flags = struct.unpack_from(SPDT_FMT, spdt.data)

        obj.effects = decode_effects(raw.subrecords)
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out += pack_subrec_header(b"NAME", len(id_data)) + id_data

        if self.name:
            n = encode_cstring(self.name)
            out += pack_subrec_header(b"FNAM", len(n)) + n

        out += pack_subrec_header(b"SPDT", SPDT_SIZE)
        out += struct.pack(SPDT_FMT, self.spell_type, self.cost, self.spell_flags)

        eff_bytes = encode_effects(self.effects)
        for i in range(0, len(eff_bytes), 24):
            chunk = eff_bytes[i:i + 24]
            out += pack_subrec_header(b"ENAM", len(chunk)) + chunk

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "SPEL",
            "record_id": refid_to_db_text(self.record_id),
            "name": self.name,
            "spell_type": self.spell_type,
            "cost": self.cost,
            "spell_flags": self.spell_flags,
            "effects": effects_to_dicts(self.effects),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Spell":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id  = refid_from_db_text(d.get("record_id", ""))
        obj.name       = d.get("name", "")
        obj.spell_type = d.get("spell_type", 0)
        obj.cost       = d.get("cost", 0)
        obj.spell_flags = d.get("spell_flags", 0)
        obj.effects    = effects_from_dicts(d.get("effects", []))
        obj.flags      = d.get("flags", 0)
        return obj
