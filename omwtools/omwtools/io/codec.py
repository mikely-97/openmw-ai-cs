"""Low-level struct helpers, FourCC utilities, and fixed-string encode/decode."""

from __future__ import annotations

import struct
from typing import Any


# ---------------------------------------------------------------------------
# Primitive pack/unpack helpers (all little-endian)
# ---------------------------------------------------------------------------

def pack_u8(v: int) -> bytes:
    return struct.pack("<B", v)

def pack_i8(v: int) -> bytes:
    return struct.pack("<b", v)

def pack_u16(v: int) -> bytes:
    return struct.pack("<H", v)

def pack_i16(v: int) -> bytes:
    return struct.pack("<h", v)

def pack_u32(v: int) -> bytes:
    return struct.pack("<I", v)

def pack_i32(v: int) -> bytes:
    return struct.pack("<i", v)

def pack_u64(v: int) -> bytes:
    return struct.pack("<Q", v)

def pack_i64(v: int) -> bytes:
    return struct.pack("<q", v)

def pack_f32(v: float) -> bytes:
    return struct.pack("<f", v)

def pack_f64(v: float) -> bytes:
    return struct.pack("<d", v)


def unpack_u8(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<B", data, offset)[0]

def unpack_i8(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<b", data, offset)[0]

def unpack_u16(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<H", data, offset)[0]

def unpack_i16(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<h", data, offset)[0]

def unpack_u32(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<I", data, offset)[0]

def unpack_i32(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<i", data, offset)[0]

def unpack_u64(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<Q", data, offset)[0]

def unpack_i64(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<q", data, offset)[0]

def unpack_f32(data: bytes, offset: int = 0) -> float:
    return struct.unpack_from("<f", data, offset)[0]

def unpack_f64(data: bytes, offset: int = 0) -> float:
    return struct.unpack_from("<d", data, offset)[0]


# ---------------------------------------------------------------------------
# FourCC helpers
# ---------------------------------------------------------------------------

def fourcc(s: str) -> bytes:
    """Encode a 4-character string as bytes, padding with NUL if shorter."""
    encoded = s.encode("ascii")
    if len(encoded) > 4:
        raise ValueError(f"FourCC must be ≤ 4 chars, got: {s!r}")
    return encoded.ljust(4, b"\x00")


def fourcc_str(b: bytes) -> str:
    """Decode a 4-byte FourCC to a string (strip trailing NULs)."""
    return b[:4].rstrip(b"\x00").decode("ascii", errors="replace")


# ---------------------------------------------------------------------------
# Fixed-length null-terminated string helpers
# ---------------------------------------------------------------------------

def encode_fixed_string(s: str, size: int, encoding: str = "cp1252") -> bytes:
    """Encode *s* into exactly *size* bytes, null-padding or truncating."""
    raw = s.encode(encoding, errors="replace")
    if len(raw) >= size:
        raw = raw[: size - 1]
    return raw + b"\x00" * (size - len(raw))


def decode_fixed_string(data: bytes, encoding: str = "cp1252") -> str:
    """Decode a null-terminated fixed-length string."""
    nul = data.find(b"\x00")
    if nul >= 0:
        data = data[:nul]
    return data.decode(encoding, errors="replace")


def encode_cstring(s: str, encoding: str = "cp1252") -> bytes:
    """Encode *s* as a NUL-terminated C string."""
    return s.encode(encoding, errors="replace") + b"\x00"


def decode_cstring(data: bytes, encoding: str = "cp1252") -> str:
    """Decode a NUL-terminated C string from *data*."""
    nul = data.find(b"\x00")
    raw = data[:nul] if nul >= 0 else data
    return raw.decode(encoding, errors="replace")


def decode_string(data: bytes, encoding: str = "cp1252") -> str:
    """Decode bytes to string, stripping a trailing NUL if present."""
    if data.endswith(b"\x00"):
        data = data[:-1]
    return data.decode(encoding, errors="replace")


# ---------------------------------------------------------------------------
# Record / subrecord header constants
# ---------------------------------------------------------------------------

RECORD_HEADER_SIZE = 16   # type(4) + data_size(4) + unknown(4) + flags(4)
SUBREC_HEADER_SIZE = 8    # type(4) + size(4)

RECORD_HEADER_FMT = "<4sIII"  # type, data_size, unknown, flags
SUBREC_HEADER_FMT = "<4sI"    # type, size


def pack_record_header(rec_type: bytes, data_size: int, unknown: int, flags: int) -> bytes:
    return struct.pack(RECORD_HEADER_FMT, rec_type[:4], data_size, unknown, flags)


def unpack_record_header(data: bytes, offset: int = 0) -> tuple[bytes, int, int, int]:
    """Return (rec_type, data_size, unknown, flags)."""
    return struct.unpack_from(RECORD_HEADER_FMT, data, offset)


def pack_subrec_header(sub_type: bytes, size: int) -> bytes:
    return struct.pack(SUBREC_HEADER_FMT, sub_type[:4], size)


def unpack_subrec_header(data: bytes, offset: int = 0) -> tuple[bytes, int]:
    """Return (sub_type, size)."""
    return struct.unpack_from(SUBREC_HEADER_FMT, data, offset)
