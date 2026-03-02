"""TES3 file-header record parser and encoder.

TES3 subrecords (in order):
  FORM (optional) : uint32 format_version
  HEDR (required) : float32 version + int32 file_type +
                    char[32] author + char[256] description + int32 record_count
  MAST / DATA pairs: master filename (NUL-terminated) + uint64 master_size
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import (
    decode_fixed_string,
    encode_fixed_string,
    decode_cstring,
    encode_cstring,
    unpack_f32, unpack_i32, unpack_u32, unpack_u64,
    pack_f32, pack_i32, pack_u32, pack_u64,
    pack_subrec_header,
)
from omwtools.records.base import BaseRecord, RawRecord

# HEDR is always 300 bytes
HEDR_SIZE = 300
FILE_TYPE_GAME   = 0   # .esm / .omwgame
FILE_TYPE_ADDON  = 1   # .esp / .omwaddon
FILE_TYPE_SAVE   = 32  # .ess  (not handled here)


@dataclass
class MasterFile:
    filename: str
    file_size: int = 0


@dataclass
class TES3Header(BaseRecord):
    """Parsed TES3 file header record."""

    REC_TYPE = b"TES3"

    flags: int = 0
    unknown: int = 0
    format_version: int = 0       # from FORM subrecord (0 = legacy)
    esm_version: float = 1.3      # float in HEDR
    file_type: int = FILE_TYPE_ADDON
    author: str = ""
    description: str = ""
    record_count: int = 0
    masters: list[MasterFile] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "TES3Header":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        # FORM — format version
        form_sub = raw.get_subrecord(b"FORM")
        if form_sub and len(form_sub.data) >= 4:
            obj.format_version = unpack_u32(form_sub.data)

        # HEDR — required
        hedr_sub = raw.get_subrecord(b"HEDR")
        if hedr_sub and len(hedr_sub.data) >= HEDR_SIZE:
            d = hedr_sub.data
            obj.esm_version = unpack_f32(d, 0)
            obj.file_type   = unpack_i32(d, 4)
            obj.author      = decode_fixed_string(d[8:40])
            obj.description = decode_fixed_string(d[40:296])
            obj.record_count = unpack_i32(d, 296)

        # MAST / DATA pairs
        subs = raw.subrecords
        i = 0
        while i < len(subs):
            if subs[i].sub_type == b"MAST":
                name = decode_cstring(subs[i].data)
                size = 0
                if i + 1 < len(subs) and subs[i + 1].sub_type == b"DATA":
                    size_bytes = subs[i + 1].data
                    if len(size_bytes) >= 8:
                        size = unpack_u64(size_bytes)
                    i += 1
                obj.masters.append(MasterFile(name, size))
            i += 1

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        # FORM subrecord (only if format_version > 0)
        fv = self.format_version if self.format_version > 0 else format_version
        if fv > 0:
            fv_bytes = pack_u32(fv)
            out += pack_subrec_header(b"FORM", 4)
            out += fv_bytes

        # HEDR subrecord — always 300 bytes
        hedr = bytearray(HEDR_SIZE)
        struct.pack_into("<f", hedr, 0, self.esm_version)
        struct.pack_into("<i", hedr, 4, self.file_type)
        author_bytes = encode_fixed_string(self.author, 32)
        hedr[8:40] = author_bytes
        desc_bytes = encode_fixed_string(self.description, 256)
        hedr[40:296] = desc_bytes
        struct.pack_into("<i", hedr, 296, self.record_count)
        out += pack_subrec_header(b"HEDR", HEDR_SIZE)
        out += bytes(hedr)

        # MAST / DATA pairs
        for mf in self.masters:
            mast_bytes = encode_cstring(mf.filename)
            out += pack_subrec_header(b"MAST", len(mast_bytes))
            out += mast_bytes
            out += pack_subrec_header(b"DATA", 8)
            out += pack_u64(mf.file_size)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "TES3",
            "format_version": self.format_version,
            "esm_version": self.esm_version,
            "file_type": self.file_type,
            "author": self.author,
            "description": self.description,
            "record_count": self.record_count,
            "masters": [{"filename": m.filename, "file_size": m.file_size}
                        for m in self.masters],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TES3Header":
        obj = cls()
        obj.format_version = d.get("format_version", 0)
        obj.esm_version    = d.get("esm_version", 1.3)
        obj.file_type      = d.get("file_type", FILE_TYPE_ADDON)
        obj.author         = d.get("author", "")
        obj.description    = d.get("description", "")
        obj.record_count   = d.get("record_count", 0)
        obj.masters = [MasterFile(m["filename"], m.get("file_size", 0))
                       for m in d.get("masters", [])]
        return obj

    def __repr__(self) -> str:
        return (
            f"TES3Header(format_version={self.format_version}, "
            f"file_type={self.file_type}, author={self.author!r}, "
            f"masters={[m.filename for m in self.masters]})"
        )
