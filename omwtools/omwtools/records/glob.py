"""GLOB and GMST records — Global Variables and Game Settings.

GLOB:
  NAME  → record_id (RefId)
  FNAM  → type char: 's' (short), 'l' (long), 'f' (float)
  FLTV  → value (float, always stored as float regardless of type)

GMST:
  NAME  → record_id (RefId)
  STRV  → string value (if string type)
  INTV  → int32 value (if int type)
  FLTV  → float value (if float type)
  (absent if no value set — VT_None)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from omwtools.io.codec import decode_cstring, encode_cstring, decode_string, pack_subrec_header, pack_i32, unpack_i32
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord


@dataclass
class GlobalVariable(BaseRecord):
    """GLOB record — global variable."""

    REC_TYPE = b"GLOB"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    var_type: str = "f"   # 's', 'l', or 'f'
    value: float = 0.0

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "GlobalVariable":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam and fnam.data:
            obj.var_type = chr(fnam.data[0])

        fltv = raw.get_subrecord(b"FLTV")
        if fltv and len(fltv.data) >= 4:
            obj.value = struct.unpack_from("<f", fltv.data)[0]

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out += pack_subrec_header(b"NAME", len(id_data)) + id_data

        type_byte = self.var_type.encode("ascii")[:1]
        out += pack_subrec_header(b"FNAM", 1) + type_byte
        out += pack_subrec_header(b"FLTV", 4) + struct.pack("<f", self.value)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "GLOB",
            "record_id": refid_to_db_text(self.record_id),
            "var_type": self.var_type,
            "value": self.value,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GlobalVariable":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id = refid_from_db_text(d.get("record_id", ""))
        obj.var_type  = d.get("var_type", "f")
        obj.value     = d.get("value", 0.0)
        obj.flags     = d.get("flags", 0)
        return obj


@dataclass
class GameSetting(BaseRecord):
    """GMST record — game setting."""

    REC_TYPE = b"GMST"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    str_value: Optional[str] = None
    int_value: Optional[int] = None
    float_value: Optional[float] = None

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "GameSetting":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        strv = raw.get_subrecord(b"STRV")
        if strv is not None:
            obj.str_value = decode_string(strv.data)

        intv = raw.get_subrecord(b"INTV")
        if intv and len(intv.data) >= 4:
            obj.int_value = unpack_i32(intv.data)

        fltv = raw.get_subrecord(b"FLTV")
        if fltv and len(fltv.data) >= 4:
            obj.float_value = struct.unpack_from("<f", fltv.data)[0]

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out += pack_subrec_header(b"NAME", len(id_data)) + id_data

        if self.str_value is not None:
            sv = self.str_value.encode("cp1252", errors="replace")
            if not sv:
                sv = b"\x00"  # empty string stored as single null byte (OpenMW convention)
            out += pack_subrec_header(b"STRV", len(sv)) + sv
        elif self.int_value is not None:
            out += pack_subrec_header(b"INTV", 4) + pack_i32(self.int_value)
        elif self.float_value is not None:
            out += pack_subrec_header(b"FLTV", 4) + struct.pack("<f", self.float_value)
        # else: VT_None — no value subrecord

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "GMST",
            "record_id": refid_to_db_text(self.record_id),
            "str_value": self.str_value,
            "int_value": self.int_value,
            "float_value": self.float_value,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GameSetting":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id   = refid_from_db_text(d.get("record_id", ""))
        obj.str_value   = d.get("str_value")
        obj.int_value   = d.get("int_value")
        obj.float_value = d.get("float_value")
        obj.flags       = d.get("flags", 0)
        return obj
