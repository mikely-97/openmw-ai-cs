"""SOUN, SNDG, and LTEX records.

SOUN — Sound definition:
  NAME  → record_id (RefId)
  FNAM  → audio file path (C-string)
  DATA  → sound data (3 bytes: uint8 volume + uint8 min_range + uint8 max_range)

SNDG — Sound generator (creature sounds):
  NAME  → record_id (RefId)
  DATA  → generator type (int32)
  CNAM  → creature RefId
  SNAM  → sound RefId

LTEX — Landscape texture:
  NAME  → record_id (RefId)
  INTV  → texture index (int32, the numeric land-texture ID)
  DATA  → texture path (C-string)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, pack_subrec_header, pack_i32, pack_u8, unpack_i32, unpack_u8
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord


@dataclass
class Sound(BaseRecord):
    """SOUN record — sound definition."""

    REC_TYPE = b"SOUN"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    filename: str = ""
    volume: int = 128
    min_range: int = 0
    max_range: int = 255

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Sound":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.filename = decode_cstring(fnam.data)

        data_sub = raw.get_subrecord(b"DATA")
        if data_sub and len(data_sub.data) >= 3:
            d = data_sub.data
            obj.volume    = d[0]
            obj.min_range = d[1]
            obj.max_range = d[2]

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out += pack_subrec_header(b"NAME", len(id_data)) + id_data

        if self.filename:
            fn = encode_cstring(self.filename)
            out += pack_subrec_header(b"FNAM", len(fn)) + fn

        out += pack_subrec_header(b"DATA", 3)
        out += bytes([self.volume & 0xFF, self.min_range & 0xFF, self.max_range & 0xFF])

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "SOUN",
            "record_id": refid_to_db_text(self.record_id),
            "filename": self.filename,
            "volume": self.volume,
            "min_range": self.min_range,
            "max_range": self.max_range,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Sound":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id = refid_from_db_text(d.get("record_id", ""))
        obj.filename  = d.get("filename", "")
        obj.volume    = d.get("volume", 128)
        obj.min_range = d.get("min_range", 0)
        obj.max_range = d.get("max_range", 255)
        obj.flags     = d.get("flags", 0)
        return obj


@dataclass
class SoundGenerator(BaseRecord):
    """SNDG record — creature sound generator."""

    REC_TYPE = b"SNDG"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    gen_type: int = 0   # 0=LeftFoot, 1=RightFoot, 2=SwimLeft, 3=SwimRight,
                        # 4=Moan, 5=Roar, 6=Scream, 7=Land
    creature: RefId = field(default_factory=EmptyRefId)
    sound: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "SoundGenerator":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        def get_refid(tag: bytes) -> RefId:
            sub = raw.get_subrecord(tag)
            return decode_refid_from_subrecord(sub.data, format_version) if sub else EmptyRefId()

        obj.record_id = get_refid(b"NAME")

        data_sub = raw.get_subrecord(b"DATA")
        if data_sub and len(data_sub.data) >= 4:
            obj.gen_type = unpack_i32(data_sub.data)

        obj.creature = get_refid(b"CNAM")
        obj.sound    = get_refid(b"SNAM")

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_refid(tag: bytes, ref: RefId) -> None:
            data = encode_refid_to_subrecord(ref, format_version)
            out.extend(pack_subrec_header(tag, len(data)) + data)

        add_refid(b"NAME", self.record_id)
        out += pack_subrec_header(b"DATA", 4) + pack_i32(self.gen_type)
        add_refid(b"CNAM", self.creature)
        add_refid(b"SNAM", self.sound)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "SNDG",
            "record_id": refid_to_db_text(self.record_id),
            "gen_type": self.gen_type,
            "creature": refid_to_db_text(self.creature),
            "sound": refid_to_db_text(self.sound),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SoundGenerator":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id = refid_from_db_text(d.get("record_id", ""))
        obj.gen_type  = d.get("gen_type", 0)
        obj.creature  = refid_from_db_text(d.get("creature", ""))
        obj.sound     = refid_from_db_text(d.get("sound", ""))
        obj.flags     = d.get("flags", 0)
        return obj


@dataclass
class LandTexture(BaseRecord):
    """LTEX record — landscape texture."""

    REC_TYPE = b"LTEX"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    texture_index: int = 0
    texture_path: str = ""

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "LandTexture":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)

        intv = raw.get_subrecord(b"INTV")
        if intv and len(intv.data) >= 4:
            obj.texture_index = unpack_i32(intv.data)

        data_sub = raw.get_subrecord(b"DATA")
        if data_sub:
            obj.texture_path = decode_cstring(data_sub.data)

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        id_data = encode_refid_to_subrecord(self.record_id, format_version)
        out += pack_subrec_header(b"NAME", len(id_data)) + id_data
        out += pack_subrec_header(b"INTV", 4) + pack_i32(self.texture_index)

        if self.texture_path:
            d = encode_cstring(self.texture_path)
            out += pack_subrec_header(b"DATA", len(d)) + d

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "LTEX",
            "record_id": refid_to_db_text(self.record_id),
            "texture_index": self.texture_index,
            "texture_path": self.texture_path,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LandTexture":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id     = refid_from_db_text(d.get("record_id", ""))
        obj.texture_index = d.get("texture_index", 0)
        obj.texture_path  = d.get("texture_path", "")
        obj.flags         = d.get("flags", 0)
        return obj
