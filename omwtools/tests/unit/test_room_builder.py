import random
from omwtools.dungeons.room_kit import RoomKit, RoomVariant
from omwtools.dungeons.tile_spec import TileSet, TileDef
from omwtools.dungeons.dungeon_spec import DungeonSpec
from omwtools.dungeons.generator import generate
from omwtools.dungeons.room_builder import stat_records_roomkit, build_roomkit

KIT = RoomKit(
    name="cave",
    tile_size=256.0,
    room_tiles=4,
    room_height=256.0,
    variants=[
        RoomVariant(mesh="omwdg\\cave_room_a.dae", stat_id="tst_room_a"),
        RoomVariant(mesh="omwdg\\cave_room_b.dae", stat_id="tst_room_b"),
    ],
    corridor_mesh="omwdg\\cave_corridor.dae",
    corridor_stat_id="tst_corridor",
)

CORRIDOR_TILES = TileSet(
    name="cave",
    tile_size=256.0,
    room_height=256.0,
    tiles={
        "floor":   TileDef(mesh="omwdg\\cave_floor.dae",   stat_id="tst_floor"),
        "wall":    TileDef(mesh="omwdg\\cave_wall.dae",    stat_id="tst_wall"),
        "corner":  TileDef(mesh="omwdg\\cave_corner.dae",  stat_id="tst_corner"),
        "pillar":  TileDef(mesh="omwdg\\cave_pillar.dae",  stat_id="tst_pillar"),
        "doorway": TileDef(mesh="omwdg\\cave_doorway.dae", stat_id="tst_doorway"),
        "ceiling": TileDef(mesh="omwdg\\cave_ceiling.dae", stat_id="tst_ceiling"),
    },
)

SPEC = DungeonSpec(
    name="test_cave", game_prefix="tst", tileset="cave_roomkit",
    room_count=(2, 3), room_size=(4, 4), pool_size=1,
    exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
    creature_pool=[], creatures_per_room=(0, 0),
    loot_containers=[], loot_per_room=(0, 0),
)


def test_roomkit_get_variant_cycles():
    assert KIT.room_size == 1024.0
    assert len(KIT.variants) == 2
    assert KIT.corridor_stat_id == "tst_corridor"


def test_stat_records_roomkit():
    stats = stat_records_roomkit(KIT)
    ids = {s["record_id"] for s in stats}
    assert "tst_room_a" in ids
    assert "tst_room_b" in ids
    assert "tst_corridor" in ids
    assert all(s["rec_type"] == "STAT" for s in stats)


def test_build_roomkit_has_one_ref_per_room():
    layout = generate(SPEC, seed=0)
    cell = build_roomkit(layout, KIT, CORRIDOR_TILES, "tst_cell_0", seed=0)
    refs = cell["refs"]
    room_refs = [r for r in refs if r["object_id"] in {"tst_room_a", "tst_room_b"}]
    assert len(room_refs) == len(layout.rooms)


def test_build_roomkit_no_room_tiles_in_corridor_floors():
    layout = generate(SPEC, seed=0)
    cell = build_roomkit(layout, KIT, CORRIDOR_TILES, "tst_cell_0", seed=0)
    refs = cell["refs"]
    ts = KIT.tile_size
    floor_refs = [r for r in refs if r["object_id"] == "tst_floor"]
    for r in floor_refs:
        tx = int(r["pos"][0] / ts)
        ty = int(r["pos"][1] / ts)
        assert (tx, ty) in layout.corridor_tiles, \
            f"Floor tile at ({tx},{ty}) is not a corridor tile"


def test_build_roomkit_cell_is_interior():
    layout = generate(SPEC, seed=0)
    cell = build_roomkit(layout, KIT, CORRIDOR_TILES, "tst_cell_0", seed=0)
    assert cell["rec_type"] == "CELL"
    assert cell["cell_flags"] & 1
    assert cell["ambient"]["ambient"] == 0xFFFFFFFF
