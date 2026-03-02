"""RefId variant type and binary codec.

OpenMW uses a tagged union for record identifiers:
  - format_version ≤ 23: plain null-terminated string
  - format_version > 23: first byte is a type tag (0–6)

Sources:
  components/esm/refid.hpp
  components/esm/stringrefid.hpp, formid.hpp, generatedrefid.hpp,
  indexrefid.hpp, esm3exteriorcellrefid.hpp
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Union

from omwtools.io.codec import (
    unpack_i32, unpack_u32, unpack_u64,
    pack_i32, pack_u32, pack_u64,
    decode_cstring,
)

# ---------------------------------------------------------------------------
# Format-version threshold
# ---------------------------------------------------------------------------

MAX_STRING_REFID_FORMAT_VERSION = 23  # components/esm3/formatversion.hpp

# ---------------------------------------------------------------------------
# RefId variant dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmptyRefId:
    """Represents a null/empty RefId."""
    pass


@dataclass(frozen=True)
class StringRefId:
    """String-based RefId (the original TES3 style)."""
    value: str


@dataclass(frozen=True)
class FormIdRefId:
    """FormId RefId: index into content file array + content file index."""
    index: int      # uint32
    content_file: int  # int32  (-1 = current file)


@dataclass(frozen=True)
class GeneratedRefId:
    """Generated (auto-counter) RefId."""
    counter: int    # uint64


@dataclass(frozen=True)
class IndexRefId:
    """Index RefId: FourCC record type + index."""
    rec_type: bytes   # 4 bytes
    index: int        # uint32


@dataclass(frozen=True)
class ESM3ExteriorCellRefId:
    """Exterior cell RefId by grid coordinates."""
    x: int  # int32
    y: int  # int32


RefId = Union[
    EmptyRefId,
    StringRefId,
    FormIdRefId,
    GeneratedRefId,
    IndexRefId,
    ESM3ExteriorCellRefId,
]

# Tag byte values for the new (>23) encoding
_TAG_EMPTY = 0
_TAG_SIZED_STRING = 1
_TAG_UNSIZED_STRING = 2
_TAG_FORM_ID = 3
_TAG_GENERATED = 4
_TAG_INDEX = 5
_TAG_ESM3_EXTERIOR_CELL = 6

# ---------------------------------------------------------------------------
# Decode
# ---------------------------------------------------------------------------

def decode_refid_from_subrecord(data: bytes, format_version: int) -> RefId:
    """Decode a RefId from the bytes of a full subrecord (after stripping the header)."""
    if format_version <= MAX_STRING_REFID_FORMAT_VERSION:
        # Old format: null-terminated string
        return StringRefId(decode_cstring(data))

    if not data:
        return EmptyRefId()

    tag = data[0]

    if tag == _TAG_EMPTY:
        return EmptyRefId()

    if tag == _TAG_SIZED_STRING:
        # 1 byte tag + 4 byte length + n bytes
        if len(data) < 5:
            return EmptyRefId()
        length = unpack_u32(data, 1)
        raw = data[5: 5 + length]
        return StringRefId(raw.decode("utf-8", errors="replace"))

    if tag == _TAG_UNSIZED_STRING:
        # 1 byte tag + remaining bytes = string
        raw = data[1:]
        return StringRefId(raw.decode("utf-8", errors="replace"))

    if tag == _TAG_FORM_ID:
        # 1 byte tag + uint32 index + int32 content_file = 9 bytes total
        idx = unpack_u32(data, 1)
        cf = unpack_i32(data, 5)
        return FormIdRefId(idx, cf)

    if tag == _TAG_GENERATED:
        # 1 byte tag + uint64 counter = 9 bytes total
        counter = unpack_u64(data, 1)
        return GeneratedRefId(counter)

    if tag == _TAG_INDEX:
        # 1 byte tag + 4-byte FourCC + uint32 index = 9 bytes total
        rec_type = data[1:5]
        idx = unpack_u32(data, 5)
        return IndexRefId(rec_type, idx)

    if tag == _TAG_ESM3_EXTERIOR_CELL:
        # 1 byte tag + int32 X + int32 Y = 9 bytes total
        x = unpack_i32(data, 1)
        y = unpack_i32(data, 5)
        return ESM3ExteriorCellRefId(x, y)

    # Unknown tag — treat as empty
    return EmptyRefId()


# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------

def encode_refid_to_subrecord(refid: RefId, format_version: int) -> bytes:
    """Encode a RefId to bytes suitable for embedding in a subrecord's data section."""
    if format_version <= MAX_STRING_REFID_FORMAT_VERSION:
        # Old format: always a null-terminated string
        if isinstance(refid, EmptyRefId):
            return b"\x00"
        if isinstance(refid, StringRefId):
            return refid.value.encode("cp1252", errors="replace") + b"\x00"
        # Non-string types downgrade gracefully to empty
        return b"\x00"

    # New typed encoding
    if isinstance(refid, EmptyRefId):
        return bytes([_TAG_EMPTY])

    if isinstance(refid, StringRefId):
        raw = refid.value.encode("utf-8")
        # Use UnsizedString (type 2) — simpler, used by default in OpenMW CS
        return bytes([_TAG_UNSIZED_STRING]) + raw

    if isinstance(refid, FormIdRefId):
        return (bytes([_TAG_FORM_ID])
                + pack_u32(refid.index)
                + pack_i32(refid.content_file))

    if isinstance(refid, GeneratedRefId):
        return bytes([_TAG_GENERATED]) + pack_u64(refid.counter)

    if isinstance(refid, IndexRefId):
        rec_type = (refid.rec_type + b"\x00\x00\x00\x00")[:4]
        return bytes([_TAG_INDEX]) + rec_type + pack_u32(refid.index)

    if isinstance(refid, ESM3ExteriorCellRefId):
        return (bytes([_TAG_ESM3_EXTERIOR_CELL])
                + pack_i32(refid.x)
                + pack_i32(refid.y))

    raise TypeError(f"Unknown RefId type: {type(refid)}")


