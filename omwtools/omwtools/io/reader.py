"""ESMReader — reads binary ESM/ESP/omwgame/omwaddon files into RawRecord objects.

Accepted extensions: .esm, .esp, .omwgame, .omwaddon
All four use the identical binary ESM3 format; the extension is cosmetic.

Usage:
    with ESMReader("Morrowind.esm") as reader:
        header = reader.read_header()
        for raw in reader.iter_records():
            ...
"""

from __future__ import annotations

import io
import logging
import struct
from pathlib import Path
from typing import BinaryIO, Generator, Optional

from omwtools.io.codec import (
    RECORD_HEADER_SIZE,
    SUBREC_HEADER_SIZE,
    unpack_record_header,
    unpack_subrec_header,
)

log = logging.getLogger(__name__)

# Accepted binary-format extensions (case-insensitive)
BINARY_ESM_EXTENSIONS = {".esm", ".esp", ".omwgame", ".omwaddon", ".project"}

# ---------------------------------------------------------------------------
# Data structures (also defined in records/base.py — imported from there in
# practice; defined here to break the circular import in reader)
# ---------------------------------------------------------------------------

# These lightweight versions are used only during reading.
# The full dataclasses live in omwtools.records.base.


class _RawSubrecord:
    __slots__ = ("sub_type", "data")

    def __init__(self, sub_type: bytes, data: bytes) -> None:
        self.sub_type = sub_type
        self.data = data


class _RawRecord:
    __slots__ = ("rec_type", "flags", "unknown", "raw_data", "subrecords")

    def __init__(
        self,
        rec_type: bytes,
        flags: int,
        unknown: int,
        raw_data: bytes,
        subrecords: list[_RawSubrecord],
    ) -> None:
        self.rec_type = rec_type
        self.flags = flags
        self.unknown = unknown
        self.raw_data = raw_data
        self.subrecords = subrecords


# ---------------------------------------------------------------------------
# ESMReader
# ---------------------------------------------------------------------------


class ESMReader:
    """Reads an OpenMW ESM3-format file (esm/esp/omwgame/omwaddon).

    Parameters
    ----------
    path:
        Path to the file.
    encoding:
        Text encoding for legacy string subrecords.  Default ``"cp1252"``.
    lenient:
        If ``True``, log warnings and skip malformed records instead of
        raising an exception.
    """

    def __init__(
        self,
        path: str | Path,
        encoding: str = "cp1252",
        lenient: bool = False,
    ) -> None:
        self.path = Path(path)
        self.encoding = encoding
        self.lenient = lenient
        self.format_version: int = 0
        self._fh: Optional[BinaryIO] = None
        self._file_size: int = 0

    # ------------------------------------------------------------------ #
    # Context-manager support
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "ESMReader":
        ext = self.path.suffix.lower()
        if ext not in BINARY_ESM_EXTENSIONS:
            log.warning("Unexpected extension %s for binary ESM reader", ext)
        self._fh = open(self.path, "rb")
        self._fh.seek(0, 2)
        self._file_size = self._fh.tell()
        self._fh.seek(0)
        return self

    def __exit__(self, *_: object) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def read_header(self) -> "_RawRecord":
        """Read the TES3 file-header record.  Must be called before iter_records().

        Sets ``self.format_version`` from the FORM subrecord (if present).
        Returns the raw TES3 record so callers can inspect HEDR/MAST/DATA.
        """
        assert self._fh is not None, "Use ESMReader as a context manager"
        raw = self._read_next_raw_record()
        if raw is None:
            raise EOFError("Empty ESM file")
        if raw.rec_type != b"TES3":
            raise ValueError(f"Expected TES3 header, got {raw.rec_type!r}")

        # Extract format_version from FORM subrecord
        for sub in raw.subrecords:
            if sub.sub_type == b"FORM" and len(sub.data) >= 4:
                self.format_version = struct.unpack_from("<I", sub.data)[0]
                break

        return raw  # type: ignore[return-value]

    def iter_records(self) -> Generator["_RawRecord", None, None]:
        """Yield every record after the TES3 header."""
        assert self._fh is not None
        while True:
            raw = self._read_next_raw_record()
            if raw is None:
                return
            yield raw  # type: ignore[misc]

    def get_file_offset(self) -> int:
        assert self._fh is not None
        return self._fh.tell()

    def get_file_size(self) -> int:
        return self._file_size

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _read_next_raw_record(self) -> Optional["_RawRecord"]:
        """Read one record from the current file position.  Returns None at EOF."""
        assert self._fh is not None
        header_bytes = self._fh.read(RECORD_HEADER_SIZE)
        if not header_bytes:
            return None
        if len(header_bytes) < RECORD_HEADER_SIZE:
            if self.lenient:
                log.warning("Truncated record header at offset %d", self._fh.tell())
                return None
            raise EOFError("Truncated record header")

        rec_type, data_size, unknown, flags = unpack_record_header(header_bytes)

        raw_data = self._fh.read(data_size)
        if len(raw_data) < data_size:
            if self.lenient:
                log.warning(
                    "Truncated record data for %s at offset %d (expected %d, got %d)",
                    rec_type, self._fh.tell(), data_size, len(raw_data),
                )
                # Use what we have
            else:
                raise EOFError(
                    f"Truncated record data for {rec_type!r}: "
                    f"expected {data_size}, got {len(raw_data)}"
                )

        subrecords = self._parse_subrecords(raw_data)
        return _RawRecord(rec_type, flags, unknown, raw_data, subrecords)

    def _parse_subrecords(self, data: bytes) -> list["_RawSubrecord"]:
        """Parse the raw bytes of a record body into a list of subrecords."""
        result: list[_RawSubrecord] = []
        pos = 0
        n = len(data)

        while pos < n:
            if pos + SUBREC_HEADER_SIZE > n:
                if self.lenient:
                    log.warning("Truncated subrecord header at body offset %d", pos)
                    break
                raise ValueError(f"Truncated subrecord header at offset {pos}")

            sub_type, size = unpack_subrec_header(data, pos)
            pos += SUBREC_HEADER_SIZE

            end = pos + size
            if end > n:
                if self.lenient:
                    log.warning(
                        "Subrecord %s data truncated (expected %d bytes, got %d)",
                        sub_type, size, n - pos,
                    )
                    sub_data = data[pos:]
                    pos = n
                else:
                    raise ValueError(
                        f"Subrecord {sub_type!r} data truncated: "
                        f"expected {size} bytes at offset {pos}"
                    )
            else:
                sub_data = data[pos:end]
                pos = end

            result.append(_RawSubrecord(sub_type, sub_data))

        return result
