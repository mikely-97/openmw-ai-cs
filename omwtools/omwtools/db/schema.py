"""Full SQLite DDL for the omwtools database schema."""

SCHEMA_VERSION = 4

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version   INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Loaded mods / content files
CREATE TABLE IF NOT EXISTS mods (
    id          INTEGER PRIMARY KEY,
    filename    TEXT NOT NULL UNIQUE,
    file_type   INTEGER NOT NULL DEFAULT 1,  -- 0=game/esm, 1=addon/esp
    format_version INTEGER NOT NULL DEFAULT 0,
    author      TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    record_count INTEGER NOT NULL DEFAULT 0,
    loaded_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Master file dependencies
CREATE TABLE IF NOT EXISTS master_files (
    id          INTEGER PRIMARY KEY,
    mod_id      INTEGER NOT NULL REFERENCES mods(id) ON DELETE CASCADE,
    master_name TEXT NOT NULL,
    master_size INTEGER NOT NULL DEFAULT 0,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Universal record index
CREATE TABLE IF NOT EXISTS records (
    id              INTEGER PRIMARY KEY,
    mod_id          INTEGER NOT NULL REFERENCES mods(id) ON DELETE CASCADE,
    rec_type        TEXT NOT NULL,
    record_id_text  TEXT NOT NULL,
    flags           INTEGER NOT NULL DEFAULT 0,
    is_deleted      INTEGER NOT NULL DEFAULT 0,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    raw_blob        BLOB,
    UNIQUE(mod_id, rec_type, record_id_text)
);
CREATE INDEX IF NOT EXISTS idx_records_type ON records(rec_type);
CREATE INDEX IF NOT EXISTS idx_records_id_text ON records(record_id_text);

-- NPC records
CREATE TABLE IF NOT EXISTS npcs (
    record_id   INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,
    mesh        TEXT NOT NULL DEFAULT '',
    name        TEXT NOT NULL DEFAULT '',
    race        TEXT NOT NULL DEFAULT '',
    class_id    TEXT NOT NULL DEFAULT '',
    faction     TEXT NOT NULL DEFAULT '',
    head        TEXT NOT NULL DEFAULT '',
    hair        TEXT NOT NULL DEFAULT '',
    script      TEXT NOT NULL DEFAULT '',
    npc_flags   INTEGER NOT NULL DEFAULT 0,
    level       INTEGER NOT NULL DEFAULT 0,
    health      INTEGER NOT NULL DEFAULT 0,
    mana        INTEGER NOT NULL DEFAULT 0,
    fatigue     INTEGER NOT NULL DEFAULT 0,
    disposition INTEGER NOT NULL DEFAULT 50,
    reputation  INTEGER NOT NULL DEFAULT 0,
    rank        INTEGER NOT NULL DEFAULT 0,
    gold        INTEGER NOT NULL DEFAULT 0,
    is_autocalc INTEGER NOT NULL DEFAULT 0,
    attributes_json TEXT NOT NULL DEFAULT '[]',
    skills_json     TEXT NOT NULL DEFAULT '[]',
    ai_hello    INTEGER NOT NULL DEFAULT 0,
    ai_fight    INTEGER NOT NULL DEFAULT 0,
    ai_flee     INTEGER NOT NULL DEFAULT 0,
    ai_alarm    INTEGER NOT NULL DEFAULT 0,
    ai_services INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS npc_inventory (
    id          INTEGER PRIMARY KEY,
    npc_id      INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    item_id     TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 1,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS npc_spells (
    id          INTEGER PRIMARY KEY,
    npc_id      INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    spell_id    TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS npc_ai_packages (
    id          INTEGER PRIMARY KEY,
    npc_id      INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    package_type TEXT NOT NULL,
    raw_hex     TEXT NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS npc_transport (
    id          INTEGER PRIMARY KEY,
    npc_id      INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    pos_x REAL, pos_y REAL, pos_z REAL,
    rot_x REAL, rot_y REAL, rot_z REAL,
    cell_name   TEXT NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Cell records
CREATE TABLE IF NOT EXISTS cells (
    record_id       INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,
    cell_name       TEXT NOT NULL DEFAULT '',
    cell_flags      INTEGER NOT NULL DEFAULT 0,
    grid_x          INTEGER NOT NULL DEFAULT 0,
    grid_y          INTEGER NOT NULL DEFAULT 0,
    region          TEXT NOT NULL DEFAULT '',
    ref_num_counter INTEGER NOT NULL DEFAULT 0,
    water_height    REAL,
    ambient         INTEGER,
    sunlight        INTEGER,
    fog             INTEGER,
    fog_density     REAL,
    map_color       INTEGER
);

CREATE TABLE IF NOT EXISTS cell_refs (
    id          INTEGER PRIMARY KEY,
    cell_id     INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    ref_num     INTEGER NOT NULL DEFAULT 0,
    object_id   TEXT NOT NULL DEFAULT '',
    scale       REAL NOT NULL DEFAULT 1.0,
    pos_x REAL NOT NULL DEFAULT 0, pos_y REAL NOT NULL DEFAULT 0, pos_z REAL NOT NULL DEFAULT 0,
    rot_x REAL NOT NULL DEFAULT 0, rot_y REAL NOT NULL DEFAULT 0, rot_z REAL NOT NULL DEFAULT 0,
    owner       TEXT NOT NULL DEFAULT '',
    owner_rank  INTEGER NOT NULL DEFAULT -1,
    owner_global TEXT NOT NULL DEFAULT '',
    soul        TEXT NOT NULL DEFAULT '',
    key_id      TEXT NOT NULL DEFAULT '',
    trap_id     TEXT NOT NULL DEFAULT '',
    enchant_charge REAL NOT NULL DEFAULT -1.0,
    charge_int  INTEGER NOT NULL DEFAULT -1,
    lock_level  REAL NOT NULL DEFAULT 0.0,
    dest_pos_x  REAL, dest_pos_y REAL, dest_pos_z REAL,
    dest_rot_x  REAL, dest_rot_y REAL, dest_rot_z REAL,
    dest_cell   TEXT NOT NULL DEFAULT '',
    is_blocked  INTEGER NOT NULL DEFAULT 0,
    is_deleted  INTEGER NOT NULL DEFAULT 0,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Script records
CREATE TABLE IF NOT EXISTS scripts (
    record_id   INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,
    script_name TEXT NOT NULL DEFAULT '',
    num_shorts  INTEGER NOT NULL DEFAULT 0,
    num_longs   INTEGER NOT NULL DEFAULT 0,
    num_floats  INTEGER NOT NULL DEFAULT 0,
    local_vars_json TEXT NOT NULL DEFAULT '[]',
    bytecode_hex    TEXT NOT NULL DEFAULT '',
    source_text     TEXT NOT NULL DEFAULT '',
    has_scdt    INTEGER NOT NULL DEFAULT 1
);

-- LUAL (Lua script configuration) records
CREATE TABLE IF NOT EXISTS lua_script_cfgs (
    record_id   INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lua_script_entries (
    id          INTEGER PRIMARY KEY,
    lual_id     INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    script_path TEXT NOT NULL,
    lua_flags   INTEGER NOT NULL DEFAULT 0,
    types_json  TEXT NOT NULL DEFAULT '[]',
    init_data_hex TEXT NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- omwscripts text-format entries (loaded separately from .omwscripts files)
CREATE TABLE IF NOT EXISTS omwscripts_files (
    id          INTEGER PRIMARY KEY,
    filename    TEXT NOT NULL UNIQUE,
    loaded_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS omwscripts_entries (
    id          INTEGER PRIMARY KEY,
    file_id     INTEGER NOT NULL REFERENCES omwscripts_files(id) ON DELETE CASCADE,
    script_path TEXT NOT NULL,
    flags       INTEGER NOT NULL DEFAULT 0,
    types_json  TEXT NOT NULL DEFAULT '[]',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Generic typed record table for Phase 2 record types
-- Stores the full decoded record as JSON alongside searchable columns.
CREATE TABLE IF NOT EXISTS typed_records (
    record_id  INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,
    name       TEXT NOT NULL DEFAULT '',
    script     TEXT NOT NULL DEFAULT '',
    data_json  TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_typed_records_name ON typed_records(name);

-- Dialogue INFO responses (linked to their parent DIAL topic)
CREATE TABLE IF NOT EXISTS dialogue_infos (
    record_id   INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,
    dial_topic  TEXT NOT NULL DEFAULT '',
    prev_id     TEXT NOT NULL DEFAULT '',
    next_id     TEXT NOT NULL DEFAULT '',
    data_json   TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_dial_infos_topic ON dialogue_infos(dial_topic);
"""


def apply_schema(conn: "sqlite3.Connection") -> None:  # type: ignore[name-defined]
    """Apply the full DDL to a fresh (or existing) database connection."""
    import sqlite3
    conn.executescript(DDL)
    # Record schema version
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
        (SCHEMA_VERSION,),
    )
    conn.commit()