# ---------------------------------------------------------------------------
# Canonical text forms for SQLite storage
# ---------------------------------------------------------------------------

def refid_to_db_text(refid: RefId) -> str:
    """Convert a RefId to a canonical human-readable string for storage.

    EmptyRefId (subrecord absent) stores as "".
    StringRefId("") (subrecord present but empty string) stores as ":"
    to distinguish from absent — colon is not a valid RefId character.
    """
    if isinstance(refid, EmptyRefId):
        return ""
    if isinstance(refid, StringRefId):
        if refid.value == "":
            return ":"  # sentinel: present-but-empty, distinct from EmptyRefId
        return refid.value.lower()  # case-folded for consistent lookups
    if isinstance(refid, FormIdRefId):
        return f"FormId:{refid.index:#010x}:{refid.content_file}"
    if isinstance(refid, GeneratedRefId):
        return f"Generated:{refid.counter:#018x}"
    if isinstance(refid, IndexRefId):
        rec_str = refid.rec_type.rstrip(b"\x00").decode("ascii", errors="replace")
        return f"Index:{rec_str}:{refid.index}"
    if isinstance(refid, ESM3ExteriorCellRefId):
        return f"Esm3ExteriorCell:{refid.x}:{refid.y}"
    raise TypeError(f"Unknown RefId type: {type(refid)}")


def refid_from_db_text(text: str) -> RefId:
    """Reconstruct a RefId from its canonical text form."""
    if text == "":
        return EmptyRefId()
    if text == ":":
        return StringRefId("")  # present-but-empty sentinel
    if text.startswith("FormId:"):
        parts = text[len("FormId:"):].split(":")
        return FormIdRefId(int(parts[0], 16), int(parts[1]))
    if text.startswith("Generated:"):
        return GeneratedRefId(int(text[len("Generated:"):], 16))
    if text.startswith("Index:"):
        parts = text[len("Index:"):].split(":")
        rec_type = parts[0].encode("ascii")[:4].ljust(4, b"\x00")
        return IndexRefId(rec_type, int(parts[1]))
    if text.startswith("Esm3ExteriorCell:"):
        parts = text[len("Esm3ExteriorCell:"):].split(":")
        return ESM3ExteriorCellRefId(int(parts[0]), int(parts[1]))
    # Default: string RefId
    return StringRefId(text)
