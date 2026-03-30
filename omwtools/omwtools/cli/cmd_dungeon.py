# omwtools/omwtools/cli/cmd_dungeon.py
import importlib.util
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path


def cmd_dungeon(args) -> None:
    if args.dungeon_command == "generate":
        _cmd_generate(args)


def _cmd_generate(args) -> None:
    game_id = args.game
    dungeon_type = args.dungeon_type
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_root = Path(__file__).parents[3]
    game_dir = repo_root / "games" / game_id
    if not game_dir.exists():
        print(f"Error: game directory not found: {game_dir}", file=sys.stderr)
        sys.exit(1)

    registry = _load_registry(game_dir)
    if dungeon_type not in registry["DUNGEON_TYPES"]:
        available = list(registry["DUNGEON_TYPES"].keys())
        print(f"Error: unknown type '{dungeon_type}'. Available: {available}", file=sys.stderr)
        sys.exit(1)

    spec = registry["DUNGEON_TYPES"][dungeon_type]
    kit_or_tileset = registry["TILESETS"][spec.tileset]

    if args.count is not None:
        spec = replace(spec, pool_size=args.count)

    start_seed = args.seed

    from omwtools.dungeons.lua_config import generate_lua_config
    from omwtools.dungeons.room_kit import RoomKit

    if isinstance(kit_or_tileset, RoomKit):
        from omwtools.dungeons.pool_builder import build_pool_roomkit
        corridor_tiles = registry.get("CORRIDOR_TILES", {}).get(spec.tileset)
        if corridor_tiles is None:
            print(f"Error: no CORRIDOR_TILES entry for tileset '{spec.tileset}'",
                  file=sys.stderr)
            sys.exit(1)
        records, layouts, cell_ids = build_pool_roomkit(
            spec, kit_or_tileset, corridor_tiles, start_seed=start_seed
        )
    else:
        from omwtools.dungeons.pool_builder import build_pool
        records, layouts, cell_ids = build_pool(
            spec, kit_or_tileset, start_seed=start_seed
        )

    # Write JSON records file
    out_json = output_dir / f"{spec.game_prefix}_{dungeon_type}.json"
    out_json.write_text(json.dumps(records, indent=2))
    print(f"Written {len(records)} records to {out_json}")

    # Write Lua config
    lua_out_dir = game_dir / "scripts" / game_id
    lua_out_dir.mkdir(parents=True, exist_ok=True)
    lua_out = lua_out_dir / f"dungeon_config_{dungeon_type}.lua"
    lua_str = generate_lua_config(dungeon_type, spec, layouts, kit_or_tileset, cell_ids)
    lua_out.write_text(lua_str)
    print(f"Written Lua config to {lua_out}")

    # Deploy tile meshes (unless --no-deploy)
    if not getattr(args, "no_deploy", False):
        from omwtools.dungeons.deployer import deploy_tiles
        tileset_name = kit_or_tileset.name
        copied = deploy_tiles(tileset_name, game_dir)
        if copied:
            print(f"Deployed {len(copied)} tile meshes to {game_dir}/meshes/omwdg/")
        else:
            print("Tile meshes already present, skipping deploy")

    # Compile .omwaddon if --addon specified
    if getattr(args, "addon", None):
        _compile_addon(out_json, Path(args.addon), game_id)


def _compile_addon(records_json: Path, addon_path: Path, mod_name: str) -> None:
    """Import JSON records into a temp DB and write as .omwaddon."""
    from omwtools.db.connection import make_db
    from omwtools.json_io.import_ import import_records_from_json
    from omwtools.cli.cmd_write import write_mod

    try:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "dungeon.db"
            conn = make_db(str(db_path))
            # Insert a mod entry (required by FK constraint)
            conn.execute(
                "INSERT INTO mods (id, filename, format_version, author, description, "
                "is_master, num_objects) VALUES (1, ?, 23, '', '', 0, 0)",
                (mod_name + ".omwaddon",)
            )
            conn.commit()
            import_records_from_json(conn, records_json.read_text(), mod_id=1)
            write_mod(conn, mod_id=1, output_path=str(addon_path))
            conn.close()
    except Exception as e:
        print(f"Error compiling addon: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Compiled addon: {addon_path}")


def _load_registry(game_dir: Path) -> dict:
    """Load the dungeons/registry.py from a game directory.

    The registry uses relative imports (e.g. ``from .tilesets.cave import cave``),
    so we need to register the whole ``dungeons`` package into sys.modules before
    executing registry.py.
    """
    dungeons_dir = game_dir / "dungeons"

    def _load_pkg(pkg_name: str, pkg_path: Path):
        """Recursively register a package and its sub-packages."""
        if pkg_name in sys.modules:
            return sys.modules[pkg_name]
        init = pkg_path / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            pkg_name, init if init.exists() else None,
            submodule_search_locations=[str(pkg_path)],
        )
        mod = importlib.util.module_from_spec(spec)
        mod.__path__ = [str(pkg_path)]
        mod.__package__ = pkg_name
        sys.modules[pkg_name] = mod
        if init.exists():
            spec.loader.exec_module(mod)
        return mod

    # Register top-level dungeons package
    _load_pkg("_omwdg_registry", dungeons_dir)

    # Pre-register all sub-packages so relative imports resolve
    for subdir in dungeons_dir.iterdir():
        if subdir.is_dir() and (subdir / "__init__.py").exists():
            sub_pkg = f"_omwdg_registry.{subdir.name}"
            _load_pkg(sub_pkg, subdir)
            # Register leaf modules inside each sub-package
            for pyfile in subdir.glob("*.py"):
                if pyfile.name == "__init__.py":
                    continue
                mod_name = f"{sub_pkg}.{pyfile.stem}"
                if mod_name not in sys.modules:
                    s = importlib.util.spec_from_file_location(mod_name, pyfile)
                    m = importlib.util.module_from_spec(s)
                    m.__package__ = sub_pkg
                    sys.modules[mod_name] = m
                    s.loader.exec_module(m)

    # Now load registry.py itself
    registry_path = dungeons_dir / "registry.py"
    reg_spec = importlib.util.spec_from_file_location("_omwdg_registry.registry", registry_path)
    reg_mod = importlib.util.module_from_spec(reg_spec)
    reg_mod.__package__ = "_omwdg_registry"
    sys.modules["_omwdg_registry.registry"] = reg_mod
    reg_spec.loader.exec_module(reg_mod)

    return {
        "TILESETS": reg_mod.TILESETS,
        "DUNGEON_TYPES": reg_mod.DUNGEON_TYPES,
        "CORRIDOR_TILES": getattr(reg_mod, "CORRIDOR_TILES", {}),
    }
