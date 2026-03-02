"""Integration test: export → JSON → import roundtrip for Phase 2 record types.

Builds records directly, inserts into an in-memory DB, exports to JSON,
re-imports into a fresh DB, then verifies that the reimported data matches.
"""

import json

import pytest

from omwtools.db.connection import make_db
from omwtools.db.store import ModStore
from omwtools.json_io.export_ import export_records_to_json
from omwtools.json_io.import_ import import_records_from_json
from omwtools.io.refid import StringRefId

from omwtools.records.weap import Weapon
from omwtools.records.spel import Spell
from omwtools.records._effects import EffectEntry
from omwtools.records.glob import GlobalVariable, GameSetting
from omwtools.records.levc import LevelledCreature, LevelledEntry
from omwtools.records.regn import Region, WeatherChances, SoundEntry
from omwtools.records.dial import Dialogue, DialogueInfo
from omwtools.records.skil import Skill, MagicEffect


# ------------------------------------------------------------------ helpers

def _make_store() -> tuple:
    """Return (conn, store, mod_id) with a fresh in-memory DB."""
    conn = make_db(":memory:")
    store = ModStore(conn)
    mod_id = conn.execute(
        "INSERT INTO mods (filename, file_type, format_version) VALUES (?,?,?)",
        ("test.esp", 1, 0),
    ).lastrowid
    conn.commit()
    return conn, store, mod_id


def _roundtrip(records_in):
    """Insert records, export JSON, re-import, return exported dicts."""
    conn1, store1, mod_id1 = _make_store()
    for i, rec in enumerate(records_in):
        store1._insert_record(mod_id1, rec, i)
    conn1.commit()

    json_str = export_records_to_json(conn1, mod_id=mod_id1)
    exported = json.loads(json_str)

    conn2 = make_db(":memory:")
    mod_id2 = conn2.execute(
        "INSERT INTO mods (filename, file_type, format_version) VALUES (?,?,?)",
        ("test.esp", 1, 0),
    ).lastrowid
    conn2.commit()
    import_records_from_json(conn2, json_str, mod_id2)

    json_str2 = export_records_to_json(conn2, mod_id=mod_id2)
    reimported = json.loads(json_str2)
    return exported, reimported


# ------------------------------------------------------------------ WEAP

def test_weapon_roundtrip():
    w = Weapon(
        record_id=StringRefId("iron longsword"),
        name="Iron Longsword",
        mesh="m\\w_longsword.nif",
        weight=10.0,
        value=100,
        weap_type=3,
        health=500,
        speed=1.2,
        reach=1.0,
        enchant_pts=0,
        chop_min=1, chop_max=10,
        slash_min=2, slash_max=20,
        thrust_min=3, thrust_max=15,
        weap_flags=0,
    )
    exported, reimported = _roundtrip([w])

    assert len(exported) == 1
    assert len(reimported) == 1
    d1, d2 = exported[0], reimported[0]
    assert d1["rec_type"] == "WEAP"
    assert d1["name"] == "Iron Longsword"
    assert d1["weight"] == pytest.approx(10.0)
    assert d1["weap_type"] == 3
    assert d1["health"] == 500
    assert d1["slash_min"] == 2
    assert d2 == {k: v for k, v in d1.items() if not k.startswith("_")} | {
        k: v for k, v in d2.items() if k.startswith("_")
    }


# ------------------------------------------------------------------ SPEL

def test_spell_roundtrip():
    effects = [
        EffectEntry(effect_id=17, skill=-1, attribute=-1,
                    range=0, area=0, duration=10, mmin=5, mmax=5),
    ]
    s = Spell(
        record_id=StringRefId("test spell"),
        name="Test Spell",
        spell_type=0,
        cost=10,
        spell_flags=0,
        effects=effects,
    )
    exported, reimported = _roundtrip([s])

    d1, d2 = exported[0], reimported[0]
    assert d1["rec_type"] == "SPEL"
    assert d1["name"] == "Test Spell"
    assert len(d1["effects"]) == 1
    assert d1["effects"][0]["effect_id"] == 17
    assert d1["effects"][0]["duration"] == 10
    assert d2["effects"] == d1["effects"]


# ------------------------------------------------------------------ GLOB / GMST

def test_glob_roundtrip():
    g = GlobalVariable(
        record_id=StringRefId("testvar"),
        var_type="f",
        value=3.14,
    )
    exported, reimported = _roundtrip([g])
    d1, d2 = exported[0], reimported[0]
    assert d1["rec_type"] == "GLOB"
    assert d1["var_type"] == "f"
    assert d1["value"] == pytest.approx(3.14)
    assert d2["value"] == pytest.approx(d1["value"])


