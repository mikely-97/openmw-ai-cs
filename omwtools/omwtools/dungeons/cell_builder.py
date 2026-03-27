# omwtools/omwtools/dungeons/cell_builder.py
from .dungeon_spec import DungeonLayout
from .tile_spec import TileSet, WALL_ROTATIONS

_REF_DEFAULTS = {
    "scale": 1.0,
    "is_deleted": False,
    "is_blocked": False,
    "soul": "",
    "owner": "",
    "owner_rank": -1,
    "owner_global": "",
    "key_id": "",
    "trap_id": "",
    "enchant_charge": -1.0,
    "charge_int": -1,
    "lock_level": 0.0,
    "dest_pos": None,
    "dest_rot": None,
    "dest_cell": "",
}


def stat_records(tileset: TileSet) -> list[dict]:
    """Return one STAT record dict per base tile type. Import before CELL records."""
    return [
        {"rec_type": "STAT", "record_id": tile_def.stat_id, "mesh": tile_def.mesh, "flags": 0}
        for tile_def in tileset.tiles.values()
    ]


def build(layout: DungeonLayout, tileset: TileSet, cell_id: str) -> dict:
    """
    Convert DungeonLayout (tile-grid coords) to an omwtools CELL record dict.
    Tile-grid coords are multiplied by tileset.tile_size to produce world coords.
    cell_name == cell_id for predictable teleportToCell(cell_id, ...) targeting.
    """
    ts = tileset.tile_size
    prefix = layout.spec.game_prefix
    refs: list[dict] = []
    ref_num = 1

    # Floor tiles
    for tx, ty in sorted(layout.floor_tiles):
        tile_def = tileset.get_tile("floor")
        refs.append(_make_ref(ref_num, tile_def.stat_id, tx * ts, ty * ts, 0.0, 0.0))
        ref_num += 1

    # Ceiling tiles (same x/y, z = room_height)
    for tx, ty in sorted(layout.floor_tiles):
        tile_def = tileset.get_tile("ceiling")
        refs.append(_make_ref(
            ref_num, tile_def.stat_id, tx * ts, ty * ts, tileset.room_height, 0.0
        ))
        ref_num += 1

    # Boundary tiles (walls, corners, pillars, doorways)
    for (tx, ty), tile_type in sorted(layout.boundary_tiles.items()):
        tile_def = tileset.get_tile(tile_type)
        rot_z = WALL_ROTATIONS.get(tile_type, 0.0)
        refs.append(_make_ref(ref_num, tile_def.stat_id, tx * ts, ty * ts, 0.0, rot_z))
        ref_num += 1

    # Entrance ACTI ref at first room centre (world coords)
    etx, ety = layout.entrance_tile
    refs.append(_make_ref(ref_num, f"{prefix}_dungeon_entrance", etx * ts, ety * ts, 0.0, 0.0))
    ref_num += 1

    # Exit ACTI ref at last room centre (world coords)
    xtx, xty = layout.exit_tile
    refs.append(_make_ref(ref_num, f"{prefix}_dungeon_exit", xtx * ts, xty * ts, 0.0, 0.0))

    return {
        "rec_type": "CELL",
        "record_id": cell_id,
        "cell_name": cell_id,          # Must equal record_id for teleportToCell
        "cell_flags": 1,               # CELL_INTERIOR = 0x01
        "grid_x": 0,
        "grid_y": 0,
        "ambient": 0x00808080,         # dim grey ambient (torchlight feel)
        "sunlight": 0,
        "fog": 0,
        "fog_density": 0.0,
        "region": "",
        "ref_num_counter": 0,
        "water_height": -1.0,
        "flags": 0,
        "refs": refs,
    }


def _make_ref(ref_num: int, object_id: str, x: float, y: float, z: float, rot_z: float) -> dict:
    ref = {"ref_num": ref_num, "object_id": object_id, "pos": [x, y, z], "rot": [0.0, 0.0, rot_z]}
    ref.update(_REF_DEFAULTS)
    return ref
