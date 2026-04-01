# omwtools/omwtools/dungeons/room_builder.py
import math
import random
from .dungeon_spec import DungeonLayout
from .room_kit import RoomKit
from .tile_spec import TileSet
from .cell_builder import _make_ref


def stat_records_roomkit(kit: RoomKit) -> list[dict]:
    """STAT records for all room variants + corridor pieces + optional door cap."""
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
    if kit.corridor_corner_stat_id:
        records.append(
            {"rec_type": "STAT", "record_id": kit.corridor_corner_stat_id,
             "mesh": kit.corridor_corner_mesh, "flags": 0}
        )
    if kit.corridor_cross_stat_id:
        records.append(
            {"rec_type": "STAT", "record_id": kit.corridor_cross_stat_id,
             "mesh": kit.corridor_cross_mesh, "flags": 0}
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
            # Cap rotation (Blender X → OpenMW X, no axis swap):
            #   cap mesh DOOR_W wide in Blender X = E-W; rot=0 seals N or S wall
            #   each 90° CW step turns cap to seal the next wall (N→E→S→W)
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
                                      math.pi / 2))
                ref_num += 1
            # West side (-X): corridor tiles just left of room
            if not any((room.x - 1, room.y + dy) in corr for dy in range(rh)):
                refs.append(_make_ref(ref_num, kit.door_cap_stat_id,
                                      room.x * ts, cy * ts, 0.0,
                                      3 * math.pi / 2))
                ref_num += 1

    # ── Corridor tiles — pre-built oriented corridor meshes ────────────────
    # Classification uses two layers:
    #   corr_set  — only for the dominant-axis guard (cn+cs or ce+cw both True)
    #               so Z-path parallel corridors don't generate false T-junctions
    #   floor_set — corridor + room tiles: counts how many cardinal directions have
    #               SOME floor (room or corridor), determines piece type and orientation
    #
    # Piece types (all rotatable):
    #   straight  — 2 walls (E+W), open N+S;  rot 90° → E-W
    #   corner    — 2 walls (N+W), open S+E;  4 rotations
    #   t         — 1 wall  (S),   open N+E+W; 4 rotations
    #   cross     — 0 walls, open all 4 sides
    corr_set  = layout.corridor_tiles
    floor_set = layout.floor_tiles
    corner_id = kit.corridor_corner_stat_id or kit.corridor_stat_id
    t_id      = kit.corridor_t_stat_id      or kit.corridor_cross_stat_id or kit.corridor_stat_id
    cross_id  = kit.corridor_cross_stat_id  or kit.corridor_stat_id

    for tx, ty in sorted(layout.corridor_tiles):
        cn = (tx, ty + 1) in corr_set
        cs = (tx, ty - 1) in corr_set
        ce = (tx + 1, ty) in corr_set
        cw = (tx - 1, ty) in corr_set
        fn = (tx, ty + 1) in floor_set
        fs = (tx, ty - 1) in floor_set
        fe = (tx + 1, ty) in floor_set
        fw = (tx - 1, ty) in floor_set
        open_n = sum([fn, fs, fe, fw])

        # Rotation convention (no axis swap: Blender X → OpenMW X, Blender Y → OpenMW Y):
        #   rot=0   corridor opens N-S  (walls E+W — Blender X=±140 → OpenMW X=±140)
        #   rot=π/2 corridor opens E-W  (walls N+S)
        #   corner base (rot=0): walls N+W, open S+E
        #   t base (rot=0): wall S, open N+E+W
        if cn and cs:
            # Dominant N-S straight — upgrade to T/cross if room also connects E or W
            if fe and fw:
                stat, rot_z = cross_id, 0.0
            elif fe:
                stat, rot_z = t_id, math.pi / 2        # wall W, open N+S+E  (CW 1 step)
            elif fw:
                stat, rot_z = t_id, 3 * math.pi / 2   # wall E, open N+S+W  (CW 3 steps)
            else:
                stat, rot_z = kit.corridor_stat_id, 0.0           # N-S straight
        elif ce and cw:
            # Dominant E-W straight — upgrade to T/cross if room also connects N or S
            if fn and fs:
                stat, rot_z = cross_id, 0.0
            elif fn:
                stat, rot_z = t_id, 0.0                # wall S, open N+E+W  (CW 0 steps)
            elif fs:
                stat, rot_z = t_id, math.pi            # wall N, open S+E+W  (CW 2 steps)
            else:
                stat, rot_z = kit.corridor_stat_id, math.pi / 2   # E-W straight
        elif open_n == 4:
            stat, rot_z = cross_id, 0.0
        elif open_n == 3:
            # T-junction: 1 wall facing the empty side
            if   not fw: stat, rot_z = t_id, math.pi / 2        # wall W, open N+S+E
            elif not fe: stat, rot_z = t_id, 3 * math.pi / 2   # wall E, open N+S+W
            elif not fn: stat, rot_z = t_id, math.pi            # wall N, open S+E+W
            else:        stat, rot_z = t_id, 0.0                # wall S, open N+E+W
        elif open_n == 2:
            if   fn and fs: stat, rot_z = kit.corridor_stat_id, 0.0            # N-S straight
            elif fe and fw: stat, rot_z = kit.corridor_stat_id, math.pi / 2    # E-W straight
            elif fn and fe: stat, rot_z = corner_id, 3 * math.pi / 2          # NE corner (CW 3 steps)
            elif fn and fw: stat, rot_z = corner_id, math.pi                   # NW corner (CW 2 steps)
            elif fs and fe: stat, rot_z = corner_id, 0.0                       # SE corner (CW 0 steps)
            elif fs and fw: stat, rot_z = corner_id, math.pi / 2               # SW corner (CW 1 step)
            else:           stat, rot_z = cross_id, 0.0
        else:
            stat, rot_z = cross_id, 0.0

        refs.append(_make_ref(ref_num, stat, tx * ts, ty * ts, 0.0, rot_z))
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

    # ── Cave torches — two per room (NW + SE corners), below ceiling ────────
    for room in layout.rooms:
        half = ts * 0.35
        corners = [
            (room.x * ts + half,              room.y * ts + half),
            ((room.x + room.w) * ts - half,   (room.y + room.h) * ts - half),
        ]
        for cx_pos, cy_pos in corners:
            refs.append(_make_ref(ref_num, f"{prefix}_cave_torch",
                                   cx_pos, cy_pos, 30.0, 0.0))
            ref_num += 1

    # ── Corridor lights — one glow mushroom every 2 tiles, offset to wall ───
    for i, (tx, ty) in enumerate(sorted(layout.corridor_tiles)):
        if i % 2 == 0:
            # Alternate left/right wall so mushrooms don't clump on one side
            offset = ts * 0.35 if (i // 2) % 2 == 0 else -ts * 0.35
            refs.append(_make_ref(ref_num, f"{prefix}_glow_mushroom",
                                   tx * ts + offset, ty * ts, 20.0, 0.0))
            ref_num += 1

    return {
        "rec_type": "CELL",
        "record_id": cell_id,
        "cell_name": cell_id,
        "cell_flags": 1,
        "grid_x": 0,
        "grid_y": 0,
        "ambient": {"ambient": 0xFFE0E0E0, "sunlight": 0xFFE0E0E0, "fog": 0, "fog_density": 0.0},
        "region": "",
        "ref_num_counter": 0,
        "water_height": -1.0,
        "flags": 0,
        "refs": refs,
    }