def test_gmst_roundtrip():
    gs = GameSetting(
        record_id=StringRefId("sPlayerName"),
        str_value="Hero",
    )
    exported, reimported = _roundtrip([gs])
    d1 = exported[0]
    assert d1["rec_type"] == "GMST"
    assert d1["str_value"] == "Hero"
    assert reimported[0]["str_value"] == "Hero"


# ------------------------------------------------------------------ LEVC

def test_levelled_creature_roundtrip():
    lc = LevelledCreature(
        record_id=StringRefId("lev_netch"),
        lev_flags=1,
        chance_none=20,
        entries=[
            LevelledEntry(StringRefId("netch_betty"), 5),
            LevelledEntry(StringRefId("netch_bull"), 10),
        ],
    )
    exported, reimported = _roundtrip([lc])
    d1, d2 = exported[0], reimported[0]
    assert d1["rec_type"] == "LEVC"
    assert len(d1["entries"]) == 2
    assert d1["entries"][0]["item"] == "netch_betty"
    assert d1["entries"][1]["level"] == 10
    assert d2["entries"] == d1["entries"]


# ------------------------------------------------------------------ REGN

def test_region_roundtrip():
    r = Region(
        record_id=StringRefId("ashlands"),
        name="Ashlands",
        weather=WeatherChances(ash=50, blight=10),
        map_color=0xFF4400,
        sounds=[SoundEntry(StringRefId("ashland ambient"), 80)],
    )
    exported, reimported = _roundtrip([r])
    d1, d2 = exported[0], reimported[0]
    assert d1["rec_type"] == "REGN"
    assert d1["weather"]["ash"] == 50
    assert d1["sounds"][0]["chance"] == 80
    assert d2["weather"] == d1["weather"]


# ------------------------------------------------------------------ DIAL + INFO

def test_dialogue_and_info_roundtrip():
    dial = Dialogue(topic="topic greeting", dial_type=0)
    info = DialogueInfo(
        record_id="00000001",
        prev_id="",
        next_id="",
        response="Hello there.",
    )
    # Insert DIAL first so _current_dial_topic is set
    conn1, store1, mod_id1 = _make_store()
    store1._insert_record(mod_id1, dial, 0)
    store1._insert_record(mod_id1, info, 1)
    conn1.commit()

    json_str = export_records_to_json(conn1, mod_id=mod_id1)
    dicts = json.loads(json_str)

    dial_d = next(d for d in dicts if d["rec_type"] == "DIAL")
    info_d = next(d for d in dicts if d["rec_type"] == "INFO")
    assert dial_d["topic"] == "topic greeting"
    assert info_d["response"] == "Hello there."

    # Reimport
    conn2 = make_db(":memory:")
    mod_id2 = conn2.execute(
        "INSERT INTO mods (filename, file_type, format_version) VALUES (?,?,?)",
        ("test.esp", 1, 0),
    ).lastrowid
    conn2.commit()
    count = import_records_from_json(conn2, json_str, mod_id2)
    assert count == 2


# ------------------------------------------------------------------ SKIL / MGEF + validate

def test_validate_missing_skil_mgef():
    """Validate reports missing SKIL and MGEF when DB is empty."""
    from omwtools.cli.cmd_validate import validate_mod
    conn = make_db(":memory:")
    result = validate_mod(conn)
    assert result["status"] == "warnings"
    assert result["skil_defined"] == 0
    assert result["mgef_defined"] == 0
    missing_types = {i["type"] for i in result["issues"]}
    assert "missing_skil" in missing_types
    assert "missing_mgef" in missing_types


def test_validate_with_skil_and_mgef():
    """Validate passes when all SKIL and MGEF are present."""
    from omwtools.cli.cmd_validate import validate_mod, _MGEF_COUNT, _SKIL_COUNT

    conn, store, mod_id = _make_store()
    for idx in range(_SKIL_COUNT):
        store._insert_record(mod_id, Skill(skill_index=idx), idx)
    for idx in range(_MGEF_COUNT):
        store._insert_record(mod_id, MagicEffect(effect_index=idx), _SKIL_COUNT + idx)
    conn.commit()

    result = validate_mod(conn, mod_id=mod_id)
    assert result["status"] == "ok"
    assert result["skil_defined"] == _SKIL_COUNT
    assert result["mgef_defined"] == _MGEF_COUNT
    assert result["issues"] == []
