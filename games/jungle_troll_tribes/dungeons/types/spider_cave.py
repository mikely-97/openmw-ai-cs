# games/jungle_troll_tribes/dungeons/types/spider_cave.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[4] / "omwtools"))
from omwtools.dungeons.dungeon_spec import DungeonSpec

spider_cave = DungeonSpec(
    name="spider_cave", game_prefix="jtt", tileset="cave",
    room_count=(3, 6), room_size=(3, 6), pool_size=8,
    exterior_return_pos={"cell": "", "x": 4096, "y": 4096, "z": 210},
    creature_pool=["jtt_spider"],
    creatures_per_room=(2, 3),
    loot_containers=["jtt_loot_small", "jtt_loot_medium"],
    loot_per_room=(0, 1),
)
