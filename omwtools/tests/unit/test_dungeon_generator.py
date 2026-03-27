import pytest
from collections import deque
from omwtools.dungeons.dungeon_spec import DungeonSpec, DungeonLayout
from omwtools.dungeons.tile_spec import TileSet, TileDef
from omwtools.dungeons.generator import generate
from omwtools.records.cell import Cell
from omwtools.dungeons.pool_builder import build_pool
from omwtools.dungeons.lua_config import generate_lua_config


SPEC = DungeonSpec(
    name="test_cave",
    game_prefix="tst",
    tileset="cave",
    room_count=(2, 4),
    room_size=(3, 5),
    pool_size=1,
    exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
    creature_pool=[],
    creatures_per_room=(0, 0),
    loot_containers=[],
    loot_per_room=(0, 0),
)

TILESET = TileSet(
    name="cave",
    tile_size=4.0,
    room_height=3.0,
    tiles={
        "floor":   TileDef(mesh="omwdg\\cave_floor.dae",   stat_id="tst_cave_floor"),
        "wall":    TileDef(mesh="omwdg\\cave_wall.dae",    stat_id="tst_cave_wall"),
        "corner":  TileDef(mesh="omwdg\\cave_corner.dae",  stat_id="tst_cave_corner"),
        "pillar":  TileDef(mesh="omwdg\\cave_pillar.dae",  stat_id="tst_cave_pillar"),
        "doorway": TileDef(mesh="omwdg\\cave_doorway.dae", stat_id="tst_cave_doorway"),
        "ceiling": TileDef(
            mesh="omwdg\\cave_ceiling.dae",
            stat_id="tst_cave_ceiling",
            z_offset=3.0,
        ),
    },
)


def test_deterministic():
    layout1 = generate(SPEC, seed=0)
    layout2 = generate(SPEC, seed=0)
    assert layout1.floor_tiles == layout2.floor_tiles
    assert layout1.rooms == layout2.rooms


def test_different_seeds_differ():
    layout0 = generate(SPEC, seed=0)
    layout1 = generate(SPEC, seed=1)
    assert layout0.floor_tiles != layout1.floor_tiles or layout0.rooms != layout1.rooms


def test_room_count_in_spec_bounds():
    for seed in range(10):
        layout = generate(SPEC, seed=seed)
        assert SPEC.room_count[0] <= len(layout.rooms) <= SPEC.room_count[1]


def test_room_size_in_spec_bounds():
    for seed in range(10):
        layout = generate(SPEC, seed=seed)
        for room in layout.rooms:
            assert SPEC.room_size[0] <= room.w <= SPEC.room_size[1]
            assert SPEC.room_size[0] <= room.h <= SPEC.room_size[1]


def test_all_rooms_connected():
    """BFS from first room centre must reach all other room centres via floor tiles."""
    layout = generate(SPEC, seed=42)
    if len(layout.rooms) < 2:
        pytest.skip("Degenerate single-room layout for this seed — use multi-room seed")
    start = layout.rooms[0].centre_tile
    visited: set[tuple[int, int]] = set()
    queue = deque([start])
    while queue:
        tx, ty = queue.popleft()
        if (tx, ty) in visited:
            continue
        visited.add((tx, ty))
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nb = (tx + dx, ty + dy)
            if nb in layout.floor_tiles and nb not in visited:
                queue.append(nb)
    for room in layout.rooms:
        assert room.centre_tile in visited, f"Room at {room.centre_tile} not reachable"


def test_anchor_count_equals_room_count():
    layout = generate(SPEC, seed=7)
    assert len(layout.anchor_tiles) == len(layout.rooms)


def test_entrance_and_exit_tiles_set():
    layout = generate(SPEC, seed=0)
    assert layout.entrance_tile == layout.rooms[0].centre_tile
    assert layout.exit_tile == layout.rooms[-1].centre_tile


def test_no_overlapping_rooms():
    for seed in range(10):
        layout = generate(SPEC, seed=seed)
        for i, r1 in enumerate(layout.rooms):
            for j, r2 in enumerate(layout.rooms):
                if i != j:
                    assert not r1.overlaps(r2, margin=0), \
                        f"Rooms {i} and {j} overlap at seed {seed}"


def test_corridor_tiles_not_in_any_room():
    """Corridor tiles must be floor tiles not belonging to any room."""
    layout = generate(SPEC, seed=3)
    all_room_tiles: set[tuple[int, int]] = set()
    for room in layout.rooms:
        all_room_tiles.update(room.room_tiles())
    assert layout.corridor_tiles.isdisjoint(all_room_tiles), \
        "corridor_tiles overlaps with room tile(s)"


def test_doorway_tiles_present_when_rooms_gt_1():
    """There must be at least one doorway boundary tile when corridors connect rooms."""
    layout = generate(SPEC, seed=0)
    if len(layout.rooms) < 2:
        return
    doorway_tiles = [t for t, tt in layout.boundary_tiles.items() if tt == "doorway"]
    assert len(doorway_tiles) > 0, "No doorway tiles generated despite multiple rooms"


