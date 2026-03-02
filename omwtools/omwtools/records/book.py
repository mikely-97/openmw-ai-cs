"""BOOK — Book/scroll record.

Subrecords:
  NAME  → record_id (RefId)
  MODL  → mesh path
  FNAM  → display name
  BKDT  → book data (20 bytes: float weight + int32 value + int32 scroll +
                      int32 teaches_skill + int32 enchant_pts)
  SCRI  → script RefId
  ITEX  → icon path
  TEXT  → book body text (HTML)
  ENAM  → enchantment RefId
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, decode_string, pack_subrec_header
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord

BKDT_FMT = "<fiiii"
BKDT_SIZE = struct.calcsize(BKDT_FMT)  # 20


@dataclass
class Book(BaseRecord):
    """BOOK record — book or scroll."""

    REC_TYPE = b"BOOK"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    weight: float = 0.0
    value: int = 0
    scroll: int = 0         # 1 = scroll
    teaches_skill: int = -1 # -1 = no skill
    enchant_pts: int = 0
    script: RefId = field(default_factory=EmptyRefId)
    icon: str = ""
    text: str = ""
    enchantment: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Book":
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

        bkdt = raw.get_subrecord(b"BKDT")
        if bkdt and len(bkdt.data) >= BKDT_SIZE:
            obj.weight, obj.value, obj.scroll, obj.teaches_skill, obj.enchant_pts = (
                struct.unpack_from(BKDT_FMT, bkdt.data)
            )

        obj.script = get_refid(b"SCRI")

        itex = raw.get_subrecord(b"ITEX")
        if itex:
            obj.icon = decode_cstring(itex.data)

        txt = raw.get_subrecord(b"TEXT")
        if txt:
            obj.text = decode_string(txt.data)

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

        out += pack_subrec_header(b"BKDT", BKDT_SIZE)
        out += struct.pack(BKDT_FMT, self.weight, self.value, self.scroll,
                           self.teaches_skill, self.enchant_pts)

        add_refid(b"SCRI", self.script)
        if self.icon:
            add_cstr(b"ITEX", self.icon)
        if self.text:
            txt_bytes = self.text.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"TEXT", len(txt_bytes)) + txt_bytes
        add_refid(b"ENAM", self.enchantment)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "BOOK",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "name": self.name,
            "weight": self.weight,
            "value": self.value,
            "scroll": self.scroll,
            "teaches_skill": self.teaches_skill,
            "enchant_pts": self.enchant_pts,
            "script": refid_to_db_text(self.script),
            "icon": self.icon,
            "text": self.text,
            "enchantment": refid_to_db_text(self.enchantment),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Book":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id     = refid_from_db_text(d.get("record_id", ""))
        obj.mesh          = d.get("mesh", "")
        obj.name          = d.get("name", "")
        obj.weight        = d.get("weight", 0.0)
        obj.value         = d.get("value", 0)
        obj.scroll        = d.get("scroll", 0)
        obj.teaches_skill = d.get("teaches_skill", -1)
        obj.enchant_pts   = d.get("enchant_pts", 0)
        obj.script        = refid_from_db_text(d.get("script", ""))
        obj.icon          = d.get("icon", "")
        obj.text          = d.get("text", "")
        obj.enchantment   = refid_from_db_text(d.get("enchantment", ""))
        obj.flags         = d.get("flags", 0)
        return obj
