# games/jungle_troll_tribes/dungeons/registry.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3] / "omwtools"))

from omwtools.dungeons.tile_spec import TileSet
from omwtools.dungeons.dungeon_spec import DungeonSpec
from .tilesets.cave import cave
from .types.bear_den import bear_den
from .types.spider_cave import spider_cave
from .types.troll_lair import troll_lair

TILESETS: dict[str, TileSet] = {"cave": cave}
DUNGEON_TYPES: dict[str, DungeonSpec] = {
    "bear_den": bear_den,
    "spider_cave": spider_cave,
    "troll_lair": troll_lair,
}
