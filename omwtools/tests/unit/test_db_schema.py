"""Unit tests: make_db() creates the expected tables."""

import sqlite3
import pytest
from omwtools.db.connection import make_db


EXPECTED_TABLES = {
    "schema_migrations",
    "mods",
    "master_files",
    "records",
    "npcs",
    "npc_inventory",
    "npc_spells",
    "npc_ai_packages",
    "npc_transport",
    "cells",
    "cell_refs",
    "scripts",
    "lua_script_cfgs",
    "lua_script_entries",
    "omwscripts_files",
    "omwscripts_entries",
    "typed_records",
    "dialogue_infos",
}


def test_make_db_creates_tables():
    conn = make_db(":memory:")
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    tables = {r[0] for r in rows}
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables: {missing}"
    conn.close()


def test_schema_version_recorded():
    conn = make_db(":memory:")
    row = conn.execute("SELECT version FROM schema_migrations").fetchone()
    assert row is not None
    assert row[0] == 4
    conn.close()


def test_foreign_keys_enabled():
    conn = make_db(":memory:")
    row = conn.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1
    conn.close()
