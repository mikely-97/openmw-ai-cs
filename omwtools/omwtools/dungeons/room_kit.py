# omwtools/omwtools/dungeons/room_kit.py
from dataclasses import dataclass


@dataclass
class RoomVariant:
    mesh: str      # e.g. "omwdg\\cave_room_a.dae"  (no meshes\ prefix)
    stat_id: str   # e.g. "jtt_cave_room_a"


@dataclass
class RoomKit:
    name: str
    tile_size: float         # corridor / boundary tile size (e.g. 256.0)
    room_tiles: int          # rooms are room_tiles × room_tiles tiles wide (e.g. 4)
    room_height: float       # room height in world units (e.g. 256.0)
    variants: list[RoomVariant]
    corridor_mesh: str       # e.g. "omwdg\\cave_corridor.dae"
    corridor_stat_id: str    # e.g. "jtt_cave_corridor"
    door_cap_mesh: str = ""          # flat panel to seal unused doorways
    door_cap_stat_id: str = ""

    @property
    def room_size(self) -> float:
        """Room footprint in world units."""
        return self.tile_size * self.room_tiles
