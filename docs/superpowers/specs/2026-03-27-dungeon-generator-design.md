# Procedural Dungeon Generator — Design Spec

**Date:** 2026-03-27
**Project:** openmw-ai-cs / omwtools
**Status:** Approved

---

## Overview

A procedural dungeon generator integrated into the `omwtools` CLI. Generates interior CELL records (rooms, corridors, doors) from a parameterised spec, outputs JSON records and a compiled `.omwaddon`. Designed to be game-agnostic: all game-specific content (mesh IDs, creature pools, loot tables) is defined in per-game config files.

Supports two usage modes:
- **Pre-authored dungeons** — generate once, polish, bake into the content file (boss dungeons)
- **Random-entry shelters** — generate a pool of variants pre-baked into a `.omwaddon`; Lua picks a variant and populates it with loot/creatures at runtime each time the player enters

---

## Architecture

### Repository layout

```
omwtools/
  dungeons/
    generator.py      ← room-and-corridor layout algorithm → DungeonLayout
    tile_spec.py      ← TileSet + TileDef dataclasses; TILESET_REGISTRY
    dungeon_spec.py   ← DungeonSpec dataclass
    cell_builder.py   ← DungeonLayout + TileSet → CELL record dict + ref list
    pool_builder.py   ← DungeonSpec + TileSet → list[dict] of CELL records (N variants)
    lua_config.py     ← DungeonLayout[] → JTT_Dungeons Lua table string
  cli/main.py         ← adds `dungeon` subcommand group
  dungeons/tilesets/meshes/
    cave/
      omwdg_cave_floor.dae
      omwdg_cave_wall.dae
      omwdg_cave_corner.dae
      omwdg_cave_pillar.dae
      omwdg_cave_doorway.dae
      omwdg_cave_ceiling.dae

games/jungle_troll_tribes/
  dungeons/
    tilesets/
      cave.py         ← JTT cave TileSet instance
    types/
      bear_den.py     ← DungeonSpec: 1-3 rooms, creature/loot tables
      spider_cave.py  ← DungeonSpec: 3-6 rooms
      troll_lair.py   ← DungeonSpec: 6-12 rooms (boss dungeon)
    registry.py       ← TILESETS dict + DUNGEON_TYPES dict for JTT
    gen_dungeon_meshes.py  ← Blender script: generates omwdg_* placeholder .dae files
```

### Game resolution

`--game jtt` resolves to `games/jtt/` (convention: `games/<id>/`). The game directory must contain `dungeons/registry.py` exporting:

```python
TILESETS: dict[str, TileSet]      # name → TileSet instance
DUNGEON_TYPES: dict[str, DungeonSpec]  # name → DungeonSpec instance
```

### Data flow

```
DungeonSpec + TileSet + seed
        ↓ generator.py
    DungeonLayout   (rooms[], corridors[], door_positions[], anchor_positions[])
        ↓ cell_builder.py
    CELL record dict + refs[]   (JSON)
        ↓ pool_builder.py (×N, seeds 0..N-1)
    list[CELL dict]
        ↓ lua_config.py
    JTT_Dungeons Lua string → LUAL record
        ↓ omw import → omw write
    jtt_dungeons.omwaddon
```

### Content file separation

```
jungle_troll_tribes.omwgame   ← base game: items, NPCs, scripts, exterior cells
jtt_dungeons.omwaddon         ← generated: CELL pool + JTT_Dungeons Lua config (LUAL record)
```

`openmw.cfg` loads both in order. Regenerating dungeons (new seed, different params) only requires rebuilding the addon — the base game is untouched.

---

## CLI Interface

```bash
# Generate pool of 8 bear_den variants (seeds 0-7)
omw dungeon generate --game jtt --type bear_den --count 8 \
    --output records/dungeons/ --addon jtt_dungeons.omwaddon

# Generate single named boss dungeon
omw dungeon generate --game jtt --type troll_lair --count 1 --seed 42 \
    --output records/dungeons/ --addon jtt_dungeons.omwaddon
```

The command also:
- Copies any missing `omwdg_*` tile meshes to `games/<id>/meshes/omwdg/` (never overwrites)
- Writes the `JTT_Dungeons` Lua config as a LUAL record into the addon

---

## Layout Algorithm

**Room-and-corridor** (parameterised by DungeonSpec):

1. Place N non-overlapping rooms (random size within spec bounds) on a tile grid
2. Sort rooms by centre position (left-to-right)
3. Connect each room to the next with an L-shaped corridor (horizontal then vertical)
4. Mark corridor–room intersections as doorway tiles
5. Fill grid:
   - Floor tiles inside rooms and corridors
   - Wall/corner tiles on room and corridor boundaries
   - Pillar tiles at isolated solid corners
   - **Ceiling tiles** placed above every floor tile at `z = room_height` (one ceiling per floor tile, same x/y position, z_offset = room_height from TileSet)
