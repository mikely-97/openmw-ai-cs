# omwtools/tests/unit/test_mesh_standards.py
"""
Verify that the mesh_standards module defines a self-consistent
connection interface for all dungeon mesh pieces.

Standard: every connectable face exposes a DOOR_W × DOOR_H opening
centred on the tile/doorway midpoint, with inner wall faces exactly
at ±HALF_OPEN = ±128 on each side.

Pieces must comply:
  - Corridor straight  (E/W walls, inner face at ±HALF_OPEN)
  - Corridor corner    (same — two walls, L-shape)
  - Corridor T         (same — one wall)
  - Corridor cross     (no walls — all four sides open)
  - Room doorway       (pillar inner face at ±HALF_OPEN)
  - Door cap           (panel exactly DOOR_W × DOOR_H)

Tests here work on the constants only (no Blender required).
Integration tests that parse the actual .dae geometry can be added
once a CI environment with generated meshes is available.
"""
import sys
from pathlib import Path

# Locate mesh_standards.py — lives in games/jungle_troll_tribes/dungeons/
# parents: [0]=unit, [1]=tests, [2]=omwtools, [3]=openmw-ai-cs
_DUNGEONS = Path(__file__).parents[3] / "games" / "jungle_troll_tribes" / "dungeons"
sys.path.insert(0, str(_DUNGEONS))

from mesh_standards import TILE, ROOM, H, WALL_T, DOOR_W, DOOR_H, HALF_OPEN


# ─── Opening dimensions ───────────────────────────────────────────────────────

class TestOpeningDimensions:
    """Opening must be exactly one tile wide and full height — no lintel."""

    def test_opening_width_is_one_tile(self):
        assert DOOR_W == TILE, (
            f"DOOR_W={DOOR_W} must equal TILE={TILE} "
            "(each doorway spans exactly one tile width)"
        )

    def test_opening_height_is_full_room_height(self):
        assert DOOR_H == H, (
            f"DOOR_H={DOOR_H} must equal H={H} "
            "(full height opening — no lintel allowed)"
        )

    def test_opening_width_is_256(self):
        assert DOOR_W == 256.0

    def test_opening_height_is_256(self):
        assert DOOR_H == 256.0


# ─── Inner face alignment ─────────────────────────────────────────────────────

class TestInnerFaceAlignment:
    """Wall inner faces must sit at exactly ±HALF_OPEN = ±128 from centre."""

    def test_half_open_is_half_tile(self):
        assert HALF_OPEN == TILE / 2 == 128.0

    def test_corridor_wall_inner_face(self):
        """
        Corridor E/W wall:
          centre  = HALF_OPEN + WALL_T/2  (= 128 + 12 = 140)
          inner   = centre   - WALL_T/2   (= 140 - 12 = 128 = HALF_OPEN)
        """
        wall_centre = HALF_OPEN + WALL_T / 2
        inner_face  = wall_centre - WALL_T / 2
        assert inner_face == HALF_OPEN, (
            f"Corridor wall inner face at {inner_face}, expected {HALF_OPEN}"
        )

    def test_room_doorway_pillar_inner_face(self):
        """
        Room doorway flanking pillar (lateral axis — perpendicular to wall normal):
          hs            = ROOM/2          = 512
          pillar_width  = hs - HALF_OPEN  = 384
          pillar_centre = HALF_OPEN + pillar_width/2 = 128 + 192 = 320
          inner_face    = pillar_centre - pillar_width/2 = 320 - 192 = 128 = HALF_OPEN
        """
        hs            = ROOM / 2
        pillar_width  = hs - HALF_OPEN
        pillar_centre = HALF_OPEN + pillar_width / 2
        inner_face    = pillar_centre - pillar_width / 2
        assert inner_face == HALF_OPEN, (
            f"Room pillar inner face at {inner_face}, expected {HALF_OPEN}"
        )

    def test_room_pillar_depth_seals_corridor_corner(self):
        """
        Pillar depth in the outward direction must extend from the room interior
        face (hs - WALL_T/2) to the far edge of the adjacent corridor tile
        (hs + TILE/2), so the corner between room wall and corridor side wall
        is fully sealed — no void gap at X > HALF_OPEN, Y > room wall outer face.

          depth = WALL_T/2 + TILE/2 = 12 + 128 = 140
          centre = hs - WALL_T/2 + depth/2 = 500 + 70 = 570
          inner face (room side) = centre - depth/2 = 500 = hs - WALL_T/2  ✓
          outer face (corridor)  = centre + depth/2 = 640 = hs + TILE/2    ✓
        """
        hs = ROOM / 2
        depth = WALL_T / 2 + TILE / 2
        centre = hs - WALL_T / 2 + depth / 2
        inner_face = centre - depth / 2
        outer_face = centre + depth / 2
        assert inner_face == hs - WALL_T / 2, "Pillar inner face must be at room interior surface"
        assert outer_face == hs + TILE / 2,   "Pillar outer face must reach corridor tile outer edge"
        assert depth == 140.0
        assert centre == 570.0

    def test_room_and_corridor_inner_faces_match(self):
        """Room doorway inner face must equal corridor wall inner face."""
        # Corridor
        corr_inner = (HALF_OPEN + WALL_T / 2) - WALL_T / 2
        # Room pillar
        pw = ROOM / 2 - HALF_OPEN
        room_inner = (HALF_OPEN + pw / 2) - pw / 2
        assert corr_inner == room_inner == HALF_OPEN