from omwtools.dungeons.cell_builder import build, stat_records


def test_cell_rec_type():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    assert cell["rec_type"] == "CELL"


def test_cell_record_id():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    assert cell["record_id"] == "tst_test_cave_0"


def test_cell_name_equals_record_id():
    """cell_name must equal record_id for predictable teleportToCell targeting."""
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    assert cell["cell_name"] == "tst_test_cave_0"


def test_cell_is_interior():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    assert cell["cell_flags"] & 0x01  # CELL_INTERIOR bit set


def test_floor_ref_count_equals_floor_tiles():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    floor_refs = [r for r in cell["refs"] if r["object_id"] == "tst_cave_floor"]
    assert len(floor_refs) == len(layout.floor_tiles)


def test_ceiling_count_equals_floor_count():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    floor_refs  = [r for r in cell["refs"] if r["object_id"] == "tst_cave_floor"]
    ceiling_refs = [r for r in cell["refs"] if r["object_id"] == "tst_cave_ceiling"]
    assert len(ceiling_refs) == len(floor_refs)


def test_entrance_and_exit_refs_present():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    ids = {r["object_id"] for r in cell["refs"]}
    assert "tst_dungeon_entrance" in ids
    assert "tst_dungeon_exit" in ids


def test_ref_world_coords_use_tile_size():
    """Floor ref at tile (1,0) should have pos [tile_size, 0, 0]."""
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    # Pick any floor ref and verify its position is a multiple of tile_size
    floor_refs = [r for r in cell["refs"] if r["object_id"] == "tst_cave_floor"]
    ts = TILESET.tile_size
    for ref in floor_refs:
        assert ref["pos"][0] % ts == pytest.approx(0.0)
        assert ref["pos"][1] % ts == pytest.approx(0.0)


def test_stat_records_returns_one_per_tile_type():
    stats = stat_records(TILESET)
    assert len(stats) == len(TILESET.tiles)
    for s in stats:
        assert s["rec_type"] == "STAT"
        assert s["mesh"].startswith("omwdg\\")
        assert s["flags"] == 0


def test_build_cell_roundtrip_via_from_dict():
    """build() output must be consumable by Cell.from_dict without errors."""
    layout = generate(SPEC, seed=0)
    cell_dict = build(layout, TILESET, "tst_test_cave_0")
    cell_obj = Cell.from_dict(cell_dict)
    assert cell_obj.cell_name == "tst_test_cave_0"
    assert cell_obj.ambient.ambient == 0x00808080


def test_pool_builder_cell_count():
    spec = DungeonSpec(
        name="tiny", game_prefix="tst", tileset="cave",
        room_count=(1, 2), room_size=(3, 4), pool_size=3,
        exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
        creature_pool=["tst_bear"], creatures_per_room=(1, 1),
        loot_containers=["tst_chest"], loot_per_room=(0, 1),
    )
    records, layouts, _ = build_pool(spec, TILESET)
    cell_records = [r for r in records if r["rec_type"] == "CELL"]
    assert len(cell_records) == 3
    assert len(layouts) == 3


def test_pool_builder_cell_ids_sequential():
    spec = DungeonSpec(
        name="tiny", game_prefix="tst", tileset="cave",
        room_count=(1, 2), room_size=(3, 4), pool_size=3,
        exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
        creature_pool=[], creatures_per_room=(0, 0),
        loot_containers=[], loot_per_room=(0, 0),
    )
    records, _, cell_ids = build_pool(spec, TILESET)
    assert cell_ids == ["tst_tiny_0", "tst_tiny_1", "tst_tiny_2"]
    # Also verify IDs are consistent with what was baked into CELL records
    record_ids = [r["record_id"] for r in records if r["rec_type"] == "CELL"]
    assert record_ids == cell_ids


def test_pool_builder_start_seed_offset():
    spec = DungeonSpec(
        name="tiny", game_prefix="tst", tileset="cave",
        room_count=(2, 3), room_size=(3, 4), pool_size=1,
        exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
        creature_pool=[], creatures_per_room=(0, 0),
        loot_containers=[], loot_per_room=(0, 0),
    )
    _, layouts_s0, _ = build_pool(spec, TILESET, start_seed=0)
    _, layouts_s5, _ = build_pool(spec, TILESET, start_seed=5)
    assert layouts_s0[0].floor_tiles != layouts_s5[0].floor_tiles


def test_lua_config_contains_cell_ids():
    spec = DungeonSpec(
        name="tiny", game_prefix="tst", tileset="cave",
        room_count=(1, 2), room_size=(3, 4), pool_size=2,
        exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
        creature_pool=["tst_bear"], creatures_per_room=(1, 1),
        loot_containers=[], loot_per_room=(0, 0),
    )
    _, layouts, cell_ids = build_pool(spec, TILESET)
    lua = generate_lua_config("tiny", spec, layouts, TILESET, cell_ids)
    assert "tst_tiny_0" in lua
    assert "tst_tiny_1" in lua
    assert "TST_Dungeons" in lua
