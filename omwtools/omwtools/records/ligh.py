"""LIGH — Light source record.

Subrecords:
  NAME  → record_id (RefId)
  MODL  → mesh path (optional for carried lights)
  FNAM  → display name (optional)
  ITEX  → icon path (optional)
  LHDT  → light data (24 bytes: float weight + int32 value + int32 time +
                        int32 radius + uint32 color (ABGR) + int32 flags)
  SCRI  → script RefId
  SNAM  → sound RefId
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

LHDT_FMT = "<fiiiIi"
LHDT_SIZE = struct.calcsize(LHDT_FMT)  # 24


@dataclass
class Light(BaseRecord):
    """LIGH record — light source."""

    REC_TYPE = b"LIGH"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    icon: str = ""
    weight: float = 0.0
    value: int = 0
    time: int = 0       # duration in seconds (-1 = infinite)
    radius: int = 0
    color: int = 0      # ABGR uint32
    light_flags: int = 0
    script: RefId = field(default_factory=EmptyRefId)
    sound: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Light":
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

        itex = raw.get_subrecord(b"ITEX")
        if itex:
            obj.icon = decode_cstring(itex.data)

        lhdt = raw.get_subrecord(b"LHDT")
        if lhdt and len(lhdt.data) >= LHDT_SIZE:
            (obj.weight, obj.value, obj.time,
             obj.radius, obj.color, obj.light_flags) = struct.unpack_from(LHDT_FMT, lhdt.data)

        obj.script = get_refid(b"SCRI")
        obj.sound  = get_refid(b"SNAM")
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
        if self.icon:
            add_cstr(b"ITEX", self.icon)

        out += pack_subrec_header(b"LHDT", LHDT_SIZE)
        out += struct.pack(LHDT_FMT, self.weight, self.value, self.time,
                           self.radius, self.color, self.light_flags)

        if not isinstance(self.script, EmptyRefId):
            add_refid(b"SCRI", self.script)
        if not isinstance(self.sound, EmptyRefId):
            add_refid(b"SNAM", self.sound)
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "LIGH",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "name": self.name,
            "icon": self.icon,
            "weight": self.weight,
            "value": self.value,
            "time": self.time,
            "radius": self.radius,
            "color": self.color,
            "light_flags": self.light_flags,
            "script": refid_to_db_text(self.script),
            "sound": refid_to_db_text(self.sound),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Light":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.mesh        = d.get("mesh", "")
        obj.name        = d.get("name", "")
        obj.icon        = d.get("icon", "")
        obj.weight      = d.get("weight", 0.0)
        obj.value       = d.get("value", 0)
        obj.time        = d.get("time", 0)
        obj.radius      = d.get("radius", 0)
        obj.color       = d.get("color", 0)
        obj.light_flags = d.get("light_flags", 0)
        obj.script      = refid_from_db_text(d.get("script", ""))
        obj.sound       = refid_from_db_text(d.get("sound", ""))
        obj.flags       = d.get("flags", 0)
        return obj
