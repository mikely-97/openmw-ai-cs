# games/jungle_troll_tribes/dungeons/mesh_standards.py
"""
Standard connection interface for all dungeon mesh pieces.

Every connectable face must expose a rectangular opening of:
  width  = DOOR_W = TILE  = 256  (one full tile)
  height = DOOR_H = H     = 256  (full room height — NO lintel)

The opening is centred on the tile/doorway mid-point.
The inner wall face on each side of the opening is at exactly ±HALF_OPEN
from that centre.

Any two adjacent pieces (room↔corridor, corridor↔corridor, room↔door_cap)
must share the same interface — otherwise the junction will show void.
"""

TILE      = 256.0   # corridor / boundary tile size
ROOM      = 1024.0  # room footprint (4 × TILE, = 4 tiles wide/tall)
H         = 256.0   # room + corridor height
WALL_T    = 24.0    # wall / cap thickness

DOOR_W    = TILE    # connection opening width   (256) — one tile
DOOR_H    = H       # connection opening height  (256) — full height, no lintel
HALF_OPEN = TILE / 2  # = 128 — inner-face offset from opening centre
