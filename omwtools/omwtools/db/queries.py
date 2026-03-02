"""Named parameterized query helpers for common operations."""

from __future__ import annotations

import sqlite3
from typing import Optional


def get_npcs(
    conn: sqlite3.Connection,
    mod_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """Return NPC rows joined with their records row."""
    if mod_id is not None:
        return conn.execute(
            """SELECT r.*, n.*
               FROM records r JOIN npcs n ON r.id=n.record_id
               WHERE r.mod_id=? AND r.rec_type='NPC_'
               ORDER BY r.sort_order LIMIT ? OFFSET ?""",
            (mod_id, limit, offset),
        ).fetchall()
    return conn.execute(
        """SELECT r.*, n.*
           FROM records r JOIN npcs n ON r.id=n.record_id
           WHERE r.rec_type='NPC_'
           ORDER BY r.sort_order LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()


def get_cells(
    conn: sqlite3.Connection,
    mod_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[sqlite3.Row]:
    if mod_id is not None:
        return conn.execute(
            """SELECT r.*, c.*
               FROM records r JOIN cells c ON r.id=c.record_id
               WHERE r.mod_id=? AND r.rec_type='CELL'
               ORDER BY r.sort_order LIMIT ? OFFSET ?""",
            (mod_id, limit, offset),
        ).fetchall()
    return conn.execute(
        """SELECT r.*, c.*
           FROM records r JOIN cells c ON r.id=c.record_id
           WHERE r.rec_type='CELL'
           ORDER BY r.sort_order LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()


def get_scripts(
    conn: sqlite3.Connection,
    mod_id: Optional[int] = None,
) -> list[sqlite3.Row]:
    if mod_id is not None:
        return conn.execute(
            """SELECT r.*, s.*
               FROM records r JOIN scripts s ON r.id=s.record_id
               WHERE r.mod_id=? AND r.rec_type='SCPT'
               ORDER BY r.sort_order""",
            (mod_id,),
        ).fetchall()
    return conn.execute(
        """SELECT r.*, s.*
           FROM records r JOIN scripts s ON r.id=s.record_id
           WHERE r.rec_type='SCPT'
           ORDER BY r.sort_order"""
    ).fetchall()


def get_record_count(
    conn: sqlite3.Connection,
    mod_id: int,
) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM records WHERE mod_id=?", (mod_id,)
    ).fetchone()
    return row[0] if row else 0
