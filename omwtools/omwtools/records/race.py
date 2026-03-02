"""RACE and BSGN (Birthsign) records.

RACE:
  NAME  → record_id (RefId)
  FNAM  → display name
  RADT  → race data (140 bytes):
            SkillBonus[7] (int32 skill_id + int32 bonus) = 56 bytes
            Attributes[16] (int32 each) = 64 bytes  (male+female str,int,wil,agi,spd,end,per,luc)
            float height_male + float height_female +
            float weight_male + float weight_female +
            int32 flags
  DESC  → description text
  NPCS  → spell RefId (32-byte fixed string, repeating)

BSGN (Birthsign):
  NAME  → record_id (RefId)
  FNAM  → display name
  TNAM  → texture path (map icon)
  DESC  → description text
  NPCS  → spell/power RefId (32-byte fixed string, repeating)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, encode_fixed_string, decode_string, pack_subrec_header
from omwtools.io.refid import (
    RefId, EmptyRefId, StringRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord

# RADT layout:
#   7 × (int32 skill + int32 bonus) = 56 bytes
#   8 × int32 male_attrs + 8 × int32 female_attrs = 64 bytes
#   float height_m + float height_f + float weight_m + float weight_f + int32 flags = 20 bytes
# Total = 140 bytes
RADT_FMT = "<" + "ii" * 7 + "i" * 16 + "ffffi"
RADT_SIZE = struct.calcsize(RADT_FMT)  # 140


@dataclass
class SkillBonus:
    skill_id: int = -1
    bonus: int = 0


@dataclass
class Race(BaseRecord):
    """RACE record."""

    REC_TYPE = b"RACE"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    name: str = ""
    skill_bonuses: list[SkillBonus] = field(default_factory=list)
    male_attrs: list[int] = field(default_factory=lambda: [0] * 8)
    female_attrs: list[int] = field(default_factory=lambda: [0] * 8)
    height_male: float = 1.0
    height_female: float = 1.0
    weight_male: float = 1.0
    weight_female: float = 1.0
    race_flags: int = 0     # 0x1=playable, 0x2=beast_race
    description: str = ""
    spells: list[RefId] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Race":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        radt = raw.get_subrecord(b"RADT")
        if radt and len(radt.data) >= RADT_SIZE:
            vals = struct.unpack_from(RADT_FMT, radt.data)
            # First 14 values: 7 pairs of (skill, bonus)
            obj.skill_bonuses = [
                SkillBonus(skill_id=vals[i * 2], bonus=vals[i * 2 + 1])
                for i in range(7)
            ]
            # Next 16 values: 8 male + 8 female attributes
            obj.male_attrs   = list(vals[14:22])
            obj.female_attrs = list(vals[22:30])
            # Last 5: heights, weights, flags
            obj.height_male   = vals[30]
            obj.height_female = vals[31]
            obj.weight_male   = vals[32]
            obj.weight_female = vals[33]
            obj.race_flags    = vals[34]

        desc = raw.get_subrecord(b"DESC")
        if desc:
            obj.description = decode_string(desc.data)

        for sub in raw.get_subrecords(b"NPCS"):
            obj.spells.append(decode_refid_from_subrecord(sub.data, format_version))

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_refid(tag: bytes, ref: RefId) -> None:
            data = encode_refid_to_subrecord(ref, format_version)
            out.extend(pack_subrec_header(tag, len(data)) + data)

        add_refid(b"NAME", self.record_id)

        if self.name:
            n = encode_cstring(self.name)
            out += pack_subrec_header(b"FNAM", len(n)) + n

        bonuses = (list(self.skill_bonuses) + [SkillBonus()] * 7)[:7]
        male_a  = (list(self.male_attrs) + [0] * 8)[:8]
        female_a = (list(self.female_attrs) + [0] * 8)[:8]
        vals = []
        for sb in bonuses:
            vals += [sb.skill_id, sb.bonus]
        vals += male_a + female_a
        vals += [self.height_male, self.height_female,
                 self.weight_male, self.weight_female, self.race_flags]
        out += pack_subrec_header(b"RADT", RADT_SIZE)
        out += struct.pack(RADT_FMT, *vals)

        if self.description:
            d = self.description.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"DESC", len(d)) + d

        for spell in self.spells:
            if format_version <= 23:
                spell_name = spell.value if isinstance(spell, StringRefId) else ""
                spell_data = encode_fixed_string(spell_name, 32)
            else:
                spell_data = encode_refid_to_subrecord(spell, format_version)
            out.extend(pack_subrec_header(b"NPCS", len(spell_data)) + spell_data)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "RACE",
            "record_id": refid_to_db_text(self.record_id),
            "name": self.name,
            "skill_bonuses": [{"skill_id": sb.skill_id, "bonus": sb.bonus}
                              for sb in self.skill_bonuses],
            "male_attrs": self.male_attrs,
            "female_attrs": self.female_attrs,
            "height_male": self.height_male,
            "height_female": self.height_female,
            "weight_male": self.weight_male,
            "weight_female": self.weight_female,
            "race_flags": self.race_flags,
            "description": self.description,
            "spells": [refid_to_db_text(s) for s in self.spells],
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Race":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id     = refid_from_db_text(d.get("record_id", ""))
        obj.name          = d.get("name", "")
        obj.skill_bonuses = [SkillBonus(sb["skill_id"], sb["bonus"])
                             for sb in d.get("skill_bonuses", [])]
        obj.male_attrs    = d.get("male_attrs", [0] * 8)
        obj.female_attrs  = d.get("female_attrs", [0] * 8)
        obj.height_male   = d.get("height_male", 1.0)
        obj.height_female = d.get("height_female", 1.0)
        obj.weight_male   = d.get("weight_male", 1.0)
        obj.weight_female = d.get("weight_female", 1.0)
        obj.race_flags    = d.get("race_flags", 0)
        obj.description   = d.get("description", "")
        obj.spells        = [refid_from_db_text(s) for s in d.get("spells", [])]
        obj.flags         = d.get("flags", 0)
        return obj


@dataclass
class Birthsign(BaseRecord):
    """BSGN record — birthsign / character sign."""

    REC_TYPE = b"BSGN"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    name: str = ""
    texture: str = ""
    description: str = ""
    spells: list[RefId] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Birthsign":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        tnam = raw.get_subrecord(b"TNAM")
        if tnam:
            obj.texture = decode_cstring(tnam.data)

        desc = raw.get_subrecord(b"DESC")
        if desc:
            obj.description = decode_string(desc.data)

        for sub in raw.get_subrecords(b"NPCS"):
            obj.spells.append(decode_refid_from_subrecord(sub.data, format_version))

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
        if self.name:
            add_cstr(b"FNAM", self.name)
        if self.texture:
            add_cstr(b"TNAM", self.texture)
        if self.description:
            d = self.description.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"DESC", len(d)) + d
        for spell in self.spells:
            if format_version <= 23:
                spell_name = spell.value if isinstance(spell, StringRefId) else ""
                spell_data = encode_fixed_string(spell_name, 32)
            else:
                spell_data = encode_refid_to_subrecord(spell, format_version)
            out.extend(pack_subrec_header(b"NPCS", len(spell_data)) + spell_data)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "BSGN",
            "record_id": refid_to_db_text(self.record_id),
            "name": self.name,
            "texture": self.texture,
            "description": self.description,
            "spells": [refid_to_db_text(s) for s in self.spells],
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Birthsign":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.name        = d.get("name", "")
        obj.texture     = d.get("texture", "")
        obj.description = d.get("description", "")
        obj.spells      = [refid_from_db_text(s) for s in d.get("spells", [])]
        obj.flags       = d.get("flags", 0)
        return obj
