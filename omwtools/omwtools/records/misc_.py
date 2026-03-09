"""Miscellaneous simple item records: MISC, LOCK, PROB, REPA, APPA.

MISC — Miscellaneous item
  NAME, MODL, FNAM, MCDT (12 bytes: float+int32+int32), SCRI, ITEX, ENAM

LOCK — Lockpick
  NAME, MODL, FNAM, LKDT (16 bytes: float+int32+float+int32), SCRI, ITEX

PROB — Probe
  NAME, MODL, FNAM, PBDT (16 bytes: float+int32+float+int32), SCRI, ITEX

REPA — Repair item
  NAME, MODL, FNAM, RIDT (16 bytes: float+int32+int32+float), SCRI, ITEX

APPA — Apparatus (alchemy equipment)
  NAME, MODL, FNAM, AADT (16 bytes: int32 type+float weight+float quality+int32 value), SCRI, ITEX
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

# Struct formats
MCDT_FMT = "<fii"
LKDT_FMT = "<fifi"
PBDT_FMT = "<fifi"
RIDT_FMT = "<fiif"
AADT_FMT = "<iffi"

MCDT_SIZE = struct.calcsize(MCDT_FMT)  # 12
LKDT_SIZE = struct.calcsize(LKDT_FMT)  # 16
PBDT_SIZE = struct.calcsize(PBDT_FMT)  # 16
RIDT_SIZE = struct.calcsize(RIDT_FMT)  # 16
AADT_SIZE = struct.calcsize(AADT_FMT)  # 16


# ---------------------------------------------------------------------------
# Actual record classes
# ---------------------------------------------------------------------------

@dataclass
class MiscItem(BaseRecord):
    """MISC record — miscellaneous item."""
    REC_TYPE = b"MISC"
    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    weight: float = 0.0
    value: int = 0
    unknown2: int = 0
    script: RefId = field(default_factory=EmptyRefId)
    icon: str = ""
    enchantment: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "MiscItem":
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
        mcdt = raw.get_subrecord(b"MCDT")
        if mcdt and len(mcdt.data) >= MCDT_SIZE:
            obj.weight, obj.value, obj.unknown2 = struct.unpack_from(MCDT_FMT, mcdt.data)
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

        def add_refid_opt(tag: bytes, ref: RefId) -> None:
            if isinstance(ref, EmptyRefId):
                return
            data = encode_refid_to_subrecord(ref, format_version)
            out.extend(pack_subrec_header(tag, len(data)) + data)

        add_refid(b"NAME", self.record_id)
        if self.mesh:
            add_cstr(b"MODL", self.mesh)
        if self.name:
            add_cstr(b"FNAM", self.name)
        out += pack_subrec_header(b"MCDT", MCDT_SIZE)
        out += struct.pack(MCDT_FMT, self.weight, self.value, self.unknown2)
        add_refid_opt(b"SCRI", self.script)
        if self.icon:
            add_cstr(b"ITEX", self.icon)
        # MISC records do not support ENAM in OpenMW — enchantment effects must
        # be driven by script instead. Do not write ENAM.
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "MISC",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh, "name": self.name,
            "weight": self.weight, "value": self.value, "unknown2": self.unknown2,
            "script": refid_to_db_text(self.script),
            "icon": self.icon,
            "enchantment": refid_to_db_text(self.enchantment),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MiscItem":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.mesh        = d.get("mesh", "")
        obj.name        = d.get("name", "")
        obj.weight      = d.get("weight", 0.0)
        obj.value       = d.get("value", 0)
        obj.unknown2    = d.get("unknown2", 0)
        obj.script      = refid_from_db_text(d.get("script", ""))
        obj.icon        = d.get("icon", "")
        obj.enchantment = refid_from_db_text(d.get("enchantment", ""))
        obj.flags       = d.get("flags", 0)
        return obj


def _simple_item(rec_type: bytes, data_tag: bytes, data_fmt: str, data_size: int,
                 field_defs: list[tuple[str, Any]]):
    """Generate a simple item dataclass (no enchantment)."""
    fnames = [fn for fn, _ in field_defs]
    fdefs  = [fv for _, fv in field_defs]

    @dataclass
    class _Rec(BaseRecord):
        REC_TYPE = rec_type
        flags: int = 0
        unknown: int = 0
        record_id: RefId = field(default_factory=EmptyRefId)
        mesh: str = ""
        name: str = ""
        script: RefId = field(default_factory=EmptyRefId)
        icon: str = ""

        @classmethod
        def from_raw(cls, raw: RawRecord, format_version: int) -> "_Rec":
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
            dsub = raw.get_subrecord(data_tag)
            if dsub and len(dsub.data) >= data_size:
                vals = struct.unpack_from(data_fmt, dsub.data)
                for fn, v in zip(fnames, vals):
                    setattr(obj, fn, v)
            obj.script = get_refid(b"SCRI")
            itex = raw.get_subrecord(b"ITEX")
            if itex:
                obj.icon = decode_cstring(itex.data)
            return obj

        def encode_subrecords(self, format_version: int) -> bytes:
            out = bytearray()

            def add_refid(tag: bytes, ref: RefId) -> None:
                data = encode_refid_to_subrecord(ref, format_version)
                out.extend(pack_subrec_header(tag, len(data)) + data)

            def add_cstr(tag: bytes, s: str) -> None:
                d = encode_cstring(s)
                out.extend(pack_subrec_header(tag, len(d)) + d)

            def add_refid_opt(tag: bytes, ref: RefId) -> None:
                if isinstance(ref, EmptyRefId):
                    return
                data = encode_refid_to_subrecord(ref, format_version)
                out.extend(pack_subrec_header(tag, len(data)) + data)

            add_refid(b"NAME", self.record_id)
            if self.mesh:
                add_cstr(b"MODL", self.mesh)
            if self.name:
                add_cstr(b"FNAM", self.name)
            vals = tuple(getattr(self, fn) for fn in fnames)
            out += pack_subrec_header(data_tag, data_size) + struct.pack(data_fmt, *vals)
            add_refid_opt(b"SCRI", self.script)
            if self.icon:
                add_cstr(b"ITEX", self.icon)
            return bytes(out)

        def to_dict(self) -> dict[str, Any]:
            d: dict[str, Any] = {
                "rec_type": rec_type.decode(),
                "record_id": refid_to_db_text(self.record_id),
                "mesh": self.mesh, "name": self.name,
                "script": refid_to_db_text(self.script),
                "icon": self.icon, "flags": self.flags,
            }
            for fn in fnames:
                d[fn] = getattr(self, fn)
            return d

        @classmethod
        def from_dict(cls, d: dict[str, Any]) -> "_Rec":
            from omwtools.io.refid import refid_from_db_text
            obj = cls()
            obj.record_id = refid_from_db_text(d.get("record_id", ""))
            obj.mesh      = d.get("mesh", "")
            obj.name      = d.get("name", "")
            obj.script    = refid_from_db_text(d.get("script", ""))
            obj.icon      = d.get("icon", "")
            obj.flags     = d.get("flags", 0)
            for fn, fdef in zip(fnames, fdefs):
                setattr(obj, fn, d.get(fn, fdef))
            return obj

    # Inject data fields as class attributes (dataclass won't see them but
    # from_raw/encode will work via setattr/getattr)
    for fn, fdef in zip(fnames, fdefs):
        setattr(_Rec, fn, fdef)
    _Rec.__name__ = rec_type.decode()
    _Rec.__qualname__ = rec_type.decode()
    return _Rec


Lockpick = _simple_item(
    b"LOCK", b"LKDT", LKDT_FMT, LKDT_SIZE,
    [("weight", 0.0), ("value", 0), ("quality", 0.0), ("uses", 0)],
)

Probe = _simple_item(
    b"PROB", b"PBDT", PBDT_FMT, PBDT_SIZE,
    [("weight", 0.0), ("value", 0), ("quality", 0.0), ("uses", 0)],
)

RepairItem = _simple_item(
    b"REPA", b"RIDT", RIDT_FMT, RIDT_SIZE,
    [("weight", 0.0), ("value", 0), ("uses", 0), ("quality", 0.0)],
)

Apparatus = _simple_item(
    b"APPA", b"AADT", AADT_FMT, AADT_SIZE,
    # AADTstruct order: mType, mQuality, mWeight, mValue
    [("appa_type", 0), ("quality", 0.0), ("weight", 0.0), ("value", 0)],
)
