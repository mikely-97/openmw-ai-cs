# games/jungle_troll_tribes/dungeons/tilesets/cave_roomkit.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[4] / "omwtools"))

from omwtools.dungeons.room_kit import RoomKit, RoomVariant
from omwtools.dungeons.tile_spec import TileSet, TileDef

# One basic cave room (1024×1024×256, full-height doorways on all 4 sides).
# Room variety comes from procedurally placed loot/creatures, not mesh variants.
cave_roomkit = RoomKit(
    name="cave",
    tile_size=256.0,
    room_tiles=4,
    room_height=256.0,
    variants=[
        RoomVariant(mesh="omwdg\\cave_room_a.dae", stat_id="jtt_cave_room_a"),
    ],
    corridor_mesh="omwdg\\cave_corridor.dae",
    corridor_stat_id="jtt_cave_corridor",
    door_cap_mesh="omwdg\\cave_doorway_cap.dae",
    door_cap_stat_id="jtt_cave_doorway_cap",
    corridor_corner_mesh="omwdg\\cave_corridor_corner.dae",
    corridor_corner_stat_id="jtt_cave_corridor_corner",
    corridor_t_mesh="omwdg\\cave_corridor_t.dae",
    corridor_t_stat_id="jtt_cave_corridor_t",
    corridor_cross_mesh="omwdg\\cave_corridor_cross.dae",
    corridor_cross_stat_id="jtt_cave_corridor_cross",
)

# Tile pieces reused for corridor sections between rooms
cave_corridor_tiles = TileSet(
    name="cave",
    tile_size=256.0,
    room_height=256.0,
    tiles={
        "floor":   TileDef(mesh="omwdg\\cave_floor.dae",   stat_id="jtt_cave_floor"),
        "wall":    TileDef(mesh="omwdg\\cave_wall.dae",    stat_id="jtt_cave_wall"),
        "corner":  TileDef(mesh="omwdg\\cave_corner.dae",  stat_id="jtt_cave_corner"),
        "pillar":  TileDef(mesh="omwdg\\cave_pillar.dae",  stat_id="jtt_cave_pillar"),
        "doorway": TileDef(mesh="omwdg\\cave_doorway.dae", stat_id="jtt_cave_doorway"),
        "ceiling": TileDef(
            mesh="omwdg\\cave_ceiling.dae",
            stat_id="jtt_cave_ceiling",
            z_offset=256.0,
        ),
    },
)
