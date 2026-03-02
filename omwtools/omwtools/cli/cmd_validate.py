"""omw validate — check loaded records for consistency.

Checks performed:
  - MGEF: all 143 effect indices (0-142) are defined
  - SKIL: all 27 skill indices (0-26) are defined
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional


_MGEF_COUNT = 143   # indices 0-142
_SKIL_COUNT = 27    # indices 0-26


def validate_mod(
    conn: sqlite3.Connection,
    mod_id: Optional[int] = None,
) -> dict[str, Any]:
    """Run validation checks and return a result dict."""
    issues: list[dict[str, Any]] = []

    mod_filter = "AND r.mod_id=?" if mod_id is not None else ""
    params: list[Any] = [mod_id] if mod_id is not None else []

    # --- MGEF coverage -------------------------------------------------
    rows = conn.execute(
        f"""SELECT t.data_json FROM typed_records t
            JOIN records r ON r.id = t.record_id
            WHERE r.rec_type = 'MGEF' {mod_filter}""",
        params,
    ).fetchall()

    found_mgef: set[int] = set()
    for row in rows:
        d = json.loads(row[0])
        found_mgef.add(d.get("effect_index", -1))

    missing_mgef = sorted(set(range(_MGEF_COUNT)) - found_mgef)
    if missing_mgef:
        issues.append({
            "type": "missing_mgef",
            "message": f"{len(missing_mgef)} magic effect(s) undefined",
            "indices": missing_mgef,
        })

    # --- SKIL coverage -------------------------------------------------
    rows = conn.execute(
        f"""SELECT t.data_json FROM typed_records t
            JOIN records r ON r.id = t.record_id
            WHERE r.rec_type = 'SKIL' {mod_filter}""",
        params,
    ).fetchall()

    found_skil: set[int] = set()
    for row in rows:
        d = json.loads(row[0])
        found_skil.add(d.get("skill_index", -1))

    missing_skil = sorted(set(range(_SKIL_COUNT)) - found_skil)
    if missing_skil:
        issues.append({
            "type": "missing_skil",
            "message": f"{len(missing_skil)} skill(s) undefined",
            "indices": missing_skil,
        })

    return {
        "status": "ok" if not issues else "warnings",
        "mgef_defined": len(found_mgef),
        "skil_defined": len(found_skil),
        "issues": issues,
    }
