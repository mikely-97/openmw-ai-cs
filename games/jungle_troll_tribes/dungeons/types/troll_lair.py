# games/jungle_troll_tribes/dungeons/types/troll_lair.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[5] / "omwtools"))
from omwtools.dungeons.dungeon_spec import DungeonSpec

troll_lair = DungeonSpec(
    name="troll_lair", game_prefix="jtt", tileset="cave",
    room_count=(6, 12), room_size=(4, 7), pool_size=3,
    exterior_return_pos={"cell": "", "x": 4096, "y": 4096, "z": 200},
    creature_pool=["jtt_troll_warrior", "jtt_troll_shaman"],
    creatures_per_room=(1, 3),
    loot_containers=["jtt_loot_medium", "jtt_loot_large"],
    loot_per_room=(0, 2),
)
