from dataclasses import dataclass
import math

# Rotation around Z-axis (yaw) in radians for each wall/corner direction
WALL_ROTATIONS: dict[str, float] = {
    "wall_n": 0.0,
    "wall_e": math.pi / 2,
    "wall_s": math.pi,
    "wall_w": 3 * math.pi / 2,
    "corner_ne": 0.0,
    "corner_se": math.pi / 2,
    "corner_sw": math.pi,
    "corner_nw": 3 * math.pi / 2,
}

# Map directional tile type to its base type (for TileSet lookup)
BASE_TILE: dict[str, str] = {
    "floor": "floor",
    "wall_n": "wall", "wall_s": "wall", "wall_e": "wall", "wall_w": "wall",
    "corner_ne": "corner", "corner_se": "corner",
    "corner_sw": "corner", "corner_nw": "corner",
    "pillar": "pillar",
    "doorway": "doorway",
    "ceiling": "ceiling",
}


@dataclass
class TileDef:
    mesh: str        # e.g. "omwdg\\cave_floor.dae" — no meshes\ prefix
    stat_id: str     # STAT record_id e.g. "jtt_cave_floor"
    scale: float = 1.0
    z_offset: float = 0.0  # for ceiling tiles: set to room_height


@dataclass
class TileSet:
    name: str
    tile_size: float    # metres, default 4.0
    room_height: float  # metres, default 3.0
    # Keys: "floor", "wall", "corner", "pillar", "doorway", "ceiling"
    tiles: dict[str, TileDef]

    def get_tile(self, tile_type: str) -> TileDef:
        """Resolve directional type (wall_n) to base TileDef."""
        if tile_type not in BASE_TILE:
            raise ValueError(f"Unknown tile type {tile_type!r}. Valid types: {sorted(BASE_TILE)}")
        base = BASE_TILE[tile_type]
        return self.tiles[base]
