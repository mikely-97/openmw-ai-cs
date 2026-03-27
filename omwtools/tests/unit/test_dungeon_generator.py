import pytest
from collections import deque
from omwtools.dungeons.dungeon_spec import DungeonSpec, DungeonLayout
from omwtools.dungeons.tile_spec import TileSet, TileDef
from omwtools.dungeons.generator import generate


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
