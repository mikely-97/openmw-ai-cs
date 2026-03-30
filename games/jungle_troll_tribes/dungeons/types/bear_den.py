# games/jungle_troll_tribes/dungeons/types/bear_den.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[4] / "omwtools"))
from omwtools.dungeons.dungeon_spec import DungeonSpec

bear_den = DungeonSpec(
    name="bear_den", game_prefix="jtt", tileset="cave_roomkit",
    room_count=(2, 4), room_size=(4, 4), pool_size=8,
    exterior_return_pos={"cell": "", "x": 4096, "y": 4096, "z": 210},
    creature_pool=["jtt_bear", "jtt_wolf"],
    creatures_per_room=(1, 2),
    loot_containers=["jtt_loot_small", "jtt_loot_medium"],
    loot_per_room=(0, 1),
)
