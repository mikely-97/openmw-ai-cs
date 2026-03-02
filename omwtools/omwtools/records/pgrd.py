"""PGRD — Pathgrid record.

One PGRD per cell, identified by grid coordinates or cell name.

Subrecords:
  DATA  → 12 bytes: int32 grid_x + int32 grid_y + int16 granularity + int16 node_count
  NAME  → interior cell name (C-string; absent for exterior cells)
  PGRP  → node array: node_count × 16 bytes each
            (int32 x + int32 y + int32 z + uint8 autogen_flags + 3 pad)
  PGRC  → edge connection data (variable length, raw blob — complex bit-packed format)

Node array and edge data are stored as hex blobs.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from omwtools.io.codec import decode_cstring, encode_cstring, pack_subrec_header
from omwtools.records.base import BaseRecord, RawRecord

DATA_FMT = "<iiHH"
DATA_SIZE = struct.calcsize(DATA_FMT)  # 12


@dataclass
class Pathgrid(BaseRecord):
    """PGRD record — cell pathgrid."""

    REC_TYPE = b"PGRD"

    flags: int = 0
    unknown: int = 0
    grid_x: int = 0
    grid_y: int = 0
    granularity: int = 128
    node_count: int = 0
    cell_name: str = ""
    # Dense arrays stored as hex blobs
    pgrp_hex: Optional[str] = None   # node positions array
    pgrc_hex: Optional[str] = None   # edge connection data

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Pathgrid":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        data_sub = raw.get_subrecord(b"DATA")
        if data_sub and len(data_sub.data) >= DATA_SIZE:
            obj.grid_x, obj.grid_y, obj.granularity, obj.node_count = \
                struct.unpack_from(DATA_FMT, data_sub.data)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.cell_name = decode_cstring(name_sub.data)

        pgrp = raw.get_subrecord(b"PGRP")
        if pgrp:
            obj.pgrp_hex = pgrp.data.hex()

        pgrc = raw.get_subrecord(b"PGRC")
        if pgrc:
            obj.pgrc_hex = pgrc.data.hex()

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        out += pack_subrec_header(b"DATA", DATA_SIZE)
        out += struct.pack(DATA_FMT,
                           self.grid_x, self.grid_y,
                           self.granularity, self.node_count)

        if self.cell_name:
            d = encode_cstring(self.cell_name)
            out += pack_subrec_header(b"NAME", len(d)) + d

        if self.pgrp_hex:
            blob = bytes.fromhex(self.pgrp_hex)
            out += pack_subrec_header(b"PGRP", len(blob)) + blob

        if self.pgrc_hex:
            blob = bytes.fromhex(self.pgrc_hex)
            out += pack_subrec_header(b"PGRC", len(blob)) + blob

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "PGRD",
            "record_id": self.cell_name or f"Esm3ExteriorCell:{self.grid_x}:{self.grid_y}",
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "granularity": self.granularity,
            "node_count": self.node_count,
            "cell_name": self.cell_name,
            "pgrp_hex": self.pgrp_hex,
            "pgrc_hex": self.pgrc_hex,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Pathgrid":
        obj = cls()
        obj.grid_x      = d.get("grid_x", 0)
        obj.grid_y      = d.get("grid_y", 0)
        obj.granularity = d.get("granularity", 128)
        obj.node_count  = d.get("node_count", 0)
        obj.cell_name   = d.get("cell_name", "")
        obj.pgrp_hex    = d.get("pgrp_hex")
        obj.pgrc_hex    = d.get("pgrc_hex")
        obj.flags       = d.get("flags", 0)
        return obj
