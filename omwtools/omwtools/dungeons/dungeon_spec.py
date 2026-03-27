from dataclasses import dataclass


@dataclass
class Room:
    x: int   # tile-grid top-left col
    y: int   # tile-grid top-left row
    w: int   # width in tiles
    h: int   # height in tiles

    @property
    def centre_tile(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def room_tiles(self) -> list[tuple[int, int]]:
        """All tile-grid positions inside this room."""
        return [
            (self.x + dx, self.y + dy)
            for dx in range(self.w)
            for dy in range(self.h)
        ]

    def overlaps(self, other: "Room", margin: int = 1) -> bool:
        return not (
            self.x + self.w + margin <= other.x
            or other.x + other.w + margin <= self.x
            or self.y + self.h + margin <= other.y
            or other.y + other.h + margin <= self.y
        )


@dataclass
class DungeonLayout:
    spec: "DungeonSpec"
    seed: int
    rooms: list[Room]
    floor_tiles: set[tuple[int, int]]
    # Tiles that are floor ONLY because of corridor carving (not part of any room).
    # Used to detect doorway positions at corridor-room boundaries.
    corridor_tiles: set[tuple[int, int]]
    # (tx, ty) → tile_type string (wall_n, corner_ne, pillar, doorway, etc.)
    boundary_tiles: dict[tuple[int, int], str]
    # Tile-grid anchor per room centre — cell_builder converts to world coords
    anchor_tiles: list[tuple[int, int]]
    entrance_tile: tuple[int, int]
    exit_tile: tuple[int, int]


@dataclass
class DungeonSpec:
    name: str
    game_prefix: str           # e.g. "jtt"
    tileset: str               # key in game TILESETS registry
    room_count: tuple[int, int]
    room_size: tuple[int, int] # (min, max) in tiles
    pool_size: int
    exterior_return_pos: dict[str, object]  # {"cell": "", "x": 4096, "y": 4096, "z": 200}
    creature_pool: list[str]
    creatures_per_room: tuple[int, int]
    loot_containers: list[str]
    loot_per_room: tuple[int, int]
