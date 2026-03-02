"""Unit tests: NPC encode → decode round-trip."""

import struct
import pytest
from omwtools.records.base import RawRecord, RawSubrecord
from omwtools.records.npc_ import NPC, NPDTFull, NPDTAutocalc, ContItem, AIData
from omwtools.io.refid import StringRefId, EmptyRefId
from omwtools.io.codec import pack_subrec_header, SUBREC_HEADER_SIZE, unpack_subrec_header


def _parse_subrecords(data: bytes) -> list[RawSubrecord]:
    subs = []
    pos = 0
    while pos + SUBREC_HEADER_SIZE <= len(data):
        sub_type, size = unpack_subrec_header(data, pos)
        pos += SUBREC_HEADER_SIZE
        subs.append(RawSubrecord(sub_type, data[pos: pos + size]))
        pos += size
    return subs


def _make_raw(npc: NPC, format_version: int) -> RawRecord:
    encoded = npc.encode_subrecords(format_version)
    subs = _parse_subrecords(encoded)
    return RawRecord(b"NPC_", npc.flags, npc.unknown, encoded, subs)


class TestNPCRoundTrip:
    def test_minimal_autocalc(self):
        npc = NPC(
            record_id=StringRefId("test_npc"),
            name="Test NPC",
            race=StringRefId("breton"),
            class_id=StringRefId("mage"),
            npc_flags=0x0011,  # autocalc + female
            npdt_autocalc=NPDTAutocalc(level=5, gold=100),
        )
        raw = _make_raw(npc, 0)
        decoded = NPC.from_raw(raw, 0)

        assert decoded.name == "Test NPC"
        assert decoded.npdt_autocalc is not None
        assert decoded.npdt_autocalc.level == 5
        assert decoded.npdt_autocalc.gold == 100
        assert decoded.npc_flags == 0x0011

    def test_full_npdt(self):
        npc = NPC(
            record_id=StringRefId("hero"),
            name="The Hero",
            npdt_full=NPDTFull(
                level=20,
                attributes=[50, 60, 40, 70, 50, 60, 55, 65],
                skills=[30] * 27,
                health=120, mana=80, fatigue=200,
                disposition=50, reputation=10, rank=3, gold=500,
            ),
        )
        raw = _make_raw(npc, 0)
        decoded = NPC.from_raw(raw, 0)

        f = decoded.npdt_full
        assert f is not None
        assert f.level == 20
        assert f.health == 120
        assert f.gold == 500
        assert f.attributes[1] == 60
        assert f.skills[0] == 30

    def test_inventory(self):
        npc = NPC(
            record_id=StringRefId("trader"),
            name="Trader",
            npdt_autocalc=NPDTAutocalc(level=1),
            inventory=[
                ContItem(3, StringRefId("bread")),
                ContItem(1, StringRefId("iron sword")),
            ],
        )
        raw = _make_raw(npc, 0)
        decoded = NPC.from_raw(raw, 0)

        assert len(decoded.inventory) == 2
        assert decoded.inventory[0].count == 3
        inv_ids = {
            item.item_id.value if isinstance(item.item_id, StringRefId) else ""
            for item in decoded.inventory
        }
        assert "bread" in inv_ids

    def test_ai_data(self):
        npc = NPC(
            record_id=StringRefId("guard"),
            name="Guard",
            npdt_autocalc=NPDTAutocalc(level=10),
            ai_data=AIData(hello=30, fight=70, flee=20, alarm=90, services=0),
        )
        raw = _make_raw(npc, 0)
        decoded = NPC.from_raw(raw, 0)

        assert decoded.ai_data is not None
        assert decoded.ai_data.hello == 30
        assert decoded.ai_data.fight == 70
        assert decoded.ai_data.alarm == 90

    def test_to_from_dict(self):
        npc = NPC(
            record_id=StringRefId("caius_cosades"),
            name="Caius Cosades",
            race=StringRefId("imperial"),
            npdt_autocalc=NPDTAutocalc(level=4, gold=50),
            npc_flags=0x0010,
        )
        d = npc.to_dict()
        assert d["rec_type"] == "NPC_"
        assert d["name"] == "Caius Cosades"

        restored = NPC.from_dict(d)
        assert restored.name == "Caius Cosades"
        assert restored.npdt_autocalc is not None
        assert restored.npdt_autocalc.gold == 50
