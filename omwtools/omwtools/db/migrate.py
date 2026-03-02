"""Schema migration framework for omwtools.

Migrations are ordered by version number.  When `apply_migrations()` is called
it checks which versions have already been applied (via the schema_migrations
table) and runs only the missing ones in order.

Adding a new migration:
  1. Define a function ``def migration_N(conn): ...``
  2. Add it to MIGRATIONS with key N.

The current schema (version 2) is created fresh by ``db/schema.py``.
Migrations are only needed when upgrading an existing database that was
created with an older version of the schema.
"""

from __future__ import annotations

import sqlite3
from typing import Callable

# Registry: version number → migration function
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}


def _register(version: int) -> Callable:
    def decorator(fn: Callable[[sqlite3.Connection], None]) -> Callable:
        MIGRATIONS[version] = fn
        return fn
    return decorator


# ------------------------------------------------------------------
# Migration 1 → 2 : add typed_records and dialogue_infos tables
# ------------------------------------------------------------------

@_register(2)
def migrate_v2(conn: sqlite3.Connection) -> None:
    """Add typed_records and dialogue_infos tables (schema version 2)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS typed_records (
            record_id  INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,
            name       TEXT NOT NULL DEFAULT '',
            script     TEXT NOT NULL DEFAULT '',
            data_json  TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_typed_records_name ON typed_records(name);

        CREATE TABLE IF NOT EXISTS dialogue_infos (
            record_id   INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,
            dial_topic  TEXT NOT NULL DEFAULT '',
            prev_id     TEXT NOT NULL DEFAULT '',
            next_id     TEXT NOT NULL DEFAULT '',
            data_json   TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_dial_infos_topic ON dialogue_infos(dial_topic);
    """)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def apply_migrations(conn: sqlite3.Connection) -> list[int]:
    """Apply all pending migrations in order.  Returns list of applied versions."""
    from omwtools.db.schema import SCHEMA_VERSION

    applied: set[int] = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }

    ran: list[int] = []
    for version in sorted(MIGRATIONS):
        if version not in applied:
            MIGRATIONS[version](conn)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
                (version,),
            )
            conn.commit()
            ran.append(version)

    return ran


def current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or 0 if none."""
    row = conn.execute(
        "SELECT MAX(version) FROM schema_migrations"
    ).fetchone()
    return row[0] or 0
