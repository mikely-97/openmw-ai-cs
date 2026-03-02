"""INGR — Ingredient record.

Subrecords:
  NAME  → record_id (RefId)
  MODL  → mesh path
  FNAM  → display name
  IRDT  → ingredient data (56 bytes):
            float weight + int32 value +
            int32[4] effect_ids + int32[4] skill_ids + int32[4] attribute_ids
  SCRI  → script RefId
  ITEX  → icon path
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

IRDT_FMT = "<fi" + "i" * 12
IRDT_SIZE = struct.calcsize(IRDT_FMT)  # 56


@dataclass
class Ingredient(BaseRecord):
    """INGR record — ingredient."""

    REC_TYPE = b"INGR"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    weight: float = 0.0
    value: int = 0
    effect_ids: list[int] = field(default_factory=lambda: [-1, -1, -1, -1])
    skill_ids: list[int] = field(default_factory=lambda: [-1, -1, -1, -1])
    attribute_ids: list[int] = field(default_factory=lambda: [-1, -1, -1, -1])
    script: RefId = field(default_factory=EmptyRefId)
    icon: str = ""

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Ingredient":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        def get_refid(tag: bytes) -> RefId:
            sub = raw.get_subrecord(tag)
            return decode_refid_from_subrecord(sub.data, format_version) if sub else EmptyRefId()

        obj.record_id = get_refid(b"NAME")

        modl = raw.get_subrecord(b"MODL")
        if modl:
            obj.mesh = decode_cstring(modl.data)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        irdt = raw.get_subrecord(b"IRDT")
        if irdt and len(irdt.data) >= IRDT_SIZE:
            vals = struct.unpack_from(IRDT_FMT, irdt.data)
            obj.weight = vals[0]
            obj.value  = vals[1]
            obj.effect_ids    = list(vals[2:6])
            obj.skill_ids     = list(vals[6:10])
            obj.attribute_ids = list(vals[10:14])

        obj.script = get_refid(b"SCRI")

        itex = raw.get_subrecord(b"ITEX")
        if itex:
            obj.icon = decode_cstring(itex.data)

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
        if self.name:
            add_cstr(b"FNAM", self.name)

        effs = (list(self.effect_ids) + [-1] * 4)[:4]
        skls = (list(self.skill_ids) + [-1] * 4)[:4]
        attrs = (list(self.attribute_ids) + [-1] * 4)[:4]
        out += pack_subrec_header(b"IRDT", IRDT_SIZE)
        out += struct.pack(IRDT_FMT, self.weight, self.value, *effs, *skls, *attrs)

        add_refid(b"SCRI", self.script)
        if self.icon:
            add_cstr(b"ITEX", self.icon)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "INGR",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "name": self.name,
            "weight": self.weight,
            "value": self.value,
            "effect_ids": self.effect_ids,
            "skill_ids": self.skill_ids,
            "attribute_ids": self.attribute_ids,
            "script": refid_to_db_text(self.script),
            "icon": self.icon,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Ingredient":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id     = refid_from_db_text(d.get("record_id", ""))
        obj.mesh          = d.get("mesh", "")
        obj.name          = d.get("name", "")
        obj.weight        = d.get("weight", 0.0)
        obj.value         = d.get("value", 0)
        obj.effect_ids    = d.get("effect_ids", [-1, -1, -1, -1])
        obj.skill_ids     = d.get("skill_ids", [-1, -1, -1, -1])
        obj.attribute_ids = d.get("attribute_ids", [-1, -1, -1, -1])
        obj.script        = refid_from_db_text(d.get("script", ""))
        obj.icon          = d.get("icon", "")
        obj.flags         = d.get("flags", 0)
        return obj
