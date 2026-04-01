# omwtools/tests/unit/test_corridor_rotation.py
"""
Rotation-compatibility tests for corridor pieces.

For every corridor tile in a generated dungeon we verify:
  1. The placed piece (stat_id + rot_z) is open toward every floor-set neighbor.
  2. Adjacent corridor tiles are *mutually* open toward each other.
  3. Each direct facing of piece A toward piece B is verified explicitly
     against the expected direction derived from the tile coordinate delta.

Rotation model (CW, OpenMW positive rot_z is clockwise when viewed from above):
  CW cycle: N → E → S → W → N  (each 90° step)

  Blender X → OpenMW X (E-W axis), Blender Y → OpenMW Y (N-S axis).  No axis swap.
  Mesh base orientations at rot_z = 0:
    straight : {N, S}            (walls E+W — Blender walls at X=±140 → OpenMW X=±140)
    corner   : {S, E}            (walls N+W — Blender N-wall at Y=+140, W-wall at X=-140)
    t        : {N, E, W}         (wall S — Blender S-wall at Y=-140)
    cross    : {N, S, E, W}      (no walls)
    room     : {N, S, E, W}      (4 doorways on all sides)
"""
import math
import pytest
from omwtools.dungeons.room_kit import RoomKit, RoomVariant
from omwtools.dungeons.tile_spec import TileSet, TileDef
from omwtools.dungeons.dungeon_spec import DungeonSpec, Room
from omwtools.dungeons.generator import generate
from omwtools.dungeons.room_builder import build_roomkit

# ─── Fixtures ────────────────────────────────────────────────────────────────

_CORRIDOR_STAT   = "rot_tst_corridor"
_CORNER_STAT     = "rot_tst_corner"
_T_STAT          = "rot_tst_t"
_CROSS_STAT      = "rot_tst_cross"
_ROOM_STAT       = "rot_tst_room"
_DOORCAP_STAT    = "rot_tst_doorcap"

KIT = RoomKit(
    name="rot_test",
    tile_size=256.0,
    room_tiles=4,
    room_height=256.0,
    variants=[RoomVariant(mesh="omwdg\\cave_room_a.dae", stat_id=_ROOM_STAT)],
    corridor_mesh="omwdg\\cave_corridor.dae",      corridor_stat_id=_CORRIDOR_STAT,
    corridor_corner_mesh="omwdg\\cave_corner.dae", corridor_corner_stat_id=_CORNER_STAT,
    corridor_t_mesh="omwdg\\cave_t.dae",           corridor_t_stat_id=_T_STAT,
    corridor_cross_mesh="omwdg\\cave_cross.dae",   corridor_cross_stat_id=_CROSS_STAT,
    door_cap_mesh="omwdg\\cave_doorcap.dae",       door_cap_stat_id=_DOORCAP_STAT,
)

CORRIDOR_TILES = TileSet(
    name="rot_test", tile_size=256.0, room_height=256.0,
    tiles={"floor": TileDef(mesh="", stat_id=""), "wall": TileDef(mesh="", stat_id=""),
           "corner": TileDef(mesh="", stat_id=""), "pillar": TileDef(mesh="", stat_id=""),
           "doorway": TileDef(mesh="", stat_id=""), "ceiling": TileDef(mesh="", stat_id="")},
)

SPEC = DungeonSpec(
    name="rot_test", game_prefix="rot", tileset="cave_roomkit",
    room_count=(3, 4), room_size=(4, 4), pool_size=1,
    exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
    creature_pool=[], creatures_per_room=(0, 0),
    loot_containers=[], loot_per_room=(0, 0),
)

SEEDS = [0, 1, 2, 7, 42]  # tested dungeon seeds


# ─── Rotation helpers ─────────────────────────────────────────────────────────

# CW order: each step rotates 90° clockwise (OpenMW positive rot_z is CW).
_CW_DIRS = ['N', 'E', 'S', 'W']

_OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}

_DELTA_TO_DIR = {(0, +1): 'N', (0, -1): 'S', (+1, 0): 'E', (-1, 0): 'W'}

