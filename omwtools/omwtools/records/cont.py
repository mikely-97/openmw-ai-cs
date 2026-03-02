"""CONT — Container record.

Subrecords:
  NAME  → record_id (RefId)
  MODL  → mesh path
  FNAM  → display name
  CNDT  → container capacity (float, 4 bytes)
  FLAG  → container flags (int32: 0x1=organic, 0x2=respawns, 0x8=default)
  SCRI  → script RefId
  NPCO  → inventory item (int32 count + RefId)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, encode_fixed_string, pack_subrec_header, pack_i32, unpack_i32
from omwtools.io.refid import (
    RefId, EmptyRefId, StringRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord


@dataclass
class ContItem:
    """One container inventory slot: count + item RefId."""
    count: int = 0
    item_id: RefId = field(default_factory=EmptyRefId)


@dataclass
class Container(BaseRecord):
    """CONT record — container."""

    REC_TYPE = b"CONT"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    capacity: float = 0.0
    cont_flags: int = 0
    script: RefId = field(default_factory=EmptyRefId)
    inventory: list[ContItem] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Container":
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

        cndt = raw.get_subrecord(b"CNDT")
        if cndt and len(cndt.data) >= 4:
            obj.capacity = struct.unpack_from("<f", cndt.data)[0]

        flag_sub = raw.get_subrecord(b"FLAG")
        if flag_sub and len(flag_sub.data) >= 4:
            obj.cont_flags = unpack_i32(flag_sub.data)

        obj.script = get_refid(b"SCRI")

        for sub in raw.get_subrecords(b"NPCO"):
            if len(sub.data) >= 4:
                count = unpack_i32(sub.data)
                item_id = decode_refid_from_subrecord(sub.data[4:], format_version)
                obj.inventory.append(ContItem(count, item_id))

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

        out += pack_subrec_header(b"CNDT", 4) + struct.pack("<f", self.capacity)
        out += pack_subrec_header(b"FLAG", 4) + pack_i32(self.cont_flags)

        if not isinstance(self.script, EmptyRefId):
            add_refid(b"SCRI", self.script)

        for item in self.inventory:
            if format_version <= 23:
                id_name = item.item_id.value if isinstance(item.item_id, StringRefId) else ""
                id_data = encode_fixed_string(id_name, 32)
            else:
                id_data = encode_refid_to_subrecord(item.item_id, format_version)
            item_data = pack_i32(item.count) + id_data
            out += pack_subrec_header(b"NPCO", len(item_data)) + item_data

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "CONT",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "name": self.name,
            "capacity": self.capacity,
            "cont_flags": self.cont_flags,
            "script": refid_to_db_text(self.script),
            "inventory": [
                {"count": it.count, "item_id": refid_to_db_text(it.item_id)}
                for it in self.inventory
            ],
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Container":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id  = refid_from_db_text(d.get("record_id", ""))
        obj.mesh       = d.get("mesh", "")
        obj.name       = d.get("name", "")
        obj.capacity   = d.get("capacity", 0.0)
        obj.cont_flags = d.get("cont_flags", 0)
        obj.script     = refid_from_db_text(d.get("script", ""))
        obj.inventory  = [
            ContItem(it["count"], refid_from_db_text(it["item_id"]))
            for it in d.get("inventory", [])
        ]
        obj.flags = d.get("flags", 0)
        return obj
