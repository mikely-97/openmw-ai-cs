"""ENCH — Enchantment record.

Subrecords:
  NAME  → record_id (RefId)
  ENDT  → enchantment data (16 bytes: int32 type + int32 cost + int32 charge + int32 flags)
  ENAM  → effect entries (24 bytes each, repeating)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import pack_subrec_header
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord
from omwtools.records._effects import EffectEntry, decode_effects, encode_effects, effects_to_dicts, effects_from_dicts

ENDT_FMT = "<iiii"
ENDT_SIZE = struct.calcsize(ENDT_FMT)  # 16


@dataclass
class Enchantment(BaseRecord):
    """ENCH record — item enchantment definition."""

    REC_TYPE = b"ENCH"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    ench_type: int = 0    # 0=cast-once, 1=on-strike, 2=on-equip, 3=constant-effect
    cost: int = 0
    charge: int = 0
    ench_flags: int = 0   # 0x1 = auto-calc
    effects: list[EffectEntry] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Enchantment":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        endt = raw.get_subrecord(b"ENDT")
        if endt and len(endt.data) >= ENDT_SIZE:
            obj.ench_type, obj.cost, obj.charge, obj.ench_flags = struct.unpack_from(ENDT_FMT, endt.data)

        obj.effects = decode_effects(raw.subrecords)
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out += pack_subrec_header(b"NAME", len(id_data)) + id_data

        out += pack_subrec_header(b"ENDT", ENDT_SIZE)
        out += struct.pack(ENDT_FMT, self.ench_type, self.cost, self.charge, self.ench_flags)

        eff_bytes = encode_effects(self.effects)
        for i in range(0, len(eff_bytes), 24):
            chunk = eff_bytes[i:i + 24]
            out += pack_subrec_header(b"ENAM", len(chunk)) + chunk

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "ENCH",
            "record_id": refid_to_db_text(self.record_id),
            "ench_type": self.ench_type,
            "cost": self.cost,
            "charge": self.charge,
            "ench_flags": self.ench_flags,
            "effects": effects_to_dicts(self.effects),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Enchantment":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.ench_type   = d.get("ench_type", 0)
        obj.cost        = d.get("cost", 0)
        obj.charge      = d.get("charge", 0)
        obj.ench_flags  = d.get("ench_flags", 0)
        obj.effects     = effects_from_dicts(d.get("effects", []))
        obj.flags       = d.get("flags", 0)
        return obj
