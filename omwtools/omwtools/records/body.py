"""BODY — Body part record.

Subrecords:
  NAME  record_id
  MODL  mesh path
  FNAM  name (display)
  BYDT  4 bytes: part_index (u8), vampire (u8), flags (u8), part_type (u8)

part_index values:
  0=head  1=hair  2=neck  3=chest  4=groin  5=skirt
  6=right_hand  7=left_hand  8=right_wrist  9=left_wrist  10=shield
  11=right_forearm  12=left_forearm  13=right_upper_arm  14=left_upper_arm
  15=right_foot  16=left_foot  17=right_ankle  18=left_ankle
  19=right_knee  20=left_knee  21=right_upper_leg  22=left_upper_leg
  23=right_pauldron  24=left_pauldron  25=weapon  26=tail

flags: bit 0 = female, bit 1 = not_playable
part_type: 0=skin  1=clothing  2=armor
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

_BYDT_FMT = "<BBBB"   # part, vampire, flags, part_type
_BYDT_SIZE = struct.calcsize(_BYDT_FMT)  # 4


@dataclass
class BodyPart(BaseRecord):
    """BODY record — body part (used for NPC appearance)."""

    REC_TYPE = b"BODY"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    part_index: int = 0    # which body slot
    vampire: int = 0
    part_flags: int = 0    # bit0=female, bit1=not_playable
    part_type: int = 0     # 0=skin, 1=clothing, 2=armor

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "BodyPart":
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
        bydt = raw.get_subrecord(b"BYDT")
        if bydt and len(bydt.data) >= _BYDT_SIZE:
            obj.part_index, obj.vampire, obj.part_flags, obj.part_type = \
                struct.unpack_from(_BYDT_FMT, bydt.data)
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_cstr(tag: bytes, s: str) -> None:
            d = encode_cstring(s)
            out.extend(pack_subrec_header(tag, len(d)) + d)

        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out.extend(pack_subrec_header(b"NAME", len(id_data)) + id_data)
        if self.mesh:
            add_cstr(b"MODL", self.mesh)
        if self.name:
            add_cstr(b"FNAM", self.name)
        bydt = struct.pack(_BYDT_FMT,
                           self.part_index, self.vampire,
                           self.part_flags, self.part_type)
        out.extend(pack_subrec_header(b"BYDT", len(bydt)) + bydt)
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type":   "BODY",
            "record_id":  refid_to_db_text(self.record_id),
            "mesh":       self.mesh,
            "name":       self.name,
            "part_index": self.part_index,
            "vampire":    self.vampire,
            "part_flags": self.part_flags,
            "part_type":  self.part_type,
            "flags":      self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BodyPart":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id  = refid_from_db_text(d.get("record_id", ""))
        obj.mesh       = d.get("mesh", "")
        obj.name       = d.get("name", "")
        obj.part_index = d.get("part_index", 0)
        obj.vampire    = d.get("vampire", 0)
        obj.part_flags = d.get("part_flags", 0)
        obj.part_type  = d.get("part_type", 0)
        obj.flags      = d.get("flags", 0)
        return obj