# Base open faces for each piece type (at rot_z = 0).
# No axis swap: Blender X → OpenMW X (E-W), Blender Y → OpenMW Y (N-S).
#   corridor walls at Blender X=±140 → OpenMW X=±140 (E+W walls) → opens N+S
#   corner: N-wall at Blender Y=+140 (OpenMW N), W-wall at Blender X=-140 (OpenMW W) → opens S+E
#   t: S-wall at Blender Y=-140 (OpenMW S) → opens N+E+W
_BASE_OPEN = {
    _CORRIDOR_STAT: frozenset({'N', 'S'}),
    _CORNER_STAT:   frozenset({'S', 'E'}),  # walls N+W
    _T_STAT:        frozenset({'N', 'E', 'W'}),  # wall S
    _CROSS_STAT:    frozenset({'N', 'S', 'E', 'W'}),
    _ROOM_STAT:     frozenset({'N', 'S', 'E', 'W'}),
    _DOORCAP_STAT:  frozenset(),  # cap seals all faces
}


def _rot_steps(rot_z: float) -> int:
    """Convert rot_z radians to the number of CCW 90° steps (0–3)."""
    return round(rot_z / (math.pi / 2)) % 4


def piece_open_faces(stat_id: str, rot_z: float) -> frozenset:
    """
    Return the set of cardinal directions that are OPEN for this piece
    after CW rotation by rot_z.

    CW rotation: N→E→S→W→N for each +90° step.
    """
    base = _BASE_OPEN.get(stat_id, frozenset({'N', 'S', 'E', 'W'}))
    steps = _rot_steps(rot_z)
    return frozenset(
        _CW_DIRS[(_CW_DIRS.index(d) + steps) % 4]
        for d in base
    )


# ─── Test helpers ─────────────────────────────────────────────────────────────

def _refs_by_tile(cell: dict, ts: float) -> dict:
    """
    Map (tile_x, tile_y) → structural corridor ref for every tile.

    Multiple refs can share a tile position (corridor piece + decorations).
    Prefer the ref whose object_id is a known corridor piece (in _BASE_OPEN);
    fall back to any other ref only if no structural piece is found.
    """
    result = {}
    for ref in cell['refs']:
        tx = round(ref['pos'][0] / ts)
        ty = round(ref['pos'][1] / ts)
        existing = result.get((tx, ty))
        # Prefer structural pieces over decorations
        if existing is None or ref['object_id'] in _BASE_OPEN:
            result[(tx, ty)] = ref
    return result


def _stat(ref: dict) -> str:
    return ref['object_id']


def _rot(ref: dict) -> float:
    return ref['rot'][2]


