"""omw CLI entry point.

Usage examples:
  omw --db my.db load Morrowind.esm
  omw --db my.db info
  omw --db my.db query "SELECT * FROM npcs LIMIT 5"
  omw --db my.db export --rec-type NPC_ --output npcs.json
  omw --db my.db write --output out.omwaddon --mod-id 1
  omw --db my.db scripts load mymod.omwscripts
  omw --db my.db scripts dump
"""

from __future__ import annotations

import argparse
import json
import sys


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omw",
        description="OpenMW ESM/omwgame/omwaddon/omwscripts toolkit",
    )
    parser.add_argument(
        "--db", default=":memory:",
        metavar="PATH",
        help="SQLite database path (default: :memory:)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Force JSON output to stdout",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # omw load
    p_load = sub.add_parser("load", help="Load ESM/ESP/omwgame/omwaddon file(s)")
    p_load.add_argument("files", nargs="+", metavar="FILE")
    p_load.add_argument("--encoding", default="cp1252")
    p_load.add_argument("--lenient", action="store_true")

    # omw info
    p_info = sub.add_parser("info", help="Show loaded mod info")
    p_info.add_argument("--mod-id", type=int, default=None)

    # omw dump
    p_dump = sub.add_parser("dump", help="Dump records as JSON")
    p_dump.add_argument("--rec-type", default=None)
    p_dump.add_argument("--id", dest="record_id", default=None)
    p_dump.add_argument("--mod-id", type=int, default=None)
    p_dump.add_argument("--output", default=None)

    # omw export
    p_export = sub.add_parser("export", help="Export records to JSON file")
    p_export.add_argument("--output", required=True)
    p_export.add_argument("--rec-type", default=None)
    p_export.add_argument("--id", dest="record_id", default=None)
    p_export.add_argument("--mod-id", type=int, default=None)

    # omw import
    p_import = sub.add_parser("import", help="Import records from JSON file")
    p_import.add_argument("file", metavar="FILE.json")
    p_import.add_argument("--mod-id", type=int, required=True)

    # omw query
    p_query = sub.add_parser("query", help="Run raw SQL query")
    p_query.add_argument("sql", metavar="SQL")
    p_query.add_argument("--params", nargs="*", default=[])

    # omw write
    p_write = sub.add_parser("write", help="Write ESM binary output")
    p_write.add_argument("--output", required=True)
    p_write.add_argument("--mod-id", type=int, required=True)
    p_write.add_argument("--format-version", type=int, default=None,
                         help="Override output format version (default: preserve source file's version)")

    # omw validate
    p_val = sub.add_parser("validate", help="Validate loaded records")
    p_val.add_argument("--mod-id", type=int, default=None)

    # omw scripts (subcommand group)
    p_scripts = sub.add_parser("scripts", help="Work with .omwscripts files")
    scripts_sub = p_scripts.add_subparsers(dest="scripts_command", required=True)

    p_scripts_load = scripts_sub.add_parser("load", help="Load a .omwscripts file")
    p_scripts_load.add_argument("file", metavar="FILE.omwscripts")

    p_scripts_dump = scripts_sub.add_parser("dump", help="Show loaded script entries")
    p_scripts_dump.add_argument("--file-id", type=int, default=None)

    # Dungeon subcommand group
    dg = sub.add_parser("dungeon", help="Procedural dungeon tools")
    dg_sub = dg.add_subparsers(dest="dungeon_command", required=True)
    dg_gen = dg_sub.add_parser("generate", help="Generate dungeon variant pool")
    dg_gen.add_argument("--game", required=True,
        help="Game ID — resolves to games/<id>/ relative to repo root")
    dg_gen.add_argument("--type", required=True, dest="dungeon_type",
        help="Dungeon type name (must exist in game registry)")
    dg_gen.add_argument("--count", type=int, default=None,
        help="Number of variants (overrides spec pool_size)")
    dg_gen.add_argument("--seed", type=int, default=0,
        help="Starting seed (default: 0)")
    dg_gen.add_argument("--output", required=True,
        help="Output directory for JSON records file")
    dg_gen.add_argument("--addon", default=None,
        help="Path to write compiled .omwaddon (optional)")
    dg_gen.add_argument("--no-deploy", action="store_true",
        help="Skip copying tile meshes to game meshes/ dir")

    return parser


def _open_db(args: argparse.Namespace) -> "sqlite3.Connection":
    from omwtools.db.connection import make_db
    return make_db(args.db)


def _out(data: object, use_json: bool = False) -> None:
    if use_json or isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)


