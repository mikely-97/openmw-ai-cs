"""Generate minimal hand-crafted ESM fixture files for testing.

Run this once to (re)generate the fixture binaries:
    python tests/fixtures/make_fixtures.py
"""

import struct
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent


def pack_subrec(tag: bytes, data: bytes) -> bytes:
    return struct.pack("<4sI", tag, len(data)) + data


def pack_record(tag: bytes, data: bytes, flags: int = 0) -> bytes:
    return struct.pack("<4sIII", tag, len(data), 0, flags) + data


def make_tes3_header(
    format_version: int,
    file_type: int,
    author: str,
    description: str,
    record_count: int,
    masters: list[tuple[str, int]] | None = None,
) -> bytes:
    """Build a TES3 header record."""
    subs = b""

    if format_version > 0:
        subs += pack_subrec(b"FORM", struct.pack("<I", format_version))

    hedr = bytearray(300)
    struct.pack_into("<f", hedr, 0, 1.3)     # esm_version
    struct.pack_into("<i", hedr, 4, file_type)
    author_b = author.encode("cp1252")[:31] + b"\x00" * (32 - min(len(author), 31))
    hedr[8:40] = author_b[:32]
    desc_b = description.encode("cp1252")[:255] + b"\x00" * (256 - min(len(description), 255))
    hedr[40:296] = desc_b[:256]
    struct.pack_into("<i", hedr, 296, record_count)
    subs += pack_subrec(b"HEDR", bytes(hedr))

    for mname, msize in (masters or []):
        subs += pack_subrec(b"MAST", mname.encode("cp1252") + b"\x00")
        subs += pack_subrec(b"DATA", struct.pack("<Q", msize))

    return pack_record(b"TES3", subs)


def make_minimal_esm() -> bytes:
    """minimal.esm — TES3 header only, legacy format 0."""
    return make_tes3_header(0, 1, "test", "Minimal fixture", 0)


def make_npc_test_esm() -> bytes:
    """npc_test.esm — TES3 header + 3 NPC records."""
    header = make_tes3_header(0, 1, "test", "NPC fixture", 3)

    def make_npc(record_id: str, name: str, level: int, gold: int) -> bytes:
        # Autocalc NPC: NAME + FNAM + NPDT(12) + FLAG
        subs = b""
        subs += pack_subrec(b"NAME", record_id.encode("cp1252") + b"\x00")
        subs += pack_subrec(b"FNAM", name.encode("cp1252") + b"\x00")
        # NPDT 12 bytes: int16 level + byte disp + byte rep + byte rank + 3pad + int32 gold
        npdt = bytearray(12)
        struct.pack_into("<h", npdt, 0, level)
        npdt[2] = 50  # disposition
        struct.pack_into("<i", npdt, 8, gold)
        subs += pack_subrec(b"NPDT", bytes(npdt))
        subs += pack_subrec(b"FLAG", struct.pack("<I", 0x0010))  # autocalc
        return pack_record(b"NPC_", subs)

    return (header
            + make_npc("caius_cosades", "Caius Cosades", 4, 50)
            + make_npc("fargoth", "Fargoth", 1, 10)
            + make_npc("vivec", "Vivec", 50, 1000))


def make_cell_test_esm() -> bytes:
    """cell_test.esm — TES3 header + 1 interior cell with 2 references."""
    header = make_tes3_header(0, 1, "test", "Cell fixture", 1)

    cell_subs = b""
    cell_subs += pack_subrec(b"NAME", b"Test Cell\x00")
    cell_subs += pack_subrec(b"DATA", struct.pack("<Iii", 0x01, 0, 0))  # interior, grid 0,0

    # Reference 1
    cell_subs += pack_subrec(b"FRMR", struct.pack("<I", 1))
    cell_subs += pack_subrec(b"NAME", b"misc_de_pot_clay_01\x00")
    pos_data = struct.pack("<ffffff", 10.0, 20.0, 0.0, 0.0, 0.0, 0.0)
    cell_subs += pack_subrec(b"DATA", pos_data)

    # Reference 2
    cell_subs += pack_subrec(b"FRMR", struct.pack("<I", 2))
    cell_subs += pack_subrec(b"NAME", b"light_de_lantern_01\x00")
    pos_data2 = struct.pack("<ffffff", -5.0, 3.0, 100.0, 0.0, 0.0, 0.0)
    cell_subs += pack_subrec(b"DATA", pos_data2)

    return header + pack_record(b"CELL", cell_subs)


if __name__ == "__main__":
    files = {
        "minimal.esm": make_minimal_esm(),
        "npc_test.esm": make_npc_test_esm(),
        "cell_test.esm": make_cell_test_esm(),
    }
    for name, data in files.items():
        path = FIXTURES / name
        path.write_bytes(data)
        print(f"Wrote {path} ({len(data)} bytes)")
