"""Import records from JSON into SQLite.

Usage:
    from omwtools.json_io.import_ import import_records_from_json
    import_records_from_json(conn, json_str, mod_id=1)
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from omwtools.records import RECORD_REGISTRY
from omwtools.records.base import BaseRecord
from omwtools.db.store import ModStore


def import_records_from_json(
    conn: sqlite3.Connection,
    json_str: str,
    mod_id: int,
) -> int:
    """Import records from a JSON string into the database.

    Expects a JSON array of record dicts (as produced by export_records_to_json).
    Records are upserted — existing records with the same (mod_id, rec_type, record_id_text)
    are updated.

    Returns the number of records imported.
    """
    records: list[dict[str, Any]] = json.loads(json_str)
    store = ModStore(conn)
    count = 0

    for sort_order, d in enumerate(records):
        rec_type_str = d.get("rec_type", "")
        if not rec_type_str:
            continue

        rec_type = rec_type_str.encode("ascii")[:4]
        cls = RECORD_REGISTRY.get(rec_type)

        if cls is not None:
            try:
                record = cls.from_dict(d)
                record.flags = d.get("flags", 0)
                store._insert_record(mod_id, record, d.get("_sort_order", sort_order))
                count += 1
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to import %s record: %s", rec_type_str, e
                )

    conn.commit()
    return count
