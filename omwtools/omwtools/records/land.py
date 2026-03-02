"""LAND — Landscape (terrain) record.

LAND records are identified by grid coordinates (X, Y) rather than a string
RefId.  The dense terrain data is stored as hex-encoded blobs in the JSON
representation to avoid exploding the schema with per-vertex arrays.

Subrecords:
  INTV  → grid coordinates (int32 X + int32 Y)
  DATA  → flags (int32): which sub-blobs are present
  VNML  → vertex normals   (65×65×3 bytes = 12675 bytes)
  VHGT  → vertex heights   (4+65×65×1+3 pad = 4232 bytes)
  WNAM  → world map heights (9×9 bytes = 81 bytes)
  VCLR  → vertex colors    (65×65×3 bytes = 12675 bytes, optional)
  VTEX  → texture indices  (16×16 = 256 int16s = 512 bytes, optional)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from omwtools.io.codec import pack_subrec_header, unpack_i32
from omwtools.records.base import BaseRecord, RawRecord


@dataclass
class Land(BaseRecord):
    """LAND record — landscape terrain tile."""

    REC_TYPE = b"LAND"

    flags: int = 0
    unknown: int = 0
    grid_x: int = 0
    grid_y: int = 0
    data_flags: int = 0
    # Dense blobs stored as raw bytes for fidelity
    vnml: Optional[bytes] = None   # vertex normals
    vhgt: Optional[bytes] = None   # vertex heights
    wnam: Optional[bytes] = None   # world map heights
    vclr: Optional[bytes] = None   # vertex colours
    vtex: Optional[bytes] = None   # texture indices

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Land":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        intv = raw.get_subrecord(b"INTV")
        if intv and len(intv.data) >= 8:
            obj.grid_x, obj.grid_y = struct.unpack_from("<ii", intv.data)

        data_sub = raw.get_subrecord(b"DATA")
        if data_sub and len(data_sub.data) >= 4:
            obj.data_flags = unpack_i32(data_sub.data)

        for tag, attr in (
            (b"VNML", "vnml"),
            (b"VHGT", "vhgt"),
            (b"WNAM", "wnam"),
            (b"VCLR", "vclr"),
            (b"VTEX", "vtex"),
        ):
            sub = raw.get_subrecord(tag)
            if sub:
                setattr(obj, attr, sub.data)

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        out += pack_subrec_header(b"INTV", 8)
        out += struct.pack("<ii", self.grid_x, self.grid_y)
        out += pack_subrec_header(b"DATA", 4)
        out += struct.pack("<i", self.data_flags)

        for tag, attr in (
            (b"VNML", "vnml"),
            (b"VHGT", "vhgt"),
            (b"WNAM", "wnam"),
            (b"VCLR", "vclr"),
            (b"VTEX", "vtex"),
        ):
            blob = getattr(self, attr)
            if blob is not None:
                out += pack_subrec_header(tag, len(blob)) + blob

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "LAND",
            "record_id": f"Esm3ExteriorCell:{self.grid_x}:{self.grid_y}",
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "data_flags": self.data_flags,
            "vnml_hex": self.vnml.hex() if self.vnml else None,
            "vhgt_hex": self.vhgt.hex() if self.vhgt else None,
            "wnam_hex": self.wnam.hex() if self.wnam else None,
            "vclr_hex": self.vclr.hex() if self.vclr else None,
            "vtex_hex": self.vtex.hex() if self.vtex else None,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Land":
        obj = cls()
        obj.grid_x     = d.get("grid_x", 0)
        obj.grid_y     = d.get("grid_y", 0)
        obj.data_flags = d.get("data_flags", 0)
        obj.vnml = bytes.fromhex(d["vnml_hex"]) if d.get("vnml_hex") else None
        obj.vhgt = bytes.fromhex(d["vhgt_hex"]) if d.get("vhgt_hex") else None
        obj.wnam = bytes.fromhex(d["wnam_hex"]) if d.get("wnam_hex") else None
        obj.vclr = bytes.fromhex(d["vclr_hex"]) if d.get("vclr_hex") else None
        obj.vtex = bytes.fromhex(d["vtex_hex"]) if d.get("vtex_hex") else None
        obj.flags = d.get("flags", 0)
        return obj