def _required_open(tx: int, ty: int, floor_set: set) -> frozenset:
    """
    Minimum open directions for the corridor tile at (tx, ty):
    the piece MUST be open toward every floor-set neighbor.
    The piece may open additional directions (T instead of straight is fine).
    """
    open_dirs = set()
    for (dx, dy), direction in _DELTA_TO_DIR.items():
        if (tx + dx, ty + dy) in floor_set:
            open_dirs.add(direction)
    return frozenset(open_dirs)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestPieceOpenFaces:
    """Unit tests for the piece_open_faces helper itself."""

    def test_straight_ns_no_rotation(self):
        """Base corridor (rot=0): walls E+W (Blender X=±140 → OpenMW X), opens N-S."""
        assert piece_open_faces(_CORRIDOR_STAT, 0.0) == {'N', 'S'}

    def test_straight_ew_half_pi(self):
        """rot=π/2 CCW rotates N-S corridor to E-W."""
        assert piece_open_faces(_CORRIDOR_STAT, math.pi / 2) == {'E', 'W'}

    def test_corner_se_no_rotation(self):
        """Base corner (rot=0): walls N+W (Blender Y=+140, X=-140), open S+E."""
        assert piece_open_faces(_CORNER_STAT, 0.0) == {'S', 'E'}

    def test_corner_sw_half_pi(self):
        """rot=π/2 CW: S→W, E→S → open S+W (SW corner)."""
        assert piece_open_faces(_CORNER_STAT, math.pi / 2) == {'S', 'W'}

    def test_corner_nw_pi(self):
        """rot=π CW: S→N, E→W → open N+W (NW corner)."""
        assert piece_open_faces(_CORNER_STAT, math.pi) == {'N', 'W'}

    def test_corner_ne_three_half_pi(self):
        """rot=3π/2 CW: S→E, E→N → open N+E (NE corner)."""
        assert piece_open_faces(_CORNER_STAT, 3 * math.pi / 2) == {'N', 'E'}

    def test_t_wall_south_no_rotation(self):
        """Base T (rot=0): wall S (Blender Y=-140 → OpenMW Y=-140), open N+E+W."""
        assert piece_open_faces(_T_STAT, 0.0) == {'N', 'E', 'W'}

    def test_t_wall_west_half_pi(self):
        """rot=π/2 CW: N→E, E→S, W→N → wall W, open N+S+E."""
        assert piece_open_faces(_T_STAT, math.pi / 2) == {'N', 'S', 'E'}

    def test_t_wall_north_pi(self):
        """rot=π CW: wall N, open S+E+W."""
        assert piece_open_faces(_T_STAT, math.pi) == {'S', 'E', 'W'}

    def test_t_wall_east_three_half_pi(self):
        """rot=3π/2 CW: wall E, open N+S+W."""
        assert piece_open_faces(_T_STAT, 3 * math.pi / 2) == {'N', 'S', 'W'}

    def test_cross_always_all_open(self):
        for rot in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
            assert piece_open_faces(_CROSS_STAT, rot) == {'N', 'S', 'E', 'W'}

    def test_all_four_corners_cover_all_combinations(self):
        """The four corner rotations collectively cover all 4 open-face pairs."""
        pairs = {frozenset(piece_open_faces(_CORNER_STAT, r))
                 for r in (0.0, math.pi/2, math.pi, 3*math.pi/2)}
        assert pairs == {
            frozenset({'S', 'E'}),
            frozenset({'S', 'W'}),
            frozenset({'N', 'W'}),
            frozenset({'N', 'E'}),
        }


