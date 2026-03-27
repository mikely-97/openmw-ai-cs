# omwtools/omwtools/dungeons/pool_builder.py
from .dungeon_spec import DungeonSpec, DungeonLayout
from .tile_spec import TileSet
from .generator import generate
from .cell_builder import build, stat_records as get_stat_records


def build_pool(
    spec: DungeonSpec,
    tileset: TileSet,
    start_seed: int = 0,
) -> tuple[list[dict], list[DungeonLayout]]:
    """
    Generate spec.pool_size CELL record dicts starting at start_seed.
    Returns (records, layouts) where records = STAT defs + CELL dicts (import order),
    and layouts carries anchor/position data for lua_config generation.
    """
    stats = get_stat_records(tileset)
    cells: list[dict] = []
    layouts: list[DungeonLayout] = []
    for i in range(spec.pool_size):
        seed = start_seed + i
        cell_id = f"{spec.game_prefix}_{spec.name}_{seed}"
        layout = generate(spec, seed)
        layouts.append(layout)
        cells.append(build(layout, tileset, cell_id))
    return stats + cells, layouts