6. Record one **anchor position** (world x/y/z) at the centre of each room — exported into the Lua config, not placed as an in-world ref

Reproducible: same `DungeonSpec` + `seed` always produces the same layout.

### Entrance and exit placement

- **Entrance**: first room (index 0) contains a pre-placed ACTI ref with id `<game_prefix>_dungeon_entrance` at the room centre. The exterior ACTI activator (e.g. `jtt_bear_den`) teleports the player to the dungeon cell's entrance position.
- **Exit**: last room contains a pre-placed ACTI ref with id `<game_prefix>_dungeon_exit` at the room centre. Activating it teleports the player back to the exterior entrance coords (stored in the Lua config per variant).

`game_prefix` is defined on `DungeonSpec` (e.g. `"jtt"`).

---

## Tile Spec

### Vocabulary

All tiles are **4m × 4m** footprint. Room height: **3m**.

| Tile type | Mesh | Description |
|---|---|---|
| `floor` | `omwdg_cave_floor.dae` | Walkable square |
| `wall_n/s/e/w` | `omwdg_cave_wall.dae` (rotated) | Wall on given face |
| `corner_ne/nw/se/sw` | `omwdg_cave_corner.dae` (rotated) | Convex corner |
| `pillar` | `omwdg_cave_pillar.dae` | Solid impassable block |
| `doorway` | `omwdg_cave_doorway.dae` | Corridor opening |
| `ceiling` | `omwdg_cave_ceiling.dae` | Placed at z=room_height, flipped normals |

Walls are separate STAT refs on floor tile edges — not baked into the floor mesh. Enables per-theme art replacement without touching the generator.

**Wall rotation convention:** `wall_n` = 0°, `wall_e` = 90°, `wall_s` = 180°, `wall_w` = 270°, all rotated around the Z axis (yaw). `corner_ne` = 0°, `corner_se` = 90°, `corner_sw` = 180°, `corner_nw` = 270°.

**Corridor height:** corridors share `room_height` — ceiling tiles are placed at `z = room_height` for both rooms and corridors.

**Interior CELL ambient settings:** generated CELLs use `ambient=128, sunlight=0, fog=0, fog_density=0` (dim torchlight feel). No water. These are written as CELL header fields by `cell_builder.build()`.

### TileSet dataclass

```python
@dataclass
class TileDef:
    mesh: str           # e.g. "omwdg\\cave_floor.dae" — no meshes\ prefix
    scale: float = 1.0
    z_offset: float = 0.0   # used for ceiling tiles (= room_height)

@dataclass
class TileSet:
    name: str
    tile_size: float    # metres, default 4.0
    room_height: float  # metres, default 3.0
    tiles: dict[str, TileDef]
```

### Mesh path convention

STAT `mesh` fields use the path as deployed: `"omwdg\\cave_floor.dae"`. OpenMW auto-prepends `meshes/`, so the full resolved path is `meshes/omwdg/cave_floor.dae`. Files are deployed to `games/<id>/meshes/omwdg/`.

### Placeholder mesh spec

| Mesh | Geometry | Dimensions |
|---|---|---|
| `omwdg_cave_floor.dae` | flat plane | 4m × 4m |
| `omwdg_cave_wall.dae` | vertical plane | 4m wide × 3m tall |
| `omwdg_cave_corner.dae` | L-shaped vertical plane | 4m × 4m footprint |
| `omwdg_cave_pillar.dae` | box | 0.5m × 0.5m × 3m |
| `omwdg_cave_doorway.dae` | arch frame | 2m wide × 3m tall opening in 4m panel |
| `omwdg_cave_ceiling.dae` | flat plane | 4m × 4m, flipped normals |

Generated by `gen_dungeon_meshes.py` (Blender Python), same pattern as existing `gen_meshes.py`.

### Tile mesh deployment

- Canonical source: `omwtools/dungeons/tilesets/meshes/cave/`
- `omw dungeon generate` auto-copies missing `omwdg_*` files to `games/<id>/meshes/omwdg/`
- **Never overwrites** existing files — allows artists to replace placeholders

---

## DungeonSpec Dataclass

```python
@dataclass
class DungeonSpec:
    name: str
    game_prefix: str                    # e.g. "jtt" — used for cell IDs and entrance/exit ref IDs
    tileset: str                        # key in game's TILESETS registry
    room_count: tuple[int, int]         # (min, max)
    room_size: tuple[int, int]          # (min, max) in tiles
    pool_size: int                      # variants to pre-generate
    exterior_return_pos: dict           # where to teleport player on exit, e.g.:
                                        # {"cell": "", "x": 4096, "y": 4096, "z": 200}
                                        # "cell" = "" means default exterior cell
    # Runtime population (written to Lua config)
    creature_pool: list[str]            # CREA/NPC_ record IDs
    creatures_per_room: tuple[int, int]
    loot_containers: list[str]          # CONT record IDs
    loot_per_room: tuple[int, int]
```

