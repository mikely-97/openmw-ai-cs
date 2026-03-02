"""SKIL and MGEF records — Skill and Magic Effect definitions.

SKIL:
  INDX  → skill index (int32, 0-26)
  SKDT  → skill data (24 bytes: int32 attr + int32 specialization + float[4] use_values)
  DESC  → description text

MGEF:
  INDX  → effect index (int32, 0-142)
  MEDT  → magic effect data (36 bytes):
            int32 school + float base_cost + int32 flags +
            int32 color (RGB) + float speed + float size + float size_cap + float wind_speed
  ITEX  → icon path
  PTEX  → particle texture path
  BSND  → bolt sound RefId
  CSND  → cast sound RefId
  HSND  → hit sound RefId
  ASND  → area sound RefId
  CVFX  → cast VFX (model path)
  BVFX  → bolt VFX
  HVFX  → hit VFX
  AVFX  → area VFX
  DESC  → description text
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, decode_string, pack_subrec_header, pack_i32, unpack_i32
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord

SKDT_FMT = "<iiffff"
SKDT_SIZE = struct.calcsize(SKDT_FMT)  # 24

MEDT_FMT = "<ifiiiifff"   # school + base_cost + flags + red + green + blue + speed + size + size_cap
MEDT_SIZE = struct.calcsize(MEDT_FMT)  # 36


@dataclass
class Skill(BaseRecord):
    """SKIL record — skill definition."""

    REC_TYPE = b"SKIL"

    flags: int = 0
    unknown: int = 0
    skill_index: int = 0
    attribute: int = 0
    specialization: int = 0
    use_values: list[float] = field(default_factory=lambda: [0.0] * 4)
    description: str = ""

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Skill":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        indx = raw.get_subrecord(b"INDX")
        if indx and len(indx.data) >= 4:
            obj.skill_index = unpack_i32(indx.data)

        skdt = raw.get_subrecord(b"SKDT")
        if skdt and len(skdt.data) >= SKDT_SIZE:
            vals = struct.unpack_from(SKDT_FMT, skdt.data)
            obj.attribute      = vals[0]
            obj.specialization = vals[1]
            obj.use_values     = list(vals[2:6])

        desc = raw.get_subrecord(b"DESC")
        if desc:
            obj.description = decode_string(desc.data)

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()
        out += pack_subrec_header(b"INDX", 4) + pack_i32(self.skill_index)
        uv = (list(self.use_values) + [0.0] * 4)[:4]
        out += pack_subrec_header(b"SKDT", SKDT_SIZE)
        out += struct.pack(SKDT_FMT, self.attribute, self.specialization, *uv)
        if self.description:
            d = self.description.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"DESC", len(d)) + d
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "SKIL",
            "skill_index": self.skill_index,
            "attribute": self.attribute,
            "specialization": self.specialization,
            "use_values": self.use_values,
            "description": self.description,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Skill":
        obj = cls()
        obj.skill_index    = d.get("skill_index", 0)
        obj.attribute      = d.get("attribute", 0)
        obj.specialization = d.get("specialization", 0)
        obj.use_values     = d.get("use_values", [0.0] * 4)
        obj.description    = d.get("description", "")
        obj.flags          = d.get("flags", 0)
        return obj


@dataclass
class MagicEffect(BaseRecord):
    """MGEF record — magic effect definition."""

    REC_TYPE = b"MGEF"

    flags: int = 0
    unknown: int = 0
    effect_index: int = 0
    school: int = 0
    base_cost: float = 0.0
    effect_flags: int = 0
    color: int = 0          # RGB packed int
    speed: float = 1.0
    size: float = 1.0
    size_cap: float = 50.0
    icon: str = ""
    particle: str = ""
    bolt_sound: RefId = field(default_factory=EmptyRefId)
    cast_sound: RefId = field(default_factory=EmptyRefId)
    hit_sound: RefId = field(default_factory=EmptyRefId)
    area_sound: RefId = field(default_factory=EmptyRefId)
    cast_vfx: str = ""
    bolt_vfx: str = ""
    hit_vfx: str = ""
    area_vfx: str = ""
    description: str = ""

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "MagicEffect":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        indx = raw.get_subrecord(b"INDX")
        if indx and len(indx.data) >= 4:
            obj.effect_index = unpack_i32(indx.data)

        medt = raw.get_subrecord(b"MEDT")
        if medt and len(medt.data) >= MEDT_SIZE:
            vals = struct.unpack_from(MEDT_FMT, medt.data)
            school, base_cost, effect_flags, red, green, blue, speed, size, size_cap = vals[:9]
            obj.school        = school
            obj.base_cost     = base_cost
            obj.effect_flags  = effect_flags
            obj.color         = (red << 16) | (green << 8) | blue
            obj.speed         = speed
            obj.size          = size
            obj.size_cap      = size_cap

        def get_cstr(tag: bytes) -> str:
            sub = raw.get_subrecord(tag)
            return decode_cstring(sub.data) if sub else ""

        def get_refid(tag: bytes) -> RefId:
            sub = raw.get_subrecord(tag)
            return decode_refid_from_subrecord(sub.data, format_version) if sub else EmptyRefId()

        obj.icon       = get_cstr(b"ITEX")
        obj.particle   = get_cstr(b"PTEX")
        obj.bolt_sound = get_refid(b"BSND")
        obj.cast_sound = get_refid(b"CSND")
        obj.hit_sound  = get_refid(b"HSND")
        obj.area_sound = get_refid(b"ASND")
        obj.cast_vfx   = get_cstr(b"CVFX")
        obj.bolt_vfx   = get_cstr(b"BVFX")
        obj.hit_vfx    = get_cstr(b"HVFX")
        obj.area_vfx   = get_cstr(b"AVFX")

        desc = raw.get_subrecord(b"DESC")
        if desc:
            obj.description = decode_string(desc.data)

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_refid_opt(tag: bytes, ref: RefId) -> None:
            # Skip if empty — OpenMW uses writeHNOString for optional sound/VFX refs
            if isinstance(ref, EmptyRefId):
                return
            data = encode_refid_to_subrecord(ref, format_version)
            out.extend(pack_subrec_header(tag, len(data)) + data)

        def add_cstr(tag: bytes, s: str) -> None:
            if s:
                d = encode_cstring(s)
                out.extend(pack_subrec_header(tag, len(d)) + d)

        out += pack_subrec_header(b"INDX", 4) + pack_i32(self.effect_index)

        r = (self.color >> 16) & 0xFF
        g = (self.color >> 8) & 0xFF
        b = self.color & 0xFF
        out += pack_subrec_header(b"MEDT", MEDT_SIZE)
        out += struct.pack(MEDT_FMT, self.school, self.base_cost, self.effect_flags,
                           r, g, b, self.speed, self.size, self.size_cap)

        add_cstr(b"ITEX", self.icon)
        add_cstr(b"PTEX", self.particle)
        add_refid_opt(b"BSND", self.bolt_sound)
        add_refid_opt(b"CSND", self.cast_sound)
        add_refid_opt(b"HSND", self.hit_sound)
        add_refid_opt(b"ASND", self.area_sound)
        add_cstr(b"CVFX", self.cast_vfx)
        add_cstr(b"BVFX", self.bolt_vfx)
        add_cstr(b"HVFX", self.hit_vfx)
        add_cstr(b"AVFX", self.area_vfx)

        if self.description:
            d = self.description.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"DESC", len(d)) + d

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "MGEF",
            "effect_index": self.effect_index,
            "school": self.school,
            "base_cost": self.base_cost,
            "effect_flags": self.effect_flags,
            "color": self.color,
            "speed": self.speed,
            "size": self.size,
            "size_cap": self.size_cap,
            "icon": self.icon,
            "particle": self.particle,
            "bolt_sound": refid_to_db_text(self.bolt_sound),
            "cast_sound": refid_to_db_text(self.cast_sound),
            "hit_sound": refid_to_db_text(self.hit_sound),
            "area_sound": refid_to_db_text(self.area_sound),
            "cast_vfx": self.cast_vfx,
            "bolt_vfx": self.bolt_vfx,
            "hit_vfx": self.hit_vfx,
            "area_vfx": self.area_vfx,
            "description": self.description,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MagicEffect":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.effect_index  = d.get("effect_index", 0)
        obj.school        = d.get("school", 0)
        obj.base_cost     = d.get("base_cost", 0.0)
        obj.effect_flags  = d.get("effect_flags", 0)
        obj.color         = d.get("color", 0)
        obj.speed         = d.get("speed", 1.0)
        obj.size          = d.get("size", 1.0)
        obj.size_cap      = d.get("size_cap", 50.0)
        obj.icon          = d.get("icon", "")
        obj.particle      = d.get("particle", "")
        obj.bolt_sound    = refid_from_db_text(d.get("bolt_sound", ""))
        obj.cast_sound    = refid_from_db_text(d.get("cast_sound", ""))
        obj.hit_sound     = refid_from_db_text(d.get("hit_sound", ""))
        obj.area_sound    = refid_from_db_text(d.get("area_sound", ""))
        obj.cast_vfx      = d.get("cast_vfx", "")
        obj.bolt_vfx      = d.get("bolt_vfx", "")
        obj.hit_vfx       = d.get("hit_vfx", "")
        obj.area_vfx      = d.get("area_vfx", "")
        obj.description   = d.get("description", "")
        obj.flags         = d.get("flags", 0)
        return obj