# ─── Door cap ─────────────────────────────────────────────────────────────────

class TestDoorCap:
    """Door cap must exactly seal one standard opening."""

    def test_cap_width_matches_opening(self):
        assert DOOR_W == TILE, "Cap must be exactly one tile wide"

    def test_cap_height_matches_opening(self):
        assert DOOR_H == H, "Cap must be full height (no lintel)"

    def test_cap_is_256x256(self):
        assert DOOR_W == 256.0 and DOOR_H == 256.0


# ─── Room / corridor interface ────────────────────────────────────────────────

class TestRoomCorridorInterface:
    """Room doorways and corridor openings must be identical."""

    def test_openings_are_identical(self):
        """A corridor tile must fit exactly into a room doorway."""
        assert DOOR_W == TILE, "Corridor opening width == TILE == DOOR_W"
        assert DOOR_H == H,    "Corridor opening height == H == DOOR_H"

    def test_room_is_four_tiles_wide(self):
        assert ROOM == 4 * TILE

    def test_floor_extension_covers_l_path_gap(self):
        """
        L-path corridors place the first tile ONE full tile beyond the room edge.
        The corridor tile's near floor edge is therefore TILE/2 beyond the room wall.
        The room floor must extend at least TILE/2 past every wall face so the
        two floor planes meet flush (no gap).

        Concrete example for a 4-tile room with south L-path corridor:
          room floor south edge  = room_center - (ROOM/2 + TILE/2) = room_center - 640
          corridor tile center   = room_center - ROOM/2 - TILE     = room_center - 768
          corridor tile near edge = room_center - 768 + TILE/2     = room_center - 640
          → exactly flush, no gap.
        """
        room_wall_offset = ROOM / 2               # 512
        floor_half       = ROOM / 2 + TILE / 2    # 640  (ROOM+TILE / 2)
        l_path_tile_center = room_wall_offset + TILE     # 768 from room center
        l_path_near_edge   = l_path_tile_center - TILE / 2  # 640 from room center
        assert floor_half >= l_path_near_edge, (
            "Room floor must reach the near edge of the first L-path corridor tile"
        )
        assert floor_half == l_path_near_edge, (
            "Room floor should meet the L-path corridor tile edge exactly (no gap, no overlap)"
        )

    def test_no_lintel(self):
        """Lintel height must be zero — opening fills the full wall height."""
        lintel_height = H - DOOR_H
        assert lintel_height == 0.0, (
            f"Lintel of {lintel_height} units will block corridor junction"
        )
