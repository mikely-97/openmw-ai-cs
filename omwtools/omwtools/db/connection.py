"""Database connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from omwtools.db.schema import apply_schema

DEFAULT_DB = ":memory:"


def make_db(path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    """Open (or create) a database and apply the schema.

    Parameters
    ----------
    path:
        File path for the SQLite database, or ``:memory:`` for an in-memory DB.

    Returns
    -------
    sqlite3.Connection
        An open connection with WAL mode and foreign keys enabled.
    """
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    apply_schema(conn)
    return conn


class DBConnection:
    """RAII wrapper around a sqlite3 connection.

    Use as a context manager:
        with DBConnection("my.db") as conn:
            conn.execute(...)
    """

    def __init__(self, path: str | Path = DEFAULT_DB) -> None:
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        self._conn = make_db(self.path)
        return self._conn

    def __exit__(self, *_: object) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