class TestCorridorRotationInDungeon:
    """
    For every dungeon seed, verify that each placed corridor piece is
    open toward exactly its floor-set neighbours (respecting dominant-axis
    guard), and that adjacent tiles are mutually open.
    """

    @pytest.mark.parametrize("seed", SEEDS)
    def test_piece_open_toward_all_floor_neighbors(self, seed):
        """Each piece must be open toward every floor-set neighbor it has."""
        layout = generate(SPEC, seed=seed)
        cell   = build_roomkit(layout, KIT, CORRIDOR_TILES, "rot_test_cell", seed=seed)
        tile_refs = _refs_by_tile(cell, KIT.tile_size)

        errors = []
        for tx, ty in sorted(layout.corridor_tiles):
            ref = tile_refs.get((tx, ty))
            if ref is None:
                errors.append(f"  No ref placed for corridor tile ({tx},{ty})")
                continue

            stat     = _stat(ref)
            rot_z    = _rot(ref)
            actual   = piece_open_faces(stat, rot_z)
            required = _required_open(tx, ty, layout.floor_tiles)

            if not required.issubset(actual):
                errors.append(
                    f"  tile ({tx},{ty}) stat={stat} rot={rot_z:.4f}: "
                    f"open={sorted(actual)} missing={sorted(required - actual)}"
                )

        assert not errors, (
            f"seed={seed}: corridor pieces have wrong open faces:\n"
            + "\n".join(errors)
        )

    @pytest.mark.parametrize("seed", SEEDS)
    def test_adjacent_corridor_tiles_mutually_open(self, seed):
        """
        For every pair of adjacent corridor tiles A and B (B is cardinal
        neighbor of A), piece A must be open toward B AND piece B must be
        open toward A.
        """
        layout    = generate(SPEC, seed=seed)
        cell      = build_roomkit(layout, KIT, CORRIDOR_TILES, "rot_test_cell", seed=seed)
        tile_refs = _refs_by_tile(cell, KIT.tile_size)
        corr      = layout.corridor_tiles

        errors = []
        checked = set()
        for (tx, ty) in sorted(corr):
            for (dx, dy), dir_a in _DELTA_TO_DIR.items():
                nb = (tx + dx, ty + dy)
                if nb not in corr:
                    continue
                pair = tuple(sorted([(tx, ty), nb]))
                if pair in checked:
                    continue
                checked.add(pair)

                ref_a = tile_refs.get((tx, ty))
                ref_b = tile_refs.get(nb)
                if not ref_a or not ref_b:
                    continue

                open_a = piece_open_faces(_stat(ref_a), _rot(ref_a))
                open_b = piece_open_faces(_stat(ref_b), _rot(ref_b))

                dir_b = _OPPOSITE[dir_a]   # B's direction back toward A
                a_open_to_b = dir_a in open_a
                b_open_to_a = dir_b in open_b

                if not a_open_to_b or not b_open_to_a:
                    errors.append(
                        f"  tiles ({tx},{ty})↔{nb}: "
                        f"A({_stat(ref_a)} rot={_rot(ref_a):.3f}) open={sorted(open_a)} "
                        f"→{dir_a}={a_open_to_b}  "
                        f"B({_stat(ref_b)} rot={_rot(ref_b):.3f}) open={sorted(open_b)} "
                        f"→{dir_b}={b_open_to_a}"
                    )

        assert not errors, (
            f"seed={seed}: adjacent corridor pairs not mutually open:\n"
            + "\n".join(errors)
        )

    @pytest.mark.parametrize("seed", SEEDS)
    def test_corridor_adjacent_to_room_at_doorway_only(self, seed):
        """
        Corridor tiles adjacent to a room wall must be at the doorway centre:
        - N/S wall (dy≠0): corridor column must equal room.centre_tile[0]
        - E/W wall (dx≠0): corridor row    must equal room.centre_tile[1]
        The room mesh has exactly one DOOR_W-wide opening per wall centred on
        centre_tile; a corridor tile at any other position hits solid wall.
        """
        layout = generate(SPEC, seed=seed)

        tile_to_room: dict[tuple[int, int], Room] = {}
        for room in layout.rooms:
            for tile in room.room_tiles():
                tile_to_room[tile] = room

        errors = []
        for (tx, ty) in sorted(layout.corridor_tiles):
            for (dx, dy), direction in _DELTA_TO_DIR.items():
                nb = (tx + dx, ty + dy)
                room = tile_to_room.get(nb)
                if room is None:
                    continue
                cx, cy = room.centre_tile
                if dy != 0:   # touching N or S wall — must be centre column
                    if tx != cx:
                        errors.append(
                            f"  ({tx},{ty})→{direction} room "
                            f"[{room.x},{room.y} {room.w}×{room.h}]: "
                            f"col {tx} ≠ doorway col {cx}"
                        )
                else:         # touching E or W wall — must be centre row
                    if ty != cy:
                        errors.append(
                            f"  ({tx},{ty})→{direction} room "
                            f"[{room.x},{room.y} {room.w}×{room.h}]: "
                            f"row {ty} ≠ doorway row {cy}"
                        )

        assert not errors, (
            f"seed={seed}: corridor tiles not at room doorway centres:\n"
            + "\n".join(errors)
        )

    @pytest.mark.parametrize("seed", SEEDS)
    def test_corridor_open_toward_room_tiles(self, seed):
        """
        A corridor tile adjacent to a room tile must be open toward that room.
        (The room mesh has doorways on all 4 sides, so the corridor must face them.)
        """
        layout    = generate(SPEC, seed=seed)
        cell      = build_roomkit(layout, KIT, CORRIDOR_TILES, "rot_test_cell", seed=seed)
        tile_refs = _refs_by_tile(cell, KIT.tile_size)
        room_tiles = {t for room in layout.rooms for t in room.room_tiles()}

        errors = []
        for (tx, ty) in sorted(layout.corridor_tiles):
            ref = tile_refs.get((tx, ty))
            if not ref:
                continue
            open_f = piece_open_faces(_stat(ref), _rot(ref))
            for (dx, dy), direction in _DELTA_TO_DIR.items():
                nb = (tx + dx, ty + dy)
                if nb in room_tiles and direction not in open_f:
                    errors.append(
                        f"  tile ({tx},{ty}) faces room at {nb} in direction {direction} "
                        f"but piece {_stat(ref)} rot={_rot(ref):.3f} "
                        f"is CLOSED in that direction (open={sorted(open_f)})"
                    )

        assert not errors, (
            f"seed={seed}: corridor tiles blocked toward adjacent rooms:\n"
            + "\n".join(errors)
        )
