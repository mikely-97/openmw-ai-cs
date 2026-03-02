"""ALCH — Potion/Alchemy item record.

Subrecords:
  NAME  → record_id (RefId)
  MODL  → mesh path
  TEXT  → icon path (note: TEXT not ITEX for potions)
  SCRI  → script RefId
  FNAM  → display name
  ALDT  → alchemy data (12 bytes: float weight + int32 value + int32 auto_calc)
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

ALDT_FMT = "<fii"
ALDT_SIZE = struct.calcsize(ALDT_FMT)  # 12


@dataclass
class Potion(BaseRecord):
    """ALCH record — potion or alchemical concoction."""

    REC_TYPE = b"ALCH"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    icon: str = ""
    script: RefId = field(default_factory=EmptyRefId)
    name: str = ""
    weight: float = 0.0
    value: int = 0
    auto_calc: int = 0
    effects: list[EffectEntry] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Potion":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        def get_refid(tag: bytes) -> RefId:
            sub = raw.get_subrecord(tag)
            return decode_refid_from_subrecord(sub.data, format_version) if sub else EmptyRefId()

        obj.record_id = get_refid(b"NAME")

        modl = raw.get_subrecord(b"MODL")
        if modl:
            obj.mesh = decode_cstring(modl.data)

        text = raw.get_subrecord(b"TEXT")
        if text:
            obj.icon = decode_cstring(text.data)

        obj.script = get_refid(b"SCRI")

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        aldt = raw.get_subrecord(b"ALDT")
        if aldt and len(aldt.data) >= ALDT_SIZE:
            obj.weight, obj.value, obj.auto_calc = struct.unpack_from(ALDT_FMT, aldt.data)

        obj.effects = decode_effects(raw.subrecords)
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_refid(tag: bytes, ref: RefId) -> None:
            data = encode_refid_to_subrecord(ref, format_version)
            out.extend(pack_subrec_header(tag, len(data)) + data)

        def add_cstr(tag: bytes, s: str) -> None:
            d = encode_cstring(s)
            out.extend(pack_subrec_header(tag, len(d)) + d)

        add_refid(b"NAME", self.record_id)
        if self.mesh:
            add_cstr(b"MODL", self.mesh)
        if self.icon:
            add_cstr(b"TEXT", self.icon)
        add_refid(b"SCRI", self.script)
        if self.name:
            add_cstr(b"FNAM", self.name)

        out += pack_subrec_header(b"ALDT", ALDT_SIZE)
        out += struct.pack(ALDT_FMT, self.weight, self.value, self.auto_calc)

        eff_bytes = encode_effects(self.effects)
        for i in range(0, len(eff_bytes), 24):
            chunk = eff_bytes[i:i + 24]
            out += pack_subrec_header(b"ENAM", len(chunk)) + chunk

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "ALCH",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "icon": self.icon,
            "script": refid_to_db_text(self.script),
            "name": self.name,
            "weight": self.weight,
            "value": self.value,
            "auto_calc": self.auto_calc,
            "effects": effects_to_dicts(self.effects),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Potion":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id  = refid_from_db_text(d.get("record_id", ""))
        obj.mesh       = d.get("mesh", "")
        obj.icon       = d.get("icon", "")
        obj.script     = refid_from_db_text(d.get("script", ""))
        obj.name       = d.get("name", "")
        obj.weight     = d.get("weight", 0.0)
        obj.value      = d.get("value", 0)
        obj.auto_calc  = d.get("auto_calc", 0)
        obj.effects    = effects_from_dicts(d.get("effects", []))
        obj.flags      = d.get("flags", 0)
        return obj
