"""ARMO — Armour record.

Subrecords:
  NAME  → record_id (RefId)
  MODL  → mesh path
  FNAM  → display name
  AODT  → armour data (24 bytes: int32 type + float weight + int32 value +
                        int32 health + int32 enchant_pts + int32 armour_rating)
  SCRI  → script RefId
  ITEX  → icon path
  INDX  → part index (1 byte) — start of a part reference
  BNAM  → male body part mesh RefId (optional, follows INDX)
  CNAM  → female body part mesh RefId (optional, follows INDX)
  ENAM  → enchantment RefId (string RefId, not effect entry)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, pack_subrec_header, pack_u8
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord

AODT_FMT = "<ifiiii"
AODT_SIZE = struct.calcsize(AODT_FMT)  # 24


@dataclass
class PartRef:
    """One body-part reference: part index + optional male/female mesh."""
    index: int = 0
    male: RefId = field(default_factory=EmptyRefId)
    female: RefId = field(default_factory=EmptyRefId)


@dataclass
class Armour(BaseRecord):
    """ARMO record — armour piece."""

    REC_TYPE = b"ARMO"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    armo_type: int = 0
    weight: float = 0.0
    value: int = 0
    health: int = 0
    enchant_pts: int = 0
    armour_rating: int = 0
    script: RefId = field(default_factory=EmptyRefId)
    icon: str = ""
    parts: list[PartRef] = field(default_factory=list)
    enchantment: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Armour":
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

        aodt = raw.get_subrecord(b"AODT")
        if aodt and len(aodt.data) >= AODT_SIZE:
            (obj.armo_type, obj.weight, obj.value,
             obj.health, obj.enchant_pts, obj.armour_rating) = struct.unpack_from(AODT_FMT, aodt.data)

        obj.script = get_refid(b"SCRI")

        itex = raw.get_subrecord(b"ITEX")
        if itex:
            obj.icon = decode_cstring(itex.data)

        # INDX/BNAM/CNAM state machine
        current: PartRef | None = None
        for sub in raw.subrecords:
            if sub.sub_type == b"INDX":
                if current is not None:
                    obj.parts.append(current)
                current = PartRef(index=sub.data[0] if sub.data else 0)
            elif sub.sub_type == b"BNAM" and current is not None:
                current.male = decode_refid_from_subrecord(sub.data, format_version)
            elif sub.sub_type == b"CNAM" and current is not None:
                current.female = decode_refid_from_subrecord(sub.data, format_version)
        if current is not None:
            obj.parts.append(current)

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

        out += pack_subrec_header(b"AODT", AODT_SIZE)
        out += struct.pack(AODT_FMT, self.armo_type, self.weight, self.value,
                           self.health, self.enchant_pts, self.armour_rating)

        if not isinstance(self.script, EmptyRefId):
            add_refid(b"SCRI", self.script)
        if self.icon:
            add_cstr(b"ITEX", self.icon)

        for part in self.parts:
            out += pack_subrec_header(b"INDX", 1) + pack_u8(part.index)
            if not isinstance(part.male, EmptyRefId):
                add_refid(b"BNAM", part.male)
            if not isinstance(part.female, EmptyRefId):
                add_refid(b"CNAM", part.female)

        if not isinstance(self.enchantment, EmptyRefId):
            add_refid(b"ENAM", self.enchantment)
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "ARMO",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "name": self.name,
            "armo_type": self.armo_type,
            "weight": self.weight,
            "value": self.value,
            "health": self.health,
            "enchant_pts": self.enchant_pts,
            "armour_rating": self.armour_rating,
            "script": refid_to_db_text(self.script),
            "icon": self.icon,
            "parts": [
                {"index": p.index,
                 "male": refid_to_db_text(p.male),
                 "female": refid_to_db_text(p.female)}
                for p in self.parts
            ],
            "enchantment": refid_to_db_text(self.enchantment),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Armour":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id     = refid_from_db_text(d.get("record_id", ""))
        obj.mesh          = d.get("mesh", "")
        obj.name          = d.get("name", "")
        obj.armo_type     = d.get("armo_type", 0)
        obj.weight        = d.get("weight", 0.0)
        obj.value         = d.get("value", 0)
        obj.health        = d.get("health", 0)
        obj.enchant_pts   = d.get("enchant_pts", 0)
        obj.armour_rating = d.get("armour_rating", 0)
        obj.script        = refid_from_db_text(d.get("script", ""))
        obj.icon          = d.get("icon", "")
        obj.parts = [
            PartRef(
                index=p["index"],
                male=refid_from_db_text(p.get("male", "")),
                female=refid_from_db_text(p.get("female", "")),
            )
            for p in d.get("parts", [])
        ]
        obj.enchantment = refid_from_db_text(d.get("enchantment", ""))
        obj.flags       = d.get("flags", 0)
        return obj
