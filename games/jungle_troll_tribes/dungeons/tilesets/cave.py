# games/jungle_troll_tribes/dungeons/tilesets/cave.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[4] / "omwtools"))

from omwtools.dungeons.tile_spec import TileSet, TileDef

cave = TileSet(
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
