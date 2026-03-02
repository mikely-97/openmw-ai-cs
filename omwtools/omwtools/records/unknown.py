"""UnknownRecord — pass-through container for unrecognised record types."""

from __future__ import annotations

from typing import Any

from omwtools.records.base import BaseRecord, RawRecord


class UnknownRecord(BaseRecord):
    """Stores the raw record body verbatim; preserves roundtrip fidelity."""

    REC_TYPE = b"????"

    def __init__(self, rec_type: bytes, raw_data: bytes,
                 flags: int = 0, unknown: int = 0) -> None:
        super().__init__(flags=flags, unknown=unknown)
        self._rec_type = rec_type
        self._raw_data = raw_data

    @property
    def actual_rec_type(self) -> bytes:
        return self._rec_type

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "UnknownRecord":
        return cls(
            rec_type=raw.rec_type,
            raw_data=raw.raw_data,
            flags=raw.flags,
            unknown=raw.unknown,
        )

    def encode_subrecords(self, format_version: int) -> bytes:
        return self._raw_data

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": self._rec_type.decode("ascii", errors="replace"),
            "flags": self.flags,
            "raw_data_hex": self._raw_data.hex(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UnknownRecord":
        return cls(
            rec_type=d["rec_type"].encode("ascii")[:4],
            raw_data=bytes.fromhex(d.get("raw_data_hex", "")),
            flags=d.get("flags", 0),
        )

    def __repr__(self) -> str:
        rt = self._rec_type.decode("ascii", errors="replace")
        return f"UnknownRecord({rt!r}, {len(self._raw_data)} bytes)"
