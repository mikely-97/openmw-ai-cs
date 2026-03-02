"""WEAP — Weapon record.

Subrecords:
  NAME  → record_id (RefId)
  MODL  → mesh path
  FNAM  → display name
  WPDT  → weapon data (32 bytes):
            float weight + int32 value + int16 weap_type + uint16 health +
            float speed + float reach + uint16 enchant_pts +
            uint8×2 chop + uint8×2 slash + uint8×2 thrust + int32 flags
  SCRI  → script RefId
  ITEX  → icon path
  ENAM  → enchantment RefId (NOT an effect entry — string RefId)
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

# WPDT actual layout from WPDTstruct in loadweap.hpp:
#   float mWeight + int32 mValue + int16 mType + uint16 mHealth +
#   float mSpeed + float mReach + uint16 mEnchant +
#   uint8[2] mChop + uint8[2] mSlash + uint8[2] mThrust + int32 mFlags
WPDT_FMT = "<fihHffHBBBBBBi"
WPDT_SIZE = struct.calcsize(WPDT_FMT)  # 32


@dataclass
class Weapon(BaseRecord):
    """WEAP record — weapon."""

    REC_TYPE = b"WEAP"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    weight: float = 0.0
    value: int = 0
    weap_type: int = 0   # weapon type enum
    health: int = 0
    speed: float = 0.0
    reach: float = 0.0
    enchant_pts: int = 0
    chop_min: int = 0
    chop_max: int = 0
    slash_min: int = 0
    slash_max: int = 0
    thrust_min: int = 0
    thrust_max: int = 0
    weap_flags: int = 0
    script: RefId = field(default_factory=EmptyRefId)
    icon: str = ""
    enchantment: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Weapon":
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

        wpdt = raw.get_subrecord(b"WPDT")
        if wpdt and len(wpdt.data) >= WPDT_SIZE:
            v = struct.unpack_from(WPDT_FMT, wpdt.data)
            (obj.weight, obj.value, obj.weap_type, obj.health,
             obj.speed, obj.reach, obj.enchant_pts,
             obj.chop_min, obj.chop_max,
             obj.slash_min, obj.slash_max,
             obj.thrust_min, obj.thrust_max,
             obj.weap_flags) = v

        obj.script = get_refid(b"SCRI")

        itex = raw.get_subrecord(b"ITEX")
        if itex:
            obj.icon = decode_cstring(itex.data)

        obj.enchantment = get_refid(b"ENAM")
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

        out += pack_subrec_header(b"WPDT", WPDT_SIZE)
        out += struct.pack(WPDT_FMT,
                           self.weight, self.value, self.weap_type, self.health,
                           self.speed, self.reach, self.enchant_pts,
                           self.chop_min, self.chop_max,
                           self.slash_min, self.slash_max,
                           self.thrust_min, self.thrust_max,
                           self.weap_flags)

        if not isinstance(self.script, EmptyRefId):
            add_refid(b"SCRI", self.script)
        if self.icon:
            add_cstr(b"ITEX", self.icon)
        if not isinstance(self.enchantment, EmptyRefId):
            add_refid(b"ENAM", self.enchantment)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "WEAP",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "name": self.name,
            "weight": self.weight,
            "value": self.value,
            "weap_type": self.weap_type,
            "health": self.health,
            "speed": self.speed,
            "reach": self.reach,
            "enchant_pts": self.enchant_pts,
            "chop_min": self.chop_min,
            "chop_max": self.chop_max,
            "slash_min": self.slash_min,
            "slash_max": self.slash_max,
            "thrust_min": self.thrust_min,
            "thrust_max": self.thrust_max,
            "weap_flags": self.weap_flags,
            "script": refid_to_db_text(self.script),
            "icon": self.icon,
            "enchantment": refid_to_db_text(self.enchantment),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Weapon":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.mesh        = d.get("mesh", "")
        obj.name        = d.get("name", "")
        obj.weight      = d.get("weight", 0.0)
        obj.value       = d.get("value", 0)
        obj.weap_type   = d.get("weap_type", 0)
        obj.health      = d.get("health", 0)
        obj.speed       = d.get("speed", 0.0)
        obj.reach       = d.get("reach", 0.0)
        obj.enchant_pts = d.get("enchant_pts", 0)
        obj.chop_min    = d.get("chop_min", 0)
        obj.chop_max    = d.get("chop_max", 0)
        obj.slash_min   = d.get("slash_min", 0)
        obj.slash_max   = d.get("slash_max", 0)
        obj.thrust_min  = d.get("thrust_min", 0)
        obj.thrust_max  = d.get("thrust_max", 0)
        obj.weap_flags  = d.get("weap_flags", 0)
        obj.script      = refid_from_db_text(d.get("script", ""))
        obj.icon        = d.get("icon", "")
        obj.enchantment = refid_from_db_text(d.get("enchantment", ""))
        obj.flags       = d.get("flags", 0)
        return obj
