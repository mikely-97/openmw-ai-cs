"""SSCR — Startup Script record.

Startup scripts run once at game start.  The record contains only:
  NAME  → script RefId (the script to execute)

The record_id_text in the DB is the script RefId string.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import pack_subrec_header
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord


@dataclass
class StartupScript(BaseRecord):
    """SSCR record — startup script."""

    REC_TYPE = b"SSCR"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "StartupScript":
        obj = cls(flags=raw.flags, unknown=raw.unknown)
        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.record_id = decode_refid_from_subrecord(name_sub.data, format_version)
        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        data = encode_refid_to_subrecord(self.record_id, format_version)
        out = pack_subrec_header(b"NAME", len(data)) + data
        out += pack_subrec_header(b"DATA", 1) + b"\x00"
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "SSCR",
            "record_id": refid_to_db_text(self.record_id),
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StartupScript":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id = refid_from_db_text(d.get("record_id", ""))
        obj.flags     = d.get("flags", 0)
        return obj
