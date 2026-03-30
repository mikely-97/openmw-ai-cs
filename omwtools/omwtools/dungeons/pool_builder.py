# omwtools/omwtools/dungeons/pool_builder.py
from .dungeon_spec import DungeonSpec, DungeonLayout
from .tile_spec import TileSet
from .generator import generate
from .cell_builder import build, stat_records


def build_pool(
    spec: DungeonSpec,
    tileset: TileSet,
    start_seed: int = 0,
) -> tuple[list[dict], list[DungeonLayout], list[str]]:
    """
    Generate spec.pool_size CELL record dicts starting at start_seed.
    Returns (records, layouts, cell_ids) where:
    - records = STAT defs + CELL dicts (import order)
    - layouts carries anchor/position data for lua_config generation
    - cell_ids are the exact IDs baked into the CELL records
    """
    stats = stat_records(tileset)
    cells: list[dict] = []
    layouts: list[DungeonLayout] = []
    cell_ids: list[str] = []
    for i in range(spec.pool_size):
        seed = start_seed + i
        cell_id = f"{spec.game_prefix}_{spec.name}_{seed}"
        cell_ids.append(cell_id)
        layout = generate(spec, seed)
        layouts.append(layout)
        cells.append(build(layout, tileset, cell_id))
    return stats + cells, layouts, cell_ids


def build_pool_roomkit(
    spec: DungeonSpec,
    kit,          # RoomKit
    corridor_tiles: TileSet,
    start_seed: int = 0,
) -> tuple[list[dict], list[DungeonLayout], list[str]]:
    """Like build_pool() but uses the room-kit builder."""
    from .room_kit import RoomKit
    from .room_builder import stat_records_roomkit, build_roomkit

    # STAT records: room variants + corridor piece + corridor tile pieces
    kit_stats = stat_records_roomkit(kit)
    tile_stats = stat_records(corridor_tiles)
    seen: set[str] = set()
    unique_stats: list[dict] = []
    for s in kit_stats + tile_stats:
        if s["record_id"] not in seen:
            seen.add(s["record_id"])
            unique_stats.append(s)

    cells: list[dict] = []
    layouts: list[DungeonLayout] = []
    cell_ids: list[str] = []
    for i in range(spec.pool_size):
        seed = start_seed + i
        cell_id = f"{spec.game_prefix}_{spec.name}_{seed}"
        cell_ids.append(cell_id)
        layout = generate(spec, seed)
        layouts.append(layout)
        cells.append(build_roomkit(layout, kit, corridor_tiles, cell_id, seed=seed))
    return unique_stats + cells, layouts, cell_ids