def _err(msg: str, exc_type: str = "Error") -> None:
    print(json.dumps({"error": msg, "type": exc_type}), file=sys.stderr)
    sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    parser = _make_parser()
    args = parser.parse_args(argv)

    try:
        conn = _open_db(args)
    except Exception as e:
        _err(str(e), type(e).__name__)
        return

    cmd = args.command

    # ------------------------------------------------------------------ #

    if cmd == "load":
        from omwtools.db.store import ModStore
        store = ModStore(conn)
        results = []
        for f in args.files:
            try:
                mid = store.load_file(f, encoding=args.encoding, lenient=args.lenient)
                results.append({"file": f, "mod_id": mid, "status": "ok"})
            except Exception as e:
                results.append({"file": f, "error": str(e), "type": type(e).__name__})
        _out(results, args.json)

    elif cmd == "info":
        from omwtools.db.store import ModStore
        store = ModStore(conn)
        if args.mod_id is not None:
            row = store.get_mod(args.mod_id)
            _out(dict(row) if row else {"error": f"mod_id {args.mod_id} not found"}, args.json)
        else:
            rows = store.list_mods()
            _out([dict(r) for r in rows], args.json)

    elif cmd in ("dump", "export"):
        from omwtools.json_io.export_ import export_records_to_json
        json_str = export_records_to_json(
            conn,
            mod_id=getattr(args, "mod_id", None),
            rec_type=getattr(args, "rec_type", None),
            record_id=getattr(args, "record_id", None),
        )
        output = getattr(args, "output", None)
        if output:
            with open(output, "w", encoding="utf-8") as fh:
                fh.write(json_str)
            print(f"Exported to {output}")
        else:
            print(json_str)

    elif cmd == "import":
        from omwtools.json_io.import_ import import_records_from_json
        with open(args.file, encoding="utf-8") as fh:
            json_str = fh.read()
        count = import_records_from_json(conn, json_str, args.mod_id)
        _out({"imported": count}, args.json)

    elif cmd == "query":
        try:
            rows = conn.execute(args.sql, args.params).fetchall()
            conn.commit()
            _out([dict(r) for r in rows], args.json)
        except Exception as e:
            _err(str(e), type(e).__name__)

    elif cmd == "write":
        from omwtools.cli.cmd_write import write_mod
        write_mod(conn, args.mod_id, args.output, args.format_version)

    elif cmd == "validate":
        from omwtools.cli.cmd_validate import validate_mod
        result = validate_mod(conn, mod_id=args.mod_id)
        _out(result, args.json)

    elif cmd == "dungeon":
        from .cmd_dungeon import cmd_dungeon
        cmd_dungeon(args)

    elif cmd == "scripts":
        sc = args.scripts_command
        if sc == "load":
            from omwtools.db.store import ModStore
            store = ModStore(conn)
            try:
                fid = store.load_omwscripts_file(args.file)
                _out({"file": args.file, "file_id": fid, "status": "ok"}, args.json)
            except Exception as e:
                _err(str(e), type(e).__name__)
        elif sc == "dump":
            from omwtools.db.store import ModStore
            import json as _json
            store = ModStore(conn)
            rows = store.get_omwscripts_entries(args.file_id)
            result = [
                {
                    "script_path": r["script_path"],
                    "flags": r["flags"],
                    "types": _json.loads(r["types_json"]),
                }
                for r in rows
            ]
            _out(result, args.json)

    conn.close()


if __name__ == "__main__":
    main()