Cell IDs are derived as `<game_prefix>_<name>_<index>` (e.g. `jtt_bear_den_0` .. `jtt_bear_den_7`).

Example (`bear_den.py`):
```python
bear_den = DungeonSpec(
    name="bear_den",
    game_prefix="jtt",
    tileset="cave",
    room_count=(1, 3),
    room_size=(3, 5),
    pool_size=8,
    exterior_return_pos={"cell": "", "x": 4096, "y": 4096, "z": 200},
    creature_pool=["jtt_bear", "jtt_wolf"],
    creatures_per_room=(1, 2),
    loot_containers=["jtt_loot_small", "jtt_loot_medium"],
    loot_per_room=(0, 1),
)
```

---

## Module Interfaces

### generator.py

```python
def generate(spec: DungeonSpec, seed: int) -> DungeonLayout:
    """
    Run the room-and-corridor algorithm with the given seed.
    Returns a DungeonLayout with rooms[], corridors[], anchor_positions[],
    entrance_pos, and exit_pos. Deterministic: same spec + seed → same layout.
    """
```

### cell_builder.py

```python
def build(layout: DungeonLayout, tileset: TileSet, cell_id: str) -> dict:
    """
    Convert an abstract DungeonLayout into an omwtools CELL record dict.
    Tile positions are converted to world coordinates using tileset.tile_size.
    Walls are placed as STAT refs on floor tile boundaries.
    Ceilings placed above every floor tile at z = tileset.room_height.
    Entrance ACTI ref placed at layout.rooms[0].centre.
    Exit ACTI ref placed at layout.rooms[-1].centre.
    Returns a single dict with rec_type="CELL" and a refs[] list.
    """
```

### pool_builder.py

```python
def build_pool(spec: DungeonSpec, tileset: TileSet) -> list[dict]:
    """
    Generate spec.pool_size CELL record dicts, one per seed (0..pool_size-1).
    Each dict is a valid omwtools JSON record ready for omw import.
    Returns list in seed order.
    """
```

Internally: `generator.generate(spec, seed)` → `cell_builder.build(layout, tileset, cell_id)` for each seed, where `cell_id = f"{spec.game_prefix}_{spec.name}_{seed}"`.

---

## Lua Runtime Populator

### Lua config (auto-generated LUAL record in addon)

Anchor positions are exported at generation time — Lua uses known world coordinates rather than iterating cell contents at runtime.

```lua
-- Auto-generated by omw dungeon generate — do not edit
JTT_Dungeons = {
  bear_den = {
    variants = {
      {
        cell_id = "jtt_bear_den_0",
        entrance_pos = {x=8.0, y=8.0, z=0.0},   -- world coords inside cell
        exit_exterior = {cell="", x=4096, y=4096, z=200},  -- exterior return point
        anchors = {{x=8.0, y=8.0, z=0.0}, {x=24.0, y=8.0, z=0.0}},  -- room centres
      },
      -- ... variants 1-7
    },
    creatures = {"jtt_bear", "jtt_wolf"},
    creatures_per_room = {1, 2},
    containers = {"jtt_loot_small", "jtt_loot_medium"},
    loot_per_room = {0, 1},
  },
}
```

### Entry/exit flow

```
player activates jtt_bear_den ACTI (exterior)
  → JTT_EnterDungeon(type="bear_den")
      → pick random variant from JTT_Dungeons["bear_den"].variants
      → core.teleportToCell(player, variant.cell_id, variant.entrance_pos)
      → JTT_PopulateDungeon(variant, type)
          → for each anchor in variant.anchors:
              → world.createObject(random creature, pos=anchor)  [tagged JTT_DungeonSpawned]
              → maybe world.createObject(random container, pos=anchor+offset)

player activates jtt_dungeon_exit ACTI (inside dungeon, last room)
  → JTT_ExitDungeon(variant)
      → despawn all JTT_DungeonSpawned objects in variant.cell_id
      → core.teleportToCell(player, variant.exit_exterior.cell, variant.exit_exterior pos)
```

---

## Testing Strategy

- **Unit tests** (`omwtools/tests/test_dungeon_generator.py`):
  - Same seed + spec → identical layout
  - Room count within spec bounds
  - All rooms connected (BFS from room 0 reaches all rooms)
  - No out-of-bounds tile refs
  - Anchor count equals room count
  - Ceiling tile count equals floor tile count
- **Integration test**: `generate → import → write → omw load` roundtrip produces valid CELL records
- **Manual test**: load `jtt_dungeons.omwaddon` in OpenMW, enter bear den, verify geometry renders and Lua populates creatures/loot

---

## Out of Scope

- Trap mechanics
- Multi-level dungeons (stairs between floors)
- Named room types beyond anchor-based population (e.g. dedicated boss rooms — can be added later via DungeonSpec extension)
- Runtime CELL creation (not possible in OpenMW Lua)
