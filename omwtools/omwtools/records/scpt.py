"""SCPT — Morrowind script record.

Subrecords:
  SCHD (52 bytes): char[32] script_name + int32 num_shorts + int32 num_longs +
                   int32 num_floats + int32 script_data_size + int32 local_var_size
  SCVR: local variable name list (NUL-separated)
  SCDT: compiled bytecode blob
  SCTX: source text
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import (
    decode_fixed_string,
    encode_fixed_string,
    unpack_i32,
    pack_subrec_header,
)
from omwtools.io.refid import RefId, StringRefId, refid_to_db_text
from omwtools.records.base import BaseRecord, RawRecord

SCHD_SIZE = 52


@dataclass
class Script(BaseRecord):
    """SCPT record — Morrowind script."""

    REC_TYPE = b"SCPT"

    flags: int = 0
    unknown: int = 0
    script_name: str = ""
    num_shorts: int = 0
    num_longs: int = 0
    num_floats: int = 0
    local_vars: list[str] = field(default_factory=list)
    bytecode: bytes = b""
    source_text: str = ""
    has_scdt: bool = True

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Script":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        schd = raw.get_subrecord(b"SCHD")
        if schd and len(schd.data) >= SCHD_SIZE:
            d = schd.data
            obj.script_name = decode_fixed_string(d[:32])
            obj.num_shorts  = unpack_i32(d, 32)
            obj.num_longs   = unpack_i32(d, 36)
            obj.num_floats  = unpack_i32(d, 40)
            # d[44] = script_data_size, d[48] = local_var_size (informational)

        scvr = raw.get_subrecord(b"SCVR")
        if scvr:
            # NUL-separated variable names
            raw_vars = scvr.data
            if raw_vars.endswith(b"\x00"):
                raw_vars = raw_vars[:-1]
            obj.local_vars = [
                v.decode("cp1252", errors="replace")
                for v in raw_vars.split(b"\x00")
                if v
            ]

        scdt = raw.get_subrecord(b"SCDT")
        obj.has_scdt = scdt is not None
        if scdt:
            obj.bytecode = scdt.data

        sctx = raw.get_subrecord(b"SCTX")
        if sctx:
            obj.source_text = sctx.data.decode("cp1252", errors="replace")

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        # SCHD
        schd = bytearray(SCHD_SIZE)
        schd[:32] = encode_fixed_string(self.script_name, 32)
        struct.pack_into("<i", schd, 32, self.num_shorts)
        struct.pack_into("<i", schd, 36, self.num_longs)
        struct.pack_into("<i", schd, 40, self.num_floats)
        struct.pack_into("<i", schd, 44, len(self.bytecode))
        var_size = sum(len(v.encode("cp1252")) + 1 for v in self.local_vars)
        struct.pack_into("<i", schd, 48, var_size)
        out += pack_subrec_header(b"SCHD", SCHD_SIZE)
        out += bytes(schd)

        # SCVR
        if self.local_vars:
            var_bytes = b"\x00".join(
                v.encode("cp1252", errors="replace") for v in self.local_vars
            ) + b"\x00"
            out += pack_subrec_header(b"SCVR", len(var_bytes))
            out += var_bytes

        # SCDT — only write if the original record had it
        if self.has_scdt:
            out += pack_subrec_header(b"SCDT", len(self.bytecode))
            if self.bytecode:
                out += self.bytecode

        # SCTX
        if self.source_text:
            txt = self.source_text.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"SCTX", len(txt))
            out += txt

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "SCPT",
            "script_name": self.script_name,
            "num_shorts": self.num_shorts,
            "num_longs": self.num_longs,
            "num_floats": self.num_floats,
            "local_vars": self.local_vars,
            "bytecode_hex": self.bytecode.hex(),
            "source_text": self.source_text,
            "has_scdt": self.has_scdt,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Script":
        obj = cls()
        obj.script_name = d.get("script_name", "")
        obj.num_shorts  = d.get("num_shorts", 0)
        obj.num_longs   = d.get("num_longs", 0)
        obj.num_floats  = d.get("num_floats", 0)
        obj.local_vars  = d.get("local_vars", [])
        obj.bytecode    = bytes.fromhex(d.get("bytecode_hex", ""))
        obj.source_text = d.get("source_text", "")
        obj.has_scdt    = d.get("has_scdt", True)
        obj.flags       = d.get("flags", 0)
        return obj
