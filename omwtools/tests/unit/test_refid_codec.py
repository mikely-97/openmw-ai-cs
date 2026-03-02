"""Unit tests for RefId encode/decode round-trips."""

import pytest
from omwtools.io.refid import (
    EmptyRefId, StringRefId, FormIdRefId, GeneratedRefId,
    IndexRefId, ESM3ExteriorCellRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord,
    refid_to_db_text, refid_from_db_text,
    MAX_STRING_REFID_FORMAT_VERSION,
)

OLD_FMT = MAX_STRING_REFID_FORMAT_VERSION      # 23
NEW_FMT = MAX_STRING_REFID_FORMAT_VERSION + 1  # 24


# ---------------------------------------------------------------------------
# Old format (≤23) — all RefIds are plain C strings
# ---------------------------------------------------------------------------

class TestOldFormat:
    def test_empty_old(self):
        encoded = encode_refid_to_subrecord(EmptyRefId(), OLD_FMT)
        assert encoded == b"\x00"
        decoded = decode_refid_from_subrecord(encoded, OLD_FMT)
        assert isinstance(decoded, StringRefId)
        assert decoded.value == ""

    def test_string_round_trip_old(self):
        refid = StringRefId("caius cosades")
        encoded = encode_refid_to_subrecord(refid, OLD_FMT)
        decoded = decode_refid_from_subrecord(encoded, OLD_FMT)
        assert isinstance(decoded, StringRefId)
        assert decoded.value == "caius cosades"

    def test_string_nul_terminated_old(self):
        encoded = encode_refid_to_subrecord(StringRefId("hello"), OLD_FMT)
        assert encoded.endswith(b"\x00")


# ---------------------------------------------------------------------------
# New format (>23) — typed encoding
# ---------------------------------------------------------------------------

class TestNewFormat:
    def test_empty_new(self):
        refid = EmptyRefId()
        encoded = encode_refid_to_subrecord(refid, NEW_FMT)
        assert encoded == bytes([0])
        decoded = decode_refid_from_subrecord(encoded, NEW_FMT)
        assert isinstance(decoded, EmptyRefId)

    def test_string_unsized_new(self):
        refid = StringRefId("vivec")
        encoded = encode_refid_to_subrecord(refid, NEW_FMT)
        assert encoded[0] == 2  # UnsizedString tag
        decoded = decode_refid_from_subrecord(encoded, NEW_FMT)
        assert isinstance(decoded, StringRefId)
        assert decoded.value == "vivec"

    def test_string_empty_new(self):
        refid = StringRefId("")
        encoded = encode_refid_to_subrecord(refid, NEW_FMT)
        decoded = decode_refid_from_subrecord(encoded, NEW_FMT)
        assert isinstance(decoded, StringRefId)
        assert decoded.value == ""

    def test_formid_round_trip(self):
        refid = FormIdRefId(index=0x1234, content_file=2)
        encoded = encode_refid_to_subrecord(refid, NEW_FMT)
        assert encoded[0] == 3  # FormId tag
        assert len(encoded) == 9
        decoded = decode_refid_from_subrecord(encoded, NEW_FMT)
        assert isinstance(decoded, FormIdRefId)
        assert decoded.index == 0x1234
        assert decoded.content_file == 2

    def test_generated_round_trip(self):
        refid = GeneratedRefId(counter=0xDEADBEEF_CAFEBABE)
        encoded = encode_refid_to_subrecord(refid, NEW_FMT)
        assert encoded[0] == 4  # Generated tag
        assert len(encoded) == 9
        decoded = decode_refid_from_subrecord(encoded, NEW_FMT)
        assert isinstance(decoded, GeneratedRefId)
        assert decoded.counter == 0xDEADBEEF_CAFEBABE

    def test_index_round_trip(self):
        refid = IndexRefId(rec_type=b"SKIL", index=42)
        encoded = encode_refid_to_subrecord(refid, NEW_FMT)
        assert encoded[0] == 5  # Index tag
        assert len(encoded) == 9
        decoded = decode_refid_from_subrecord(encoded, NEW_FMT)
        assert isinstance(decoded, IndexRefId)
        assert decoded.rec_type == b"SKIL"
        assert decoded.index == 42

    def test_exterior_cell_round_trip(self):
        refid = ESM3ExteriorCellRefId(x=2, y=-4)
        encoded = encode_refid_to_subrecord(refid, NEW_FMT)
        assert encoded[0] == 6  # ESM3ExteriorCell tag
        assert len(encoded) == 9
        decoded = decode_refid_from_subrecord(encoded, NEW_FMT)
        assert isinstance(decoded, ESM3ExteriorCellRefId)
        assert decoded.x == 2
        assert decoded.y == -4

    def test_negative_formid_content_file(self):
        refid = FormIdRefId(index=0, content_file=-1)
        encoded = encode_refid_to_subrecord(refid, NEW_FMT)
        decoded = decode_refid_from_subrecord(encoded, NEW_FMT)
        assert isinstance(decoded, FormIdRefId)
        assert decoded.content_file == -1


# ---------------------------------------------------------------------------
# DB text canonical forms
# ---------------------------------------------------------------------------

class TestDbText:
    def test_empty(self):
        assert refid_to_db_text(EmptyRefId()) == ""
        assert isinstance(refid_from_db_text(""), EmptyRefId)

    def test_string(self):
        text = refid_to_db_text(StringRefId("Caius Cosades"))
        assert text == "caius cosades"  # lowercase
        r = refid_from_db_text(text)
        assert isinstance(r, StringRefId)
        assert r.value == "caius cosades"

    def test_formid(self):
        r = FormIdRefId(0x1234, 2)
        text = refid_to_db_text(r)
        assert "FormId" in text
        r2 = refid_from_db_text(text)
        assert isinstance(r2, FormIdRefId)
        assert r2.index == r.index
        assert r2.content_file == r.content_file

    def test_generated(self):
        r = GeneratedRefId(0xABCDEF)
        text = refid_to_db_text(r)
        assert "Generated" in text
        r2 = refid_from_db_text(text)
        assert isinstance(r2, GeneratedRefId)
        assert r2.counter == r.counter

    def test_index(self):
        r = IndexRefId(b"SKIL", 3)
        text = refid_to_db_text(r)
        assert "Index:SKIL:3" == text
        r2 = refid_from_db_text(text)
        assert isinstance(r2, IndexRefId)
        assert r2.index == 3

    def test_exterior_cell(self):
        r = ESM3ExteriorCellRefId(2, -4)
        text = refid_to_db_text(r)
        assert "Esm3ExteriorCell:2:-4" == text
        r2 = refid_from_db_text(text)
        assert isinstance(r2, ESM3ExteriorCellRefId)
        assert r2.x == 2 and r2.y == -4
