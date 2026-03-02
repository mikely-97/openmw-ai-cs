"""Unit tests: CELL encode → decode round-trip with references."""

import pytest
from omwtools.records.base import RawRecord, RawSubrecord
from omwtools.records.cell import Cell, CellRef, CellAmbient, CELL_INTERIOR
from omwtools.io.refid import StringRefId, EmptyRefId
from omwtools.io.codec import SUBREC_HEADER_SIZE, unpack_subrec_header


def _parse_subrecords(data: bytes) -> list[RawSubrecord]:
    subs = []
    pos = 0
    while pos + SUBREC_HEADER_SIZE <= len(data):
        sub_type, size = unpack_subrec_header(data, pos)
        pos += SUBREC_HEADER_SIZE
        subs.append(RawSubrecord(sub_type, data[pos: pos + size]))
        pos += size
    return subs


def _make_raw(cell: Cell, format_version: int) -> RawRecord:
    encoded = cell.encode_subrecords(format_version)
    subs = _parse_subrecords(encoded)
    return RawRecord(b"CELL", cell.flags, 0, encoded, subs)


class TestCellRoundTrip:
    def test_interior_cell_no_refs(self):
        cell = Cell(
            cell_name="Balmora, South Wall Cornerclub",
            cell_flags=CELL_INTERIOR,
            grid_x=0, grid_y=0,
            ambient=CellAmbient(0x404040, 0x808080, 0x202020, 0.3),
        )
        raw = _make_raw(cell, 0)
        decoded = Cell.from_raw(raw, 0)

        assert decoded.cell_name == "Balmora, South Wall Cornerclub"
        assert decoded.cell_flags == CELL_INTERIOR
        assert decoded.ambient is not None
        assert decoded.ambient.fog_density == pytest.approx(0.3, abs=1e-5)

    def test_exterior_cell(self):
        cell = Cell(
            cell_name="",
            cell_flags=0,
            grid_x=2, grid_y=-4,
            region=StringRefId("bitter coast"),
            water_height=-1.0,
        )
        raw = _make_raw(cell, 0)
        decoded = Cell.from_raw(raw, 0)

        assert decoded.grid_x == 2
        assert decoded.grid_y == -4
        assert decoded.water_height == pytest.approx(-1.0, abs=1e-5)

    def test_cell_with_refs(self):
        cell = Cell(
            cell_name="Test Room",
            cell_flags=CELL_INTERIOR,
            refs=[
                CellRef(
                    ref_num=1,
                    object_id=StringRefId("misc_de_pot_clay_01"),
                    pos_x=10.0, pos_y=20.0, pos_z=0.0,
                    rot_x=0.0, rot_y=0.0, rot_z=1.57,
                ),
                CellRef(
                    ref_num=2,
                    object_id=StringRefId("light_de_lantern_01"),
                    pos_x=-5.0, pos_y=3.0, pos_z=100.0,
                ),
                CellRef(
                    ref_num=3,
                    object_id=StringRefId("door_de_arch_01"),
                    is_deleted=True,
                ),
            ],
        )
        raw = _make_raw(cell, 0)
        decoded = Cell.from_raw(raw, 0)

        assert len(decoded.refs) == 3
        assert decoded.refs[0].ref_num == 1
        assert decoded.refs[1].pos_z == pytest.approx(100.0, abs=1e-5)
        assert decoded.refs[2].is_deleted is True

    def test_cell_to_from_dict(self):
        cell = Cell(
            cell_name="My Cell",
            cell_flags=CELL_INTERIOR,
            grid_x=0, grid_y=0,
        )
        d = cell.to_dict()
        assert d["rec_type"] == "CELL"
        assert d["cell_name"] == "My Cell"

        restored = Cell.from_dict(d)
        assert restored.cell_name == "My Cell"
        assert restored.cell_flags == CELL_INTERIOR
