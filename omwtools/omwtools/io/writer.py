"""ESMWriter — writes ESM3-format binary files.

Accepted output extensions: .esm, .esp, .omwgame, .omwaddon
All four use the identical binary ESM3 format.

Usage:
    with ESMWriter("output.omwaddon", format_version=1) as writer:
        writer.write_record(tes3_header_record)
        for record in records:
            writer.write_record(record)
"""

from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import BinaryIO, Optional

from omwtools.io.codec import (
    RECORD_HEADER_SIZE,
    pack_record_header,
    pack_subrec_header,
)

CURRENT_CONTENT_FORMAT_VERSION = 1  # components/esm3/formatversion.hpp


class ESMWriter:
    """Writes an OpenMW ESM3-format binary file.

    Parameters
    ----------
    path:
        Output file path.  Extension may be .esm/.esp/.omwgame/.omwaddon.
    format_version:
        The FORM format_version to embed.  Default ``1`` (CurrentContentFormatVersion).
        Use ``0`` for legacy TES3/Morrowind compatibility.
    """

    def __init__(
        self,
        path: str | Path,
        format_version: int = CURRENT_CONTENT_FORMAT_VERSION,
    ) -> None:
        self.path = Path(path)
        self.format_version = format_version
        self._fh: Optional[BinaryIO] = None

    # ------------------------------------------------------------------ #
    # Context-manager support
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "ESMWriter":
        self._fh = open(self.path, "wb")
        return self

    def __exit__(self, *_: object) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def write_record(self, rec_type: bytes, subrecords_data: bytes,
                     unknown: int = 0, flags: int = 0) -> None:
        """Write one record to the output file.

        Parameters
        ----------
        rec_type:
            4-byte record type tag.
        subrecords_data:
            The already-encoded subrecord bytes (concatenated subrecord
            headers + data).
        unknown:
            The 'unknown' field in the record header (preserve from source).
        flags:
            Record flags.
        """
        assert self._fh is not None
        header = pack_record_header(rec_type, len(subrecords_data), unknown, flags)
        self._fh.write(header)
        self._fh.write(subrecords_data)

    # ------------------------------------------------------------------ #
    # Subrecord building helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def make_subrecord(sub_type: bytes, data: bytes) -> bytes:
        """Build a subrecord: 8-byte header + data bytes."""
        return pack_subrec_header(sub_type, len(data)) + data

    @staticmethod
    def make_string_subrecord(sub_type: bytes, value: str,
                               encoding: str = "cp1252") -> bytes:
        """Build a NUL-terminated string subrecord."""
        raw = value.encode(encoding, errors="replace") + b"\x00"
        return ESMWriter.make_subrecord(sub_type, raw)

    @staticmethod
    def make_u32_subrecord(sub_type: bytes, value: int) -> bytes:
        return ESMWriter.make_subrecord(sub_type, struct.pack("<I", value))

    @staticmethod
    def make_i32_subrecord(sub_type: bytes, value: int) -> bytes:
        return ESMWriter.make_subrecord(sub_type, struct.pack("<i", value))

    @staticmethod
    def make_f32_subrecord(sub_type: bytes, value: float) -> bytes:
        return ESMWriter.make_subrecord(sub_type, struct.pack("<f", value))

    # ------------------------------------------------------------------ #
    # Subrecord buffer accumulator
    # ------------------------------------------------------------------ #

    def new_buffer(self) -> "SubrecordBuffer":
        """Return a fresh SubrecordBuffer for building subrecords."""
        return SubrecordBuffer(self.format_version)


class SubrecordBuffer:
    """Accumulates subrecord bytes and supports writing them as a record.

    Convenience class for building the subrecord portion of a record.
    """

    def __init__(self, format_version: int) -> None:
        self.format_version = format_version
        self._buf = io.BytesIO()

    def add(self, sub_type: bytes, data: bytes) -> None:
        """Append one subrecord (header + data) to the buffer."""
        self._buf.write(pack_subrec_header(sub_type, len(data)))
        self._buf.write(data)

    def add_string(self, sub_type: bytes, value: str,
                   encoding: str = "cp1252") -> None:
        """Append a NUL-terminated string subrecord."""
        raw = value.encode(encoding, errors="replace") + b"\x00"
        self.add(sub_type, raw)

    def add_u8(self, sub_type: bytes, value: int) -> None:
        self.add(sub_type, struct.pack("<B", value))

    def add_u16(self, sub_type: bytes, value: int) -> None:
        self.add(sub_type, struct.pack("<H", value))

    def add_u32(self, sub_type: bytes, value: int) -> None:
        self.add(sub_type, struct.pack("<I", value))

    def add_i32(self, sub_type: bytes, value: int) -> None:
        self.add(sub_type, struct.pack("<i", value))

    def add_f32(self, sub_type: bytes, value: float) -> None:
        self.add(sub_type, struct.pack("<f", value))

    def add_f64(self, sub_type: bytes, value: float) -> None:
        self.add(sub_type, struct.pack("<d", value))

    def get_bytes(self) -> bytes:
        return self._buf.getvalue()

    def __len__(self) -> int:
        return self._buf.tell()
