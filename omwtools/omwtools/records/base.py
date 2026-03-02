"""Base record types: RawSubrecord, RawRecord, RecordFlags, BaseRecord."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntFlag
from typing import Any, ClassVar, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from omwtools.io.writer import SubrecordBuffer


# ---------------------------------------------------------------------------
# Record flags  (record header bytes 12-15)
# ---------------------------------------------------------------------------

class RecordFlags(IntFlag):
    NONE       = 0x0000
    DELETED    = 0x0020
    PERSISTENT = 0x0400
    IGNORED    = 0x1000
    BLOCKED    = 0x2000


# ---------------------------------------------------------------------------
# Raw (unparsed) subrecord and record
# ---------------------------------------------------------------------------

@dataclass
class RawSubrecord:
    """A single subrecord as read from the file — type tag + raw bytes."""
    sub_type: bytes
    data: bytes

    def __repr__(self) -> str:
        preview = self.data[:16].hex()
        return f"RawSubrecord({self.sub_type!r}, {len(self.data)} bytes, {preview}...)"


@dataclass
class RawRecord:
    """A full record as read from the file — header fields + subrecords."""
    rec_type: bytes
    flags: int
    unknown: int
    raw_data: bytes
    subrecords: list[RawSubrecord] = field(default_factory=list)

    @property
    def record_flags(self) -> RecordFlags:
        return RecordFlags(self.flags)

    @property
    def is_deleted(self) -> bool:
        return bool(self.flags & RecordFlags.DELETED)

    def get_subrecord(self, sub_type: bytes) -> Optional[RawSubrecord]:
        """Return the first subrecord of the given type, or None."""
        for sub in self.subrecords:
            if sub.sub_type == sub_type:
                return sub
        return None

    def get_subrecords(self, sub_type: bytes) -> list[RawSubrecord]:
        """Return all subrecords of the given type."""
        return [s for s in self.subrecords if s.sub_type == sub_type]

    def get_string(self, sub_type: bytes, encoding: str = "cp1252") -> Optional[str]:
        """Convenience: get the string value of the first matching subrecord."""
        sub = self.get_subrecord(sub_type)
        if sub is None:
            return None
        data = sub.data
        if data.endswith(b"\x00"):
            data = data[:-1]
        return data.decode(encoding, errors="replace")


# ---------------------------------------------------------------------------
# Abstract base record
# ---------------------------------------------------------------------------

class BaseRecord:
    """Base class for all typed record implementations.

    Subclasses must define:
      - ``REC_TYPE: ClassVar[bytes]``  — 4-byte record type tag
      - ``from_raw(cls, raw, format_version) -> Self``
      - ``encode_subrecords(format_version) -> bytes``
      - ``to_dict() -> dict``
      - ``from_dict(cls, d) -> Self``
    """

    REC_TYPE: ClassVar[bytes] = b"\x00\x00\x00\x00"

    def __init__(self, flags: int = 0, unknown: int = 0) -> None:
        self.flags = flags
        self.unknown = unknown

    @property
    def record_flags(self) -> RecordFlags:
        return RecordFlags(self.flags)

    @property
    def is_deleted(self) -> bool:
        return bool(self.flags & RecordFlags.DELETED)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "BaseRecord":
        raise NotImplementedError

    def encode_subrecords(self, format_version: int) -> bytes:
        """Encode all subrecords and return their concatenated bytes."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BaseRecord":
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}(flags={self.flags:#010x})"
