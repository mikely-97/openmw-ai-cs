"""DOOR, ACTI, STAT — simple world-object records.

DOOR — Door
  NAME, MODL, FNAM, SCRI, SNAM (open sound), ANAM (close sound)

ACTI — Activator
  NAME, MODL, FNAM, SCRI

STAT — Static object
  NAME, MODL
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, pack_subrec_header
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord


@dataclass
class Door(BaseRecord):
    """DOOR record."""

    REC_TYPE = b"DOOR"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    script: RefId = field(default_factory=EmptyRefId)
    open_sound: RefId = field(default_factory=EmptyRefId)
    close_sound: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Door":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        def get_refid(tag: bytes) -> RefId:
            sub = raw.get_subrecord(tag)
            return decode_refid_from_subrecord(sub.data, format_version) if sub else EmptyRefId()

        obj.record_id  = get_refid(b"NAME")
        modl = raw.get_subrecord(b"MODL")
        if modl:
            obj.mesh = decode_cstring(modl.data)
        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)
        obj.script      = get_refid(b"SCRI")
        obj.open_sound  = get_refid(b"SNAM")
        obj.close_sound = get_refid(b"ANAM")
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_refid(tag: bytes, ref: RefId) -> None:
            data = encode_refid_to_subrecord(ref, format_version)
            out.extend(pack_subrec_header(tag, len(data)) + data)

        def add_refid_opt(tag: bytes, ref: RefId) -> None:
            if isinstance(ref, EmptyRefId):
                return
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
        add_refid_opt(b"SCRI", self.script)
        add_refid_opt(b"SNAM", self.open_sound)
        add_refid_opt(b"ANAM", self.close_sound)
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "DOOR",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh, "name": self.name,
            "script": refid_to_db_text(self.script),
            "open_sound": refid_to_db_text(self.open_sound),
            "close_sound": refid_to_db_text(self.close_sound),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Door":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.mesh        = d.get("mesh", "")
        obj.name        = d.get("name", "")
        obj.script      = refid_from_db_text(d.get("script", ""))
        obj.open_sound  = refid_from_db_text(d.get("open_sound", ""))
        obj.close_sound = refid_from_db_text(d.get("close_sound", ""))
        obj.flags       = d.get("flags", 0)
        return obj


@dataclass
class Activator(BaseRecord):
    """ACTI record — activator."""

    REC_TYPE = b"ACTI"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    script: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Activator":
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
        obj.script = get_refid(b"SCRI")
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
        if not isinstance(self.script, EmptyRefId):
            add_refid(b"SCRI", self.script)
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "ACTI",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh, "name": self.name,
            "script": refid_to_db_text(self.script),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Activator":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id = refid_from_db_text(d.get("record_id", ""))
        obj.mesh      = d.get("mesh", "")
        obj.name      = d.get("name", "")
        obj.script    = refid_from_db_text(d.get("script", ""))
        obj.flags     = d.get("flags", 0)
        return obj


@dataclass
class Static(BaseRecord):
    """STAT record — static mesh."""

    REC_TYPE = b"STAT"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Static":
        obj = cls(flags=raw.flags, unknown=raw.unknown)
        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)
        modl = raw.get_subrecord(b"MODL")
        if modl:
            obj.mesh = decode_cstring(modl.data)
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()
        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out += pack_subrec_header(b"NAME", len(id_data)) + id_data
        if self.mesh:
            d = encode_cstring(self.mesh)
            out += pack_subrec_header(b"MODL", len(d)) + d
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "STAT",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Static":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id = refid_from_db_text(d.get("record_id", ""))
        obj.mesh      = d.get("mesh", "")
        obj.flags     = d.get("flags", 0)
        return obj
