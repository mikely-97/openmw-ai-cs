"""omw write — write a mod from SQLite back to ESM binary format."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from omwtools.io.writer import ESMWriter
from omwtools.records import parse_record, RECORD_REGISTRY
from omwtools.records.base import RawRecord, RawSubrecord
from omwtools.records.unknown import UnknownRecord
from omwtools.records.tes3 import TES3Header, MasterFile, FILE_TYPE_ADDON, FILE_TYPE_GAME
from omwtools.io.codec import unpack_subrec_header, SUBREC_HEADER_SIZE


def write_mod(
    conn: sqlite3.Connection,
    mod_id: int,
    output_path: str,
    format_version: int | None = None,
) -> None:
    """Write mod_id's records from the database to an ESM binary file.

    The output extension may be .esm/.esp/.omwgame/.omwaddon — all produce
    the same binary format.

    If format_version is None (default), uses the format_version stored when
    the mod was loaded, preserving the original file format.
    """
    out = Path(output_path)

    # Build TES3 header
    mod_row = conn.execute("SELECT * FROM mods WHERE id=?", (mod_id,)).fetchone()
    if mod_row is None:
        raise ValueError(f"mod_id {mod_id} not found")

    # Default to the mod's original format_version
    if format_version is None:
        format_version = mod_row["format_version"]

    masters_rows = conn.execute(
        "SELECT * FROM master_files WHERE mod_id=? ORDER BY sort_order",
        (mod_id,),
    ).fetchall()

    record_count = conn.execute(
        "SELECT COUNT(*) FROM records WHERE mod_id=?", (mod_id,)
    ).fetchone()[0]

    header = TES3Header(
        format_version=format_version,
        file_type=mod_row["file_type"],
        author=mod_row["author"] or "",
        description=mod_row["description"] or "",
        record_count=record_count,
        masters=[
            MasterFile(r["master_name"], r["master_size"])
            for r in masters_rows
        ],
    )

    with ESMWriter(out, format_version=format_version) as writer:
        # Write TES3 header
        header_bytes = header.encode_subrecords(format_version)
        writer.write_record(
            b"TES3", header_bytes, unknown=0, flags=0
        )

        # Write all records in order
        for row in conn.execute(
            "SELECT * FROM records WHERE mod_id=? ORDER BY sort_order",
            (mod_id,),
        ):
            rt = row["rec_type"].encode("ascii")[:4]
            raw_blob = row["raw_blob"]

            if raw_blob is not None:
                # Unknown record — use raw blob
                writer.write_record(rt, raw_blob, unknown=0, flags=row["flags"])
            else:
                # Typed record — reconstruct from satellite tables
                record = _load_typed_record(conn, row, format_version)
                if record is not None:
                    encoded = record.encode_subrecords(format_version)
                    writer.write_record(rt, encoded, unknown=0, flags=row["flags"])

    print(f"Written {record_count} records to {out}")


def _load_typed_record(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    format_version: int,
) -> object | None:
    """Reconstruct a typed record from the satellite tables using the registry."""
    import logging
    from omwtools.records import RECORD_REGISTRY
    from omwtools.json_io.export_ import _export_from_satellite

    rec_type = row["rec_type"]
    rt_bytes = rec_type.encode("ascii")[:4]
    cls = RECORD_REGISTRY.get(rt_bytes)
    if cls is None:
        return None

    d = _export_from_satellite(conn, row)
    try:
        return cls.from_dict(d)
    except Exception:
        logging.getLogger(__name__).warning(
            "Failed to reconstruct %s record %r: ", rec_type, row["record_id_text"],
            exc_info=True,
        )
        return None
