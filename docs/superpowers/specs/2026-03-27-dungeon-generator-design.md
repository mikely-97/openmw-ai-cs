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
    tile_spec.py      ← TileSet + TileDef dataclasses
    dungeon_spec.py   ← DungeonSpec dataclass
    cell_builder.py   ← DungeonLayout + TileSet → CELL record dict + ref list
    pool_builder.py   ← generates N variants → list of CELL dicts
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
      cave.py         ← JTT cave TileSet (mesh IDs, dimensions)
    types/
      bear_den.py     ← DungeonSpec: 1-3 rooms, creature/loot tables
      spider_cave.py  ← DungeonSpec: 3-6 rooms
      troll_lair.py   ← DungeonSpec: 6-12 rooms (boss dungeon)
    gen_dungeon_meshes.py  ← Blender script: generates omwdg_* placeholder .dae files
```

### Data flow

```
DungeonSpec + TileSet + seed
        ↓ generator.py
    DungeonLayout   (rooms[], corridors[], door_positions[], anchor_positions[])
        ↓ cell_builder.py
    CELL record dict + refs[]   (JSON)
        ↓ pool_builder.py (×N)
    records/dungeons/*.json
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
- Copies any missing `omwdg_*` tile meshes to the target game's `meshes/` directory (never overwrites existing files, allowing art replacement)
- Writes a companion `JTT_Dungeons` Lua config as a LUAL record into the addon

---

## Layout Algorithm

**Room-and-corridor** (parameterised by DungeonSpec):

1. Place N non-overlapping rooms (random size within spec bounds) on a tile grid
2. Sort rooms by centre position (left-to-right)
3. Connect each room to the next with an L-shaped corridor (horizontal then vertical)
4. Mark corridor–room intersections as doorway tiles
5. Fill grid: floor tiles inside rooms/corridors, wall/corner tiles on boundaries, pillar tiles at isolated solid corners
6. Place one invisible anchor ACTI ref at each room centre (used by Lua populator for creature/loot placement)

Reproducible: same `DungeonSpec` + `seed` always produces the same layout.

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
| `ceiling` | `omwdg_cave_ceiling.dae` | Caps room (flipped normals) |

Walls are separate STAT refs on floor tile edges — not baked into the floor mesh. Enables per-theme art replacement without touching the generator.

### TileSet dataclass

```python
@dataclass
class TileDef:
    mesh: str           # e.g. "omwdg\\cave_floor.dae" — no meshes\ prefix
    scale: float = 1.0
    z_offset: float = 0.0

@dataclass
class TileSet:
    name: str
    tile_size: float    # metres, default 4.0
    room_height: float  # metres, default 3.0
    tiles: dict[str, TileDef]
```

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
- `omw dungeon generate` auto-copies missing `omwdg_*` files to `<game>/meshes/omwdg/`
- **Never overwrites** existing files — allows artists to replace placeholders

---

## DungeonSpec Dataclass

```python
@dataclass
class DungeonSpec:
    name: str
    tileset: str                        # references a TileSet by name
    room_count: tuple[int, int]         # (min, max)
    room_size: tuple[int, int]          # (min, max) in tiles
    pool_size: int                      # variants to pre-generate
    # Runtime population (written to Lua config)
    creature_pool: list[str]            # CREA/NPC_ record IDs
    creatures_per_room: tuple[int, int]
    loot_containers: list[str]          # CONT record IDs
    loot_per_room: tuple[int, int]
```

Example (`bear_den.py`):
```python
bear_den = DungeonSpec(
    name="bear_den",
    tileset="cave",
    room_count=(1, 3),
    room_size=(3, 5),
    pool_size=8,
    creature_pool=["jtt_bear", "jtt_wolf"],
    creatures_per_room=(1, 2),
    loot_containers=["jtt_loot_small", "jtt_loot_medium"],
    loot_per_room=(0, 1),
)
```

---

## Lua Runtime Populator

### Lua config (auto-generated LUAL record in addon)

```lua
-- Auto-generated by omw dungeon generate — do not edit
JTT_Dungeons = {
  bear_den = {
    variants = {"jtt_bear_den_0", "jtt_bear_den_1", ..., "jtt_bear_den_7"},
    creatures = {"jtt_bear", "jtt_wolf"},
    creatures_per_room = {1, 2},
    containers = {"jtt_loot_small", "jtt_loot_medium"},
    loot_per_room = {0, 1},
  },
  -- ... other types
}
```

### Entry/exit flow

```
player activates bear_den entrance ACTI
  → JTT_EnterDungeon(type="bear_den")
      → pick random variant cell id from JTT_Dungeons[type].variants
      → core.teleportToCell(player, cell_id, entrance_pos)
      → JTT_PopulateDungeon(cell_id, type)
          → iterate jtt_dungeon_anchor refs in cell
          → per anchor: spawn N creatures + maybe spawn loot container
          → tag spawned objects JTT_DungeonSpawned=true

player activates exit marker inside dungeon
  → JTT_ExitDungeon(cell_id)
      → despawn all JTT_DungeonSpawned objects in cell
      → core.teleportToCell(player, exterior_cell, entrance_coords)
```

### Room anchor points

Each generated CELL contains one invisible **ACTI ref** with id `jtt_dungeon_anchor` at each room centre. The Lua populator iterates these refs to place creatures and loot — no hardcoded coordinates in Lua.

---

## Testing Strategy

- **Unit tests** (`omwtools/tests/test_dungeon_generator.py`):
  - Same seed + spec → identical layout
  - Room count within spec bounds
  - All rooms connected (BFS from room 0 reaches all rooms)
  - No out-of-bounds tile refs
- **Integration test**: `generate → import → write → omw load` roundtrip produces valid CELL records
- **Manual test**: load `jtt_dungeons.omwaddon` in OpenMW, enter bear den, verify geometry renders and Lua populates creatures/loot

---

## Out of Scope

- Trap mechanics
- Multi-level dungeons (stairs between floors)
- Named room types beyond anchor-based population (e.g. dedicated boss rooms — can be added later via DungeonSpec extension)
- Runtime CELL creation (not possible in OpenMW Lua)
