"""Unit tests: parse records from hand-crafted binaries (fixture files)."""

import struct
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True, scope="session")
def generate_fixtures():
    """Generate fixture files if they don't exist."""
    import importlib.util, sys
    script = FIXTURES / "make_fixtures.py"
    spec = importlib.util.spec_from_file_location("make_fixtures", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod  # just import — it won't auto-run __main__

    # Actually generate
    files = {
        "minimal.esm": mod.make_minimal_esm(),
        "npc_test.esm": mod.make_npc_test_esm(),
        "cell_test.esm": mod.make_cell_test_esm(),
    }
    for name, data in files.items():
        path = FIXTURES / name
        if not path.exists():
            path.write_bytes(data)


class TestMinimalESM:
    def test_loads(self):
        from omwtools.io.reader import ESMReader
        path = FIXTURES / "minimal.esm"
        with ESMReader(path) as reader:
            header = reader.read_header()
            assert header.rec_type == b"TES3"
            records = list(reader.iter_records())
            assert records == []

    def test_header_fields(self):
        from omwtools.io.reader import ESMReader
        from omwtools.records.tes3 import TES3Header
        from omwtools.records.base import RawRecord, RawSubrecord
        from omwtools.io.codec import SUBREC_HEADER_SIZE, unpack_subrec_header

        path = FIXTURES / "minimal.esm"
        with ESMReader(path) as reader:
            raw_h = reader.read_header()
            # Adapt the internal _RawRecord to full RawRecord
            subs = [
                RawSubrecord(s.sub_type, s.data)
                for s in raw_h.subrecords
            ]
            raw = RawRecord(raw_h.rec_type, raw_h.flags, raw_h.unknown,
                            raw_h.raw_data, subs)
            header = TES3Header.from_raw(raw, reader.format_version)
            assert header.author == "test"
            assert header.description == "Minimal fixture"
            assert header.file_type == 1  # addon/esp


class TestNPCFixture:
    def test_loads_three_npcs(self):
        from omwtools.io.reader import ESMReader
        path = FIXTURES / "npc_test.esm"
        with ESMReader(path) as reader:
            reader.read_header()
            records = list(reader.iter_records())
        assert len(records) == 3
        for r in records:
            assert r.rec_type == b"NPC_"

    def test_npc_fields(self):
        from omwtools.io.reader import ESMReader
        from omwtools.records.npc_ import NPC
        from omwtools.records.base import RawRecord, RawSubrecord

        path = FIXTURES / "npc_test.esm"
        npcs = []
        with ESMReader(path) as reader:
            reader.read_header()
            for raw in reader.iter_records():
                subs = [RawSubrecord(s.sub_type, s.data) for s in raw.subrecords]
                full_raw = RawRecord(raw.rec_type, raw.flags, raw.unknown,
                                     raw.raw_data, subs)
                npcs.append(NPC.from_raw(full_raw, reader.format_version))

        names = {n.name for n in npcs}
        assert "Caius Cosades" in names
        assert "Fargoth" in names

        caius = next(n for n in npcs if n.name == "Caius Cosades")
        assert caius.npdt_autocalc is not None
        assert caius.npdt_autocalc.level == 4
        assert caius.npdt_autocalc.gold == 50


class TestCellFixture:
    def test_loads_one_cell(self):
        from omwtools.io.reader import ESMReader
        path = FIXTURES / "cell_test.esm"
        with ESMReader(path) as reader:
            reader.read_header()
            records = list(reader.iter_records())
        assert len(records) == 1
        assert records[0].rec_type == b"CELL"

    def test_cell_refs(self):
        from omwtools.io.reader import ESMReader
        from omwtools.records.cell import Cell
        from omwtools.records.base import RawRecord, RawSubrecord

        path = FIXTURES / "cell_test.esm"
        cells = []
        with ESMReader(path) as reader:
            reader.read_header()
            for raw in reader.iter_records():
                subs = [RawSubrecord(s.sub_type, s.data) for s in raw.subrecords]
                full_raw = RawRecord(raw.rec_type, raw.flags, raw.unknown,
                                     raw.raw_data, subs)
                cells.append(Cell.from_raw(full_raw, reader.format_version))

        assert len(cells) == 1
        cell = cells[0]
        assert cell.cell_name == "Test Cell"
        assert len(cell.refs) == 2
        assert cell.refs[0].ref_num == 1
        assert cell.refs[1].pos_z == pytest.approx(100.0, abs=1e-5)
