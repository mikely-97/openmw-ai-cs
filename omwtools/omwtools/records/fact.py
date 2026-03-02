"""FACT and CLAS records — Faction and Class.

FACT:
  NAME  → record_id (RefId)
  FNAM  → display name
  RNAM  → rank names (up to 10, one per subrecord)
  FADT  → faction data (240 bytes):
            int32 attr1 + int32 attr2 (favoured attributes)
            RankData[10]: int32 attr1_req + int32 attr2_req + int32 skill1_req +
                          int32 skill2_req + int32 faction_req = 50 ints = 200 bytes
            int32[7] skill_ids (favoured skills)
            int32 flags (0x1=hidden)
  ANAM  → reaction faction RefId (followed by INTV reaction value)
  INTV  → reaction value (int32, follows ANAM)

CLAS:
  NAME  → record_id (RefId)
  FNAM  → display name
  CLDT  → class data (60 bytes):
            int32 attr1 + int32 attr2 (primary attributes)
            int32 specialization (0=combat, 1=magic, 2=stealth)
            int32[5] minor_skills + int32[5] major_skills
            int32 flags (0x1=playable, 0x2=autocalc)
            int32 auto_calc_services (bitfield)
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

# FADT: int32 × 2 + (int32 × 5) × 10 + int32 × 7 + int32 = 2 + 50 + 7 + 1 = 60 ints = 240 bytes
FADT_FMT = "<" + "i" * 60
FADT_SIZE = struct.calcsize(FADT_FMT)  # 240

# CLDT: int32 × 15 = 60 bytes
CLDT_FMT = "<" + "i" * 15
CLDT_SIZE = struct.calcsize(CLDT_FMT)  # 60


@dataclass
class RankData:
    attr1_req: int = 0
    attr2_req: int = 0
    skill1_req: int = 0
    skill2_req: int = 0
    faction_req: int = 0


@dataclass
class Reaction:
    faction: RefId = field(default_factory=EmptyRefId)
    value: int = 0


@dataclass
class Faction(BaseRecord):
    """FACT record — faction."""

    REC_TYPE = b"FACT"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    name: str = ""
    rank_names: list[str] = field(default_factory=list)
    attr1: int = 0
    attr2: int = 0
    ranks: list[RankData] = field(default_factory=list)
    skill_ids: list[int] = field(default_factory=lambda: [-1] * 7)
    fact_flags: int = 0
    reactions: list[Reaction] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Faction":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        for sub in raw.get_subrecords(b"RNAM"):
            obj.rank_names.append(decode_cstring(sub.data))

        fadt = raw.get_subrecord(b"FADT")
        if fadt and len(fadt.data) >= FADT_SIZE:
            vals = struct.unpack_from(FADT_FMT, fadt.data)
            obj.attr1 = vals[0]
            obj.attr2 = vals[1]
            obj.ranks = [
                RankData(vals[2 + i*5], vals[3 + i*5], vals[4 + i*5], vals[5 + i*5], vals[6 + i*5])
                for i in range(10)
            ]
            obj.skill_ids = list(vals[52:59])
            obj.fact_flags = vals[59]

        # ANAM/INTV pairs
        subs = raw.subrecords
        i = 0
        while i < len(subs):
            if subs[i].sub_type == b"ANAM":
                fac = decode_refid_from_subrecord(subs[i].data, format_version)
                val = 0
                if i + 1 < len(subs) and subs[i + 1].sub_type == b"INTV":
                    val = unpack_i32(subs[i + 1].data)
                    i += 1
                obj.reactions.append(Reaction(fac, val))
            i += 1

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

        for rn in self.rank_names:
            d = encode_cstring(rn)
            out += pack_subrec_header(b"RNAM", len(d)) + d

        ranks = (list(self.ranks) + [RankData()] * 10)[:10]
        skill_ids = (list(self.skill_ids) + [-1] * 7)[:7]
        vals = [self.attr1, self.attr2]
        for r in ranks:
            vals += [r.attr1_req, r.attr2_req, r.skill1_req, r.skill2_req, r.faction_req]
        vals += skill_ids
        vals.append(self.fact_flags)
        out += pack_subrec_header(b"FADT", FADT_SIZE)
        out += struct.pack(FADT_FMT, *vals)

        for rxn in self.reactions:
            add_refid(b"ANAM", rxn.faction)
            out += pack_subrec_header(b"INTV", 4) + pack_i32(rxn.value)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "FACT",
            "record_id": refid_to_db_text(self.record_id),
            "name": self.name,
            "rank_names": self.rank_names,
            "attr1": self.attr1,
            "attr2": self.attr2,
            "ranks": [{"attr1_req": r.attr1_req, "attr2_req": r.attr2_req,
                       "skill1_req": r.skill1_req, "skill2_req": r.skill2_req,
                       "faction_req": r.faction_req} for r in self.ranks],
            "skill_ids": self.skill_ids,
            "fact_flags": self.fact_flags,
            "reactions": [{"faction": refid_to_db_text(r.faction), "value": r.value}
                          for r in self.reactions],
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Faction":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id  = refid_from_db_text(d.get("record_id", ""))
        obj.name       = d.get("name", "")
        obj.rank_names = d.get("rank_names", [])
        obj.attr1      = d.get("attr1", 0)
        obj.attr2      = d.get("attr2", 0)
        obj.ranks      = [RankData(**r) for r in d.get("ranks", [])]
        obj.skill_ids  = d.get("skill_ids", [-1] * 7)
        obj.fact_flags = d.get("fact_flags", 0)
        obj.reactions  = [Reaction(refid_from_db_text(r["faction"]), r["value"])
                          for r in d.get("reactions", [])]
        obj.flags      = d.get("flags", 0)
        return obj


@dataclass
class Class(BaseRecord):
    """CLAS record — character class."""

    REC_TYPE = b"CLAS"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    name: str = ""
    attr1: int = 0
    attr2: int = 0
    specialization: int = 0
    minor_skills: list[int] = field(default_factory=lambda: [0] * 5)
    major_skills: list[int] = field(default_factory=lambda: [0] * 5)
    clas_flags: int = 0
    auto_calc_services: int = 0
    description: str = ""

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Class":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        cldt = raw.get_subrecord(b"CLDT")
        if cldt and len(cldt.data) >= CLDT_SIZE:
            vals = struct.unpack_from(CLDT_FMT, cldt.data)
            obj.attr1             = vals[0]
            obj.attr2             = vals[1]
            obj.specialization    = vals[2]
            obj.minor_skills      = list(vals[3:8])
            obj.major_skills      = list(vals[8:13])
            obj.clas_flags        = vals[13]
            obj.auto_calc_services = vals[14]

        desc = raw.get_subrecord(b"DESC")
        if desc:
            obj.description = decode_string(desc.data)

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out += pack_subrec_header(b"NAME", len(id_data)) + id_data

        if self.name:
            n = encode_cstring(self.name)
            out += pack_subrec_header(b"FNAM", len(n)) + n

        minor = (list(self.minor_skills) + [0] * 5)[:5]
        major = (list(self.major_skills) + [0] * 5)[:5]
        vals = [self.attr1, self.attr2, self.specialization] + minor + major + [self.clas_flags, self.auto_calc_services]
        out += pack_subrec_header(b"CLDT", CLDT_SIZE)
        out += struct.pack(CLDT_FMT, *vals)

        if self.description:
            d = self.description.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"DESC", len(d)) + d

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "CLAS",
            "record_id": refid_to_db_text(self.record_id),
            "name": self.name,
            "attr1": self.attr1,
            "attr2": self.attr2,
            "specialization": self.specialization,
            "minor_skills": self.minor_skills,
            "major_skills": self.major_skills,
            "clas_flags": self.clas_flags,
            "auto_calc_services": self.auto_calc_services,
            "description": self.description,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Class":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id          = refid_from_db_text(d.get("record_id", ""))
        obj.name               = d.get("name", "")
        obj.attr1              = d.get("attr1", 0)
        obj.attr2              = d.get("attr2", 0)
        obj.specialization     = d.get("specialization", 0)
        obj.minor_skills       = d.get("minor_skills", [0] * 5)
        obj.major_skills       = d.get("major_skills", [0] * 5)
        obj.clas_flags         = d.get("clas_flags", 0)
        obj.auto_calc_services = d.get("auto_calc_services", 0)
        obj.description        = d.get("description", "")
        obj.flags              = d.get("flags", 0)
        return obj
