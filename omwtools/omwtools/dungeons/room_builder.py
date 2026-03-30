# omwtools/omwtools/dungeons/room_builder.py
import math
import random
from .dungeon_spec import DungeonLayout
from .room_kit import RoomKit
from .tile_spec import TileSet, WALL_ROTATIONS, BASE_TILE
from .cell_builder import _make_ref


def stat_records_roomkit(kit: RoomKit) -> list[dict]:
    """STAT records for all room variants + corridor piece + optional door cap."""
    records = [
        {"rec_type": "STAT", "record_id": v.stat_id, "mesh": v.mesh, "flags": 0}
        for v in kit.variants
    ]
    records.append(
        {"rec_type": "STAT", "record_id": kit.corridor_stat_id,
         "mesh": kit.corridor_mesh, "flags": 0}
    )
    if kit.door_cap_stat_id:
        records.append(
            {"rec_type": "STAT", "record_id": kit.door_cap_stat_id,
             "mesh": kit.door_cap_mesh, "flags": 0}
        )
    return records


def build_roomkit(
    layout: DungeonLayout,
    kit: RoomKit,
    corridor_tiles: TileSet,
    cell_id: str,
    seed: int = 0,
) -> dict:
    """
    Build a CELL record using the room-kit approach:
    - One pre-built room mesh per room (randomly chosen variant)
    - Corridor floor/ceiling tiles only for corridor_tiles
    - Boundary walls only where adjacent to corridor tiles
    - Entrance + exit ACTI refs at first/last room centres
    - Bone torches at mid-height in each room
    """
    rng = random.Random(seed)
    ts  = kit.tile_size
    prefix = layout.spec.game_prefix
    refs: list[dict] = []
    ref_num = 1

    # ── Room meshes (one per room) ──────────────────────────────────────────
    for room in layout.rooms:
        cx, cy = room.centre_tile
        variant = rng.choice(kit.variants)
        refs.append(_make_ref(ref_num, variant.stat_id, cx * ts, cy * ts, 0.0, 0.0))
        ref_num += 1

    # ── Door caps — seal doorways on sides with no corridor ─────────────────
    if kit.door_cap_stat_id:
        corr = layout.corridor_tiles
        for room in layout.rooms:
            cx, cy = room.centre_tile
            rw, rh = room.w, room.h
            # North side (+Y): corridor tiles just above room
            if not any((room.x + dx, room.y + rh) in corr for dx in range(rw)):
                refs.append(_make_ref(ref_num, kit.door_cap_stat_id,
                                      cx * ts, (room.y + rh) * ts, 0.0, 0.0))
                ref_num += 1
            # South side (-Y): corridor tiles just below room
            if not any((room.x + dx, room.y - 1) in corr for dx in range(rw)):
                refs.append(_make_ref(ref_num, kit.door_cap_stat_id,
                                      cx * ts, room.y * ts, 0.0, math.pi))
                ref_num += 1
            # East side (+X): corridor tiles just right of room
            if not any((room.x + rw, room.y + dy) in corr for dy in range(rh)):
                refs.append(_make_ref(ref_num, kit.door_cap_stat_id,
                                      (room.x + rw) * ts, cy * ts, 0.0,
                                      -math.pi / 2))
                ref_num += 1
            # West side (-X): corridor tiles just left of room
            if not any((room.x - 1, room.y + dy) in corr for dy in range(rh)):
                refs.append(_make_ref(ref_num, kit.door_cap_stat_id,
                                      room.x * ts, cy * ts, 0.0,
                                      math.pi / 2))
                ref_num += 1

    # ── Corridor floor + ceiling ────────────────────────────────────────────
    for tx, ty in sorted(layout.corridor_tiles):
        floor_def = corridor_tiles.get_tile("floor")
        refs.append(_make_ref(ref_num, floor_def.stat_id, tx * ts, ty * ts, 0.0, 0.0))
        ref_num += 1
        ceil_def = corridor_tiles.get_tile("ceiling")
        refs.append(_make_ref(ref_num, ceil_def.stat_id, tx * ts, ty * ts,
                               kit.room_height, 0.0))
        ref_num += 1

    # ── Corridor boundary walls (skip tiles adjacent only to room tiles) ────
    corridor_set = layout.corridor_tiles
    for (tx, ty), tile_type in sorted(layout.boundary_tiles.items()):
        cardinal = [(tx, ty - 1), (tx, ty + 1), (tx + 1, ty), (tx - 1, ty)]
        if not any(nb in corridor_set for nb in cardinal):
            continue  # adjacent only to room tiles — room mesh handles this
        base = BASE_TILE.get(tile_type)
        if base not in corridor_tiles.tiles:
            continue
        tile_def = corridor_tiles.get_tile(tile_type)
        rot_z = WALL_ROTATIONS.get(tile_type, 0.0)
        refs.append(_make_ref(ref_num, tile_def.stat_id, tx * ts, ty * ts, 0.0, rot_z))
        ref_num += 1

    # ── Entrance ACTI ───────────────────────────────────────────────────────
    etx, ety = layout.entrance_tile
    refs.append(_make_ref(ref_num, f"{prefix}_dungeon_entrance",
                           etx * ts, ety * ts, 0.0, 0.0))
    ref_num += 1

    # ── Exit ACTI ───────────────────────────────────────────────────────────
    xtx, xty = layout.exit_tile
    refs.append(_make_ref(ref_num, f"{prefix}_dungeon_exit",
                           xtx * ts, xty * ts, 0.0, 0.0))
    ref_num += 1

    # ── Bone torches — one per room ─────────────────────────────────────────
    for room in layout.rooms:
        cx, cy = room.centre_tile
        refs.append(_make_ref(ref_num, f"{prefix}_bone_torch",
                               cx * ts, cy * ts, ts * 0.5, 0.0))
        ref_num += 1

    return {
        "rec_type": "CELL",
        "record_id": cell_id,
        "cell_name": cell_id,
        "cell_flags": 1,
        "grid_x": 0,
        "grid_y": 0,
        "ambient": {"ambient": 0xFFFFFFFF, "sunlight": 0, "fog": 0, "fog_density": 0.0},
        "region": "",
        "ref_num_counter": 0,
        "water_height": -1.0,
        "flags": 0,
        "refs": refs,
    }
