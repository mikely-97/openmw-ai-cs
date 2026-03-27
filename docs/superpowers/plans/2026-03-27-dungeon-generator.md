# Procedural Dungeon Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `omw dungeon generate` CLI command that produces interior CELL records (tile-based rooms + corridors) from a parameterised spec, outputs a pool of variants as a `.omwaddon`, with a companion Lua config enabling runtime content population.

**Architecture:** Game-agnostic generator core in `omwtools/omwtools/dungeons/` — takes `DungeonSpec` + `TileSet` + seed, produces CELL JSON records. Layout algorithm works in tile-grid coordinates; `cell_builder` converts to world coords using `tileset.tile_size`. Game-specific configs (JTT) live in `games/jungle_troll_tribes/dungeons/`. Lua runtime populator in `global.lua` reads anchor positions from a generated `dungeon_config.lua` and spawns creatures/loot on cell entry.

**Tech Stack:** Python 3.10+, dataclasses, argparse (existing CLI pattern), pytest, Blender Python (mesh gen only)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `omwtools/omwtools/dungeons/__init__.py` | Create | Package marker |
| `omwtools/omwtools/dungeons/tile_spec.py` | Create | `TileDef`, `TileSet` dataclasses |
| `omwtools/omwtools/dungeons/dungeon_spec.py` | Create | `DungeonSpec`, `Room`, `DungeonLayout` dataclasses |
| `omwtools/omwtools/dungeons/generator.py` | Create | `generate(spec, seed) → DungeonLayout` |
| `omwtools/omwtools/dungeons/cell_builder.py` | Create | `build(layout, tileset, cell_id) → dict`, `stat_records(tileset) → list[dict]` |
| `omwtools/omwtools/dungeons/pool_builder.py` | Create | `build_pool(spec, tileset, start_seed) → tuple[list[dict], list[DungeonLayout]]` |
| `omwtools/omwtools/dungeons/lua_config.py` | Create | `generate_lua_config(type_name, spec, layouts) → str` |
| `omwtools/omwtools/dungeons/deployer.py` | Create | `deploy_tiles(tileset_name, game_dir)` — copies missing `omwdg_*` meshes |
| `omwtools/omwtools/dungeons/tilesets/meshes/cave/` | Create | Placeholder `.dae` files (6 meshes) |
| `omwtools/omwtools/cli/cmd_dungeon.py` | Create | CLI handler for `dungeon generate` |
| `omwtools/omwtools/cli/main.py` | Modify | Add `dungeon` subcommand group |
| `omwtools/tests/unit/test_dungeon_generator.py` | Create | Unit tests for generator + cell_builder + pool_builder |
| `games/jungle_troll_tribes/dungeons/__init__.py` | Create | Package marker |
| `games/jungle_troll_tribes/dungeons/tilesets/__init__.py` | Create | Package marker |
| `games/jungle_troll_tribes/dungeons/tilesets/cave.py` | Create | JTT cave `TileSet` instance |
| `games/jungle_troll_tribes/dungeons/types/__init__.py` | Create | Package marker |
| `games/jungle_troll_tribes/dungeons/types/bear_den.py` | Create | `DungeonSpec`: 1-3 rooms |
| `games/jungle_troll_tribes/dungeons/types/spider_cave.py` | Create | `DungeonSpec`: 3-6 rooms |
| `games/jungle_troll_tribes/dungeons/types/troll_lair.py` | Create | `DungeonSpec`: 6-12 rooms |
| `games/jungle_troll_tribes/dungeons/registry.py` | Create | `TILESETS` + `DUNGEON_TYPES` dicts |
| `games/jungle_troll_tribes/dungeons/gen_dungeon_meshes.py` | Create | Blender Python script: generate 6 placeholder `.dae` files |
| `games/jungle_troll_tribes/scripts/jtt/global.lua` | Modify | Add `JTT_EnterDungeon`, `JTT_PopulateDungeon`, `JTT_ExitDungeon` handlers |

---

## Task 1: Core Datastructures

**Files:**
- Create: `omwtools/omwtools/dungeons/__init__.py`
- Create: `omwtools/omwtools/dungeons/tile_spec.py`
- Create: `omwtools/omwtools/dungeons/dungeon_spec.py`

- [ ] **Step 1: Create the dungeons package**

```python
# omwtools/omwtools/dungeons/__init__.py
# empty
```

- [ ] **Step 2: Write tile_spec.py**

```python
# omwtools/omwtools/dungeons/tile_spec.py
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
        base = BASE_TILE.get(tile_type, tile_type)
        return self.tiles[base]
```

- [ ] **Step 3: Write dungeon_spec.py**

Note: `DungeonLayout` stores anchor positions and entrance/exit as **tile-grid coordinates** `(tx, ty)`, not world coordinates. `cell_builder.build()` converts to world coords using `tileset.tile_size`.

```python
# omwtools/omwtools/dungeons/dungeon_spec.py
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
    exterior_return_pos: dict  # {"cell": "", "x": 4096, "y": 4096, "z": 200}
    creature_pool: list[str]
    creatures_per_room: tuple[int, int]
    loot_containers: list[str]
    loot_per_room: tuple[int, int]
```

- [ ] **Step 4: Commit**

```bash
git add omwtools/omwtools/dungeons/
git commit -m "feat: dungeon generator core datastructures (TileSet, DungeonSpec, DungeonLayout)"
```

---

## Task 2: Layout Algorithm (TDD)

**Files:**
- Create: `omwtools/omwtools/dungeons/generator.py`
- Create: `omwtools/tests/unit/test_dungeon_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# omwtools/tests/unit/test_dungeon_generator.py
import pytest
from collections import deque
from omwtools.dungeons.dungeon_spec import DungeonSpec, DungeonLayout
from omwtools.dungeons.tile_spec import TileSet, TileDef
from omwtools.dungeons.generator import generate


SPEC = DungeonSpec(
    name="test_cave",
    game_prefix="tst",
    tileset="cave",
    room_count=(2, 4),
    room_size=(3, 5),
    pool_size=1,
    exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
    creature_pool=[],
    creatures_per_room=(0, 0),
    loot_containers=[],
    loot_per_room=(0, 0),
)

TILESET = TileSet(
    name="cave",
    tile_size=4.0,
    room_height=3.0,
    tiles={
        "floor":   TileDef(mesh="omwdg\\cave_floor.dae",   stat_id="tst_cave_floor"),
        "wall":    TileDef(mesh="omwdg\\cave_wall.dae",    stat_id="tst_cave_wall"),
        "corner":  TileDef(mesh="omwdg\\cave_corner.dae",  stat_id="tst_cave_corner"),
        "pillar":  TileDef(mesh="omwdg\\cave_pillar.dae",  stat_id="tst_cave_pillar"),
        "doorway": TileDef(mesh="omwdg\\cave_doorway.dae", stat_id="tst_cave_doorway"),
        "ceiling": TileDef(
            mesh="omwdg\\cave_ceiling.dae",
            stat_id="tst_cave_ceiling",
            z_offset=3.0,
        ),
    },
)


def test_deterministic():
    layout1 = generate(SPEC, seed=0)
    layout2 = generate(SPEC, seed=0)
    assert layout1.floor_tiles == layout2.floor_tiles
    assert layout1.rooms == layout2.rooms


def test_different_seeds_differ():
    layout0 = generate(SPEC, seed=0)
    layout1 = generate(SPEC, seed=1)
    assert layout0.floor_tiles != layout1.floor_tiles or layout0.rooms != layout1.rooms


def test_room_count_in_spec_bounds():
    for seed in range(10):
        layout = generate(SPEC, seed=seed)
        assert SPEC.room_count[0] <= len(layout.rooms) <= SPEC.room_count[1]


def test_room_size_in_spec_bounds():
    for seed in range(10):
        layout = generate(SPEC, seed=seed)
        for room in layout.rooms:
            assert SPEC.room_size[0] <= room.w <= SPEC.room_size[1]
            assert SPEC.room_size[0] <= room.h <= SPEC.room_size[1]


def test_all_rooms_connected():
    """BFS from first room centre must reach all other room centres via floor tiles."""
    layout = generate(SPEC, seed=42)
    if len(layout.rooms) < 2:
        return
    start = layout.rooms[0].centre_tile
    visited: set[tuple[int, int]] = set()
    queue = deque([start])
    while queue:
        tx, ty = queue.popleft()
        if (tx, ty) in visited:
            continue
        visited.add((tx, ty))
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nb = (tx + dx, ty + dy)
            if nb in layout.floor_tiles and nb not in visited:
                queue.append(nb)
    for room in layout.rooms:
        assert room.centre_tile in visited, f"Room at {room.centre_tile} not reachable"


def test_anchor_count_equals_room_count():
    layout = generate(SPEC, seed=7)
    assert len(layout.anchor_tiles) == len(layout.rooms)


def test_entrance_and_exit_tiles_set():
    layout = generate(SPEC, seed=0)
    assert layout.entrance_tile == layout.rooms[0].centre_tile
    assert layout.exit_tile == layout.rooms[-1].centre_tile


def test_no_overlapping_rooms():
    for seed in range(10):
        layout = generate(SPEC, seed=seed)
        for i, r1 in enumerate(layout.rooms):
            for j, r2 in enumerate(layout.rooms):
                if i != j:
                    assert not r1.overlaps(r2, margin=0), \
                        f"Rooms {i} and {j} overlap at seed {seed}"


def test_corridor_tiles_not_in_any_room():
    """Corridor tiles must be floor tiles not belonging to any room."""
    layout = generate(SPEC, seed=3)
    all_room_tiles: set[tuple[int, int]] = set()
    for room in layout.rooms:
        all_room_tiles.update(room.room_tiles())
    # corridor_tiles should not overlap with room tiles
    assert layout.corridor_tiles.isdisjoint(all_room_tiles), \
        "corridor_tiles overlaps with room tile(s)"


def test_doorway_tiles_present_when_rooms_gt_1():
    """There must be at least one doorway boundary tile when corridors connect rooms."""
    layout = generate(SPEC, seed=0)
    if len(layout.rooms) < 2:
        return
    doorway_tiles = [t for t, tt in layout.boundary_tiles.items() if tt == "doorway"]
    assert len(doorway_tiles) > 0, "No doorway tiles generated despite multiple rooms"
```

- [ ] **Step 2: Run to verify all fail**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest tests/unit/test_dungeon_generator.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` (generator.py doesn't exist)

- [ ] **Step 3: Implement generator.py**

```python
# omwtools/omwtools/dungeons/generator.py
import random
from .dungeon_spec import DungeonSpec, DungeonLayout, Room


def generate(spec: DungeonSpec, seed: int) -> DungeonLayout:
    rng = random.Random(seed)
    rooms = _place_rooms(spec, rng)

    # Collect all room floor tiles
    room_tiles: set[tuple[int, int]] = set()
    for room in rooms:
        room_tiles.update(room.room_tiles())

    # Carve corridors — returns only the NEW tiles added (not already room tiles)
    corridor_tiles: set[tuple[int, int]] = set()
    _carve_corridors(rooms, room_tiles, corridor_tiles)

    floor_tiles = room_tiles | corridor_tiles
    boundary_tiles = _compute_boundary(floor_tiles, corridor_tiles)

    anchor_tiles = [r.centre_tile for r in rooms]
    return DungeonLayout(
        spec=spec,
        seed=seed,
        rooms=rooms,
        floor_tiles=floor_tiles,
        corridor_tiles=corridor_tiles,
        boundary_tiles=boundary_tiles,
        anchor_tiles=anchor_tiles,
        entrance_tile=rooms[0].centre_tile,
        exit_tile=rooms[-1].centre_tile,
    )


def _place_rooms(spec: DungeonSpec, rng: random.Random) -> list[Room]:
    count = rng.randint(*spec.room_count)
    rooms: list[Room] = []
    grid_size = max(spec.room_count[1] * spec.room_size[1] * 2, 30)
    max_attempts = 300
    while len(rooms) < count and max_attempts > 0:
        max_attempts -= 1
        w = rng.randint(*spec.room_size)
        h = rng.randint(*spec.room_size)
        x = rng.randint(1, grid_size - w - 1)
        y = rng.randint(1, grid_size - h - 1)
        candidate = Room(x=x, y=y, w=w, h=h)
        if not any(candidate.overlaps(r) for r in rooms):
            rooms.append(candidate)
    rooms.sort(key=lambda r: r.centre_tile[0])
    return rooms


def _carve_corridors(
    rooms: list[Room],
    room_tiles: set[tuple[int, int]],
    corridor_tiles: set[tuple[int, int]],
) -> None:
    """Connect each room to the next with an L-shaped corridor.
    Only adds tiles that are NOT already room tiles to corridor_tiles.
    """
    for i in range(len(rooms) - 1):
        ax, ay = rooms[i].centre_tile
        bx, by = rooms[i + 1].centre_tile
        # Horizontal leg
        for tx in range(min(ax, bx), max(ax, bx) + 1):
            if (tx, ay) not in room_tiles:
                corridor_tiles.add((tx, ay))
        # Vertical leg
        for ty in range(min(ay, by), max(ay, by) + 1):
            if (bx, ty) not in room_tiles:
                corridor_tiles.add((bx, ty))


def _compute_boundary(
    floor_tiles: set[tuple[int, int]],
    corridor_tiles: set[tuple[int, int]],
) -> dict[tuple[int, int], str]:
    """
    For each non-floor tile adjacent to a floor tile, determine its type.
    A boundary tile adjacent to a corridor floor tile at a corridor-room junction
    is classified as "doorway" instead of a plain wall.
    """
    candidates: set[tuple[int, int]] = set()
    for tx, ty in floor_tiles:
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
            nb = (tx + dx, ty + dy)
            if nb not in floor_tiles:
                candidates.add(nb)

    boundary: dict[tuple[int, int], str] = {}
    for tx, ty in candidates:
        n = (tx,   ty-1) in floor_tiles
        s = (tx,   ty+1) in floor_tiles
        e = (tx+1, ty  ) in floor_tiles
        w = (tx-1, ty  ) in floor_tiles
        # Check if any adjacent floor tile is a corridor tile at a room boundary
        # (i.e., the corridor tile is adjacent to a room tile on the far side)
        is_doorway = _is_doorway(tx, ty, floor_tiles, corridor_tiles)
        tile_type = _classify_boundary(n, s, e, w, is_doorway)
        if tile_type:
            boundary[(tx, ty)] = tile_type
    return boundary


def _is_doorway(
    tx: int, ty: int,
    floor_tiles: set[tuple[int, int]],
    corridor_tiles: set[tuple[int, int]],
) -> bool:
    """
    A boundary tile is a doorway if it has exactly one cardinal floor neighbour
    that is a corridor tile (the corridor is entering a room through this position).
    """
    cardinal = [(tx, ty-1), (tx, ty+1), (tx+1, ty), (tx-1, ty)]
    corridor_neighbours = [p for p in cardinal if p in corridor_tiles]
    return len(corridor_neighbours) == 1


def _classify_boundary(n: bool, s: bool, e: bool, w: bool, is_doorway: bool) -> str | None:
    """Return tile type string for a boundary tile, or None if no tile needed."""
    if is_doorway:
        return "doorway"
    if s and not n and not e and not w:
        return "wall_n"
    if n and not s and not e and not w:
        return "wall_s"
    if w and not e and not n and not s:
        return "wall_e"
    if e and not w and not n and not s:
        return "wall_w"
    if s and e and not n and not w:
        return "corner_ne"
    if s and w and not n and not e:
        return "corner_nw"
    if n and e and not s and not w:
        return "corner_se"
    if n and w and not s and not e:
        return "corner_sw"
    if (n or s) and (e or w):
        return "pillar"
    return None
```

- [ ] **Step 4: Run tests**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest tests/unit/test_dungeon_generator.py -v
```
Expected: all 10 tests PASS

- [ ] **Step 5: Run full suite (regression check)**

```bash
poetry run pytest -x -q
```
Expected: all 65 existing + 10 new tests pass

- [ ] **Step 6: Commit**

```bash
git add omwtools/omwtools/dungeons/generator.py omwtools/tests/unit/test_dungeon_generator.py
git commit -m "feat: room-and-corridor dungeon layout algorithm with full test coverage"
```

---

## Task 3: Cell Builder (TDD)

**Files:**
- Create: `omwtools/omwtools/dungeons/cell_builder.py`
- Modify: `omwtools/tests/unit/test_dungeon_generator.py`

The cell builder converts `DungeonLayout` (tile-grid coords) into a CELL JSON dict. It also produces STAT record definitions for all tile types.

**CELL JSON format** (interior cell, matches omwtools `Cell.from_dict` schema):
- `rec_type: "CELL"`, `record_id`, `cell_name` (= `cell_id` — used for `teleportToCell` targeting)
- `cell_flags: 1` (CELL_INTERIOR), `grid_x/y: 0`
- `ambient: int`, `sunlight: int`, `fog: int`, `fog_density: float`
- `refs: list[dict]` where each ref has: `ref_num`, `object_id`, `pos: [x,y,z]`, `rot: [0,0,rot_z]`, plus defaults: `scale: 1.0`, `is_deleted: false`, `is_blocked: false`, `soul: ""`, `owner: ""`, `owner_rank: -1`, `owner_global: ""`, `key_id: ""`, `trap_id: ""`, `enchant_charge: -1.0`, `charge_int: -1`, `lock_level: 0.0`, `dest_pos: null`, `dest_rot: null`, `dest_cell: ""`

- [ ] **Step 1: Write failing tests (append to test file)**

```python
# Append to omwtools/tests/unit/test_dungeon_generator.py

from omwtools.dungeons.cell_builder import build, stat_records


def test_cell_rec_type():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    assert cell["rec_type"] == "CELL"


def test_cell_record_id():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    assert cell["record_id"] == "tst_test_cave_0"


def test_cell_name_equals_record_id():
    """cell_name must equal record_id for predictable teleportToCell targeting."""
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    assert cell["cell_name"] == "tst_test_cave_0"


def test_cell_is_interior():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    assert cell["cell_flags"] & 0x01  # CELL_INTERIOR bit set


def test_floor_ref_count_equals_floor_tiles():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    floor_refs = [r for r in cell["refs"] if r["object_id"] == "tst_cave_floor"]
    assert len(floor_refs) == len(layout.floor_tiles)


def test_ceiling_count_equals_floor_count():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    floor_refs  = [r for r in cell["refs"] if r["object_id"] == "tst_cave_floor"]
    ceiling_refs = [r for r in cell["refs"] if r["object_id"] == "tst_cave_ceiling"]
    assert len(ceiling_refs) == len(floor_refs)


def test_entrance_and_exit_refs_present():
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    ids = {r["object_id"] for r in cell["refs"]}
    assert "tst_dungeon_entrance" in ids
    assert "tst_dungeon_exit" in ids


def test_ref_world_coords_use_tile_size():
    """Floor ref at tile (1,0) should have pos [tile_size, 0, 0]."""
    layout = generate(SPEC, seed=0)
    cell = build(layout, TILESET, "tst_test_cave_0")
    # Pick any floor ref and verify its position is a multiple of tile_size
    floor_refs = [r for r in cell["refs"] if r["object_id"] == "tst_cave_floor"]
    ts = TILESET.tile_size
    for ref in floor_refs:
        assert ref["pos"][0] % ts == pytest.approx(0.0)
        assert ref["pos"][1] % ts == pytest.approx(0.0)


def test_stat_records_returns_one_per_tile_type():
    stats = stat_records(TILESET)
    assert len(stats) == len(TILESET.tiles)
    for s in stats:
        assert s["rec_type"] == "STAT"
        assert s["mesh"].startswith("omwdg\\")
```

- [ ] **Step 2: Verify tests fail**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest tests/unit/test_dungeon_generator.py -v -k "cell or stat" 2>&1 | head -10
```
Expected: `ImportError` for `cell_builder`

- [ ] **Step 3: Implement cell_builder.py**

```python
# omwtools/omwtools/dungeons/cell_builder.py
from .dungeon_spec import DungeonLayout
from .tile_spec import TileSet, WALL_ROTATIONS

_REF_DEFAULTS = {
    "scale": 1.0,
    "is_deleted": False,
    "is_blocked": False,
    "soul": "",
    "owner": "",
    "owner_rank": -1,
    "owner_global": "",
    "key_id": "",
    "trap_id": "",
    "enchant_charge": -1.0,
    "charge_int": -1,
    "lock_level": 0.0,
    "dest_pos": None,
    "dest_rot": None,
    "dest_cell": "",
}


def stat_records(tileset: TileSet) -> list[dict]:
    """Return one STAT record dict per base tile type. Import before CELL records."""
    return [
        {"rec_type": "STAT", "record_id": tile_def.stat_id, "mesh": tile_def.mesh}
        for tile_def in tileset.tiles.values()
    ]


def build(layout: DungeonLayout, tileset: TileSet, cell_id: str) -> dict:
    """
    Convert DungeonLayout (tile-grid coords) to an omwtools CELL record dict.
    Tile-grid coords are multiplied by tileset.tile_size to produce world coords.
    cell_name == cell_id for predictable teleportToCell(cell_id, ...) targeting.
    """
    ts = tileset.tile_size
    prefix = layout.spec.game_prefix
    refs: list[dict] = []
    ref_num = 1

    # Floor tiles
    for tx, ty in sorted(layout.floor_tiles):
        tile_def = tileset.get_tile("floor")
        refs.append(_make_ref(ref_num, tile_def.stat_id, tx * ts, ty * ts, 0.0, 0.0))
        ref_num += 1

    # Ceiling tiles (same x/y, z = room_height)
    for tx, ty in sorted(layout.floor_tiles):
        tile_def = tileset.get_tile("ceiling")
        refs.append(_make_ref(
            ref_num, tile_def.stat_id, tx * ts, ty * ts, tileset.room_height, 0.0
        ))
        ref_num += 1

    # Boundary tiles (walls, corners, pillars, doorways)
    for (tx, ty), tile_type in sorted(layout.boundary_tiles.items()):
        tile_def = tileset.get_tile(tile_type)
        rot_z = WALL_ROTATIONS.get(tile_type, 0.0)
        refs.append(_make_ref(ref_num, tile_def.stat_id, tx * ts, ty * ts, 0.0, rot_z))
        ref_num += 1

    # Entrance ACTI ref at first room centre (world coords)
    etx, ety = layout.entrance_tile
    refs.append(_make_ref(ref_num, f"{prefix}_dungeon_entrance", etx * ts, ety * ts, 0.0, 0.0))
    ref_num += 1

    # Exit ACTI ref at last room centre (world coords)
    xtx, xty = layout.exit_tile
    refs.append(_make_ref(ref_num, f"{prefix}_dungeon_exit", xtx * ts, xty * ts, 0.0, 0.0))

    return {
        "rec_type": "CELL",
        "record_id": cell_id,
        "cell_name": cell_id,          # Must equal record_id for teleportToCell
        "cell_flags": 1,               # CELL_INTERIOR = 0x01
        "grid_x": 0,
        "grid_y": 0,
        "ambient": 0x00808080,         # dim grey ambient (torchlight feel)
        "sunlight": 0,
        "fog": 0,
        "fog_density": 0.0,
        "water_height": None,
        "refs": refs,
    }


def _make_ref(ref_num: int, object_id: str, x: float, y: float, z: float, rot_z: float) -> dict:
    ref = {"ref_num": ref_num, "object_id": object_id, "pos": [x, y, z], "rot": [0.0, 0.0, rot_z]}
    ref.update(_REF_DEFAULTS)
    return ref
```

- [ ] **Step 4: Run cell builder tests**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest tests/unit/test_dungeon_generator.py -v
```
Expected: all 20 tests PASS

- [ ] **Step 5: Run full suite**

```bash
poetry run pytest -x -q
```

- [ ] **Step 6: Commit**

```bash
git add omwtools/omwtools/dungeons/cell_builder.py omwtools/tests/unit/test_dungeon_generator.py
git commit -m "feat: cell builder — DungeonLayout to CELL JSON with full TDD coverage"
```

---

## Task 4: Pool Builder + Lua Config (TDD)

**Files:**
- Create: `omwtools/omwtools/dungeons/pool_builder.py`
- Create: `omwtools/omwtools/dungeons/lua_config.py`
- Modify: `omwtools/tests/unit/test_dungeon_generator.py`

- [ ] **Step 1: Write failing tests (append to test file)**

```python
# Append to omwtools/tests/unit/test_dungeon_generator.py

from omwtools.dungeons.pool_builder import build_pool
from omwtools.dungeons.lua_config import generate_lua_config


def test_pool_builder_cell_count():
    spec = DungeonSpec(
        name="tiny", game_prefix="tst", tileset="cave",
        room_count=(1, 2), room_size=(3, 4), pool_size=3,
        exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
        creature_pool=["tst_bear"], creatures_per_room=(1, 1),
        loot_containers=["tst_chest"], loot_per_room=(0, 1),
    )
    records, layouts = build_pool(spec, TILESET)
    cell_records = [r for r in records if r["rec_type"] == "CELL"]
    assert len(cell_records) == 3
    assert len(layouts) == 3


def test_pool_builder_cell_ids_sequential():
    spec = DungeonSpec(
        name="tiny", game_prefix="tst", tileset="cave",
        room_count=(1, 2), room_size=(3, 4), pool_size=3,
        exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
        creature_pool=[], creatures_per_room=(0, 0),
        loot_containers=[], loot_per_room=(0, 0),
    )
    records, _ = build_pool(spec, TILESET)
    cell_ids = [r["record_id"] for r in records if r["rec_type"] == "CELL"]
    assert cell_ids == ["tst_tiny_0", "tst_tiny_1", "tst_tiny_2"]


def test_pool_builder_start_seed_offset():
    spec = DungeonSpec(
        name="tiny", game_prefix="tst", tileset="cave",
        room_count=(2, 3), room_size=(3, 4), pool_size=1,
        exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
        creature_pool=[], creatures_per_room=(0, 0),
        loot_containers=[], loot_per_room=(0, 0),
    )
    _, layouts_s0 = build_pool(spec, TILESET, start_seed=0)
    _, layouts_s5 = build_pool(spec, TILESET, start_seed=5)
    assert layouts_s0[0].floor_tiles != layouts_s5[0].floor_tiles


def test_lua_config_contains_cell_ids():
    spec = DungeonSpec(
        name="tiny", game_prefix="tst", tileset="cave",
        room_count=(1, 2), room_size=(3, 4), pool_size=2,
        exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
        creature_pool=["tst_bear"], creatures_per_room=(1, 1),
        loot_containers=[], loot_per_room=(0, 0),
    )
    _, layouts = build_pool(spec, TILESET)
    lua = generate_lua_config("tiny", spec, layouts, TILESET)
    assert "tst_tiny_0" in lua
    assert "tst_tiny_1" in lua
    assert "TST_Dungeons" in lua
```

- [ ] **Step 2: Verify tests fail**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest tests/unit/test_dungeon_generator.py -v -k "pool or lua" 2>&1 | head -10
```
Expected: `ImportError`

- [ ] **Step 3: Implement pool_builder.py**

```python
# omwtools/omwtools/dungeons/pool_builder.py
from .dungeon_spec import DungeonSpec, DungeonLayout
from .tile_spec import TileSet
from .generator import generate
from .cell_builder import build, stat_records as get_stat_records


def build_pool(
    spec: DungeonSpec,
    tileset: TileSet,
    start_seed: int = 0,
) -> tuple[list[dict], list[DungeonLayout]]:
    """
    Generate spec.pool_size CELL record dicts starting at start_seed.
    Returns (records, layouts) where records = STAT defs + CELL dicts (import order),
    and layouts carries anchor/position data for lua_config generation.
    """
    stats = get_stat_records(tileset)
    cells: list[dict] = []
    layouts: list[DungeonLayout] = []
    for i in range(spec.pool_size):
        seed = start_seed + i
        cell_id = f"{spec.game_prefix}_{spec.name}_{seed}"
        layout = generate(spec, seed)
        layouts.append(layout)
        cells.append(build(layout, tileset, cell_id))
    return stats + cells, layouts
```

- [ ] **Step 4: Implement lua_config.py**

```python
# omwtools/omwtools/dungeons/lua_config.py
from .dungeon_spec import DungeonSpec, DungeonLayout


def generate_lua_config(
    type_name: str,
    spec: DungeonSpec,
    layouts: list[DungeonLayout],
    tileset: "TileSet",
    start_seed: int = 0,
) -> str:
    """
    Generate a Lua module string defining the dungeon config table.
    Anchor positions are exported as world coords (tile_grid * tileset.tile_size).
    Returns a string suitable for require() from global.lua.
    """
    ts = tileset.tile_size
    cfg_var = f"{spec.game_prefix.upper()}_Dungeons"
    lines = [f"-- Auto-generated by omw dungeon generate — do not edit"]
    lines.append(f"local {cfg_var} = {{")
    lines.append(f"  {type_name} = {{")
    lines.append("    variants = {")

    for i, layout in enumerate(layouts):
        seed = start_seed + i
        cell_id = f"{spec.game_prefix}_{spec.name}_{seed}"
        etx, ety = layout.entrance_tile
        ex, ey, ez = etx * ts, ety * ts, 0.0
        rx = spec.exterior_return_pos["x"]
        ry = spec.exterior_return_pos["y"]
        rz = spec.exterior_return_pos["z"]
        rc = spec.exterior_return_pos.get("cell", "")
        anchor_strs = ", ".join(
            f"{{x={atx * ts:.1f}, y={aty * ts:.1f}, z=0.0}}"
            for atx, aty in layout.anchor_tiles
        )
        lines.append(f"      {{")
        lines.append(f'        cell_id = "{cell_id}",')
        lines.append(f"        entrance_pos = {{x={ex:.1f}, y={ey:.1f}, z={ez:.1f}}},")
        lines.append(f'        exit_exterior = {{cell="{rc}", x={rx}, y={ry}, z={rz}}},')
        lines.append(f"        anchors = {{{anchor_strs}}},")
        lines.append(f"      }},")

    lines.append("    },")
    creatures = ", ".join(f'"{c}"' for c in spec.creature_pool)
    lines.append(f"    creatures = {{{creatures}}},")
    lines.append(f"    creatures_per_room = {{{spec.creatures_per_room[0]}, {spec.creatures_per_room[1]}}},")
    containers = ", ".join(f'"{c}"' for c in spec.loot_containers)
    lines.append(f"    containers = {{{containers}}},")
    lines.append(f"    loot_per_room = {{{spec.loot_per_room[0]}, {spec.loot_per_room[1]}}},")
    lines.append("  },")
    lines.append("}")
    lines.append(f"return {cfg_var}")
    return "\n".join(lines)
```

- [ ] **Step 5: Run all tests**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest tests/unit/test_dungeon_generator.py -v
poetry run pytest -x -q
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add omwtools/omwtools/dungeons/pool_builder.py omwtools/omwtools/dungeons/lua_config.py \
        omwtools/tests/unit/test_dungeon_generator.py
git commit -m "feat: pool builder and Lua config generator with TDD coverage"
```

---

## Task 5: JTT Game Configs

**Files:**
- Create: All `games/jungle_troll_tribes/dungeons/` files

Note: these files use `sys.path.insert` to allow importing from `omwtools/` without installing. The parent depth differs per file location — verify with the smoke test.

- [ ] **Step 1: Create package markers**

Create empty `__init__.py` files:
- `games/jungle_troll_tribes/dungeons/__init__.py`
- `games/jungle_troll_tribes/dungeons/tilesets/__init__.py`
- `games/jungle_troll_tribes/dungeons/types/__init__.py`

- [ ] **Step 2: Create cave tileset**

```python
# games/jungle_troll_tribes/dungeons/tilesets/cave.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[4] / "omwtools"))

from omwtools.dungeons.tile_spec import TileSet, TileDef

cave = TileSet(
    name="cave",
    tile_size=4.0,
    room_height=3.0,
    tiles={
        "floor":   TileDef(mesh="omwdg\\cave_floor.dae",   stat_id="jtt_cave_floor"),
        "wall":    TileDef(mesh="omwdg\\cave_wall.dae",    stat_id="jtt_cave_wall"),
        "corner":  TileDef(mesh="omwdg\\cave_corner.dae",  stat_id="jtt_cave_corner"),
        "pillar":  TileDef(mesh="omwdg\\cave_pillar.dae",  stat_id="jtt_cave_pillar"),
        "doorway": TileDef(mesh="omwdg\\cave_doorway.dae", stat_id="jtt_cave_doorway"),
        "ceiling": TileDef(
            mesh="omwdg\\cave_ceiling.dae",
            stat_id="jtt_cave_ceiling",
            z_offset=3.0,
        ),
    },
)
```

- [ ] **Step 3: Create dungeon type specs**

```python
# games/jungle_troll_tribes/dungeons/types/bear_den.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[5] / "omwtools"))
from omwtools.dungeons.dungeon_spec import DungeonSpec

bear_den = DungeonSpec(
    name="bear_den", game_prefix="jtt", tileset="cave",
    room_count=(1, 3), room_size=(3, 5), pool_size=8,
    exterior_return_pos={"cell": "", "x": 4096, "y": 4096, "z": 200},
    creature_pool=["jtt_bear", "jtt_wolf"],
    creatures_per_room=(1, 2),
    loot_containers=["jtt_loot_small", "jtt_loot_medium"],
    loot_per_room=(0, 1),
)
```

```python
# games/jungle_troll_tribes/dungeons/types/spider_cave.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[5] / "omwtools"))
from omwtools.dungeons.dungeon_spec import DungeonSpec

spider_cave = DungeonSpec(
    name="spider_cave", game_prefix="jtt", tileset="cave",
    room_count=(3, 6), room_size=(3, 6), pool_size=8,
    exterior_return_pos={"cell": "", "x": 4096, "y": 4096, "z": 200},
    creature_pool=["jtt_spider"],
    creatures_per_room=(2, 3),
    loot_containers=["jtt_loot_small", "jtt_loot_medium"],
    loot_per_room=(0, 1),
)
```

```python
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
```

- [ ] **Step 4: Create registry.py**

```python
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
```

- [ ] **Step 5: Smoke-test registry**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs
python -c "
import sys; sys.path.insert(0, 'omwtools')
from games.jungle_troll_tribes.dungeons.registry import TILESETS, DUNGEON_TYPES
print('Tilesets:', list(TILESETS.keys()))
print('Types:', list(DUNGEON_TYPES.keys()))
"
```
Expected:
```
Tilesets: ['cave']
Types: ['bear_den', 'spider_cave', 'troll_lair']
```

- [ ] **Step 6: Commit**

```bash
git add games/jungle_troll_tribes/dungeons/
git commit -m "feat: JTT dungeon configs — cave tileset + bear_den/spider_cave/troll_lair specs"
```

---

## Task 6: CLI Command + Tile Deployer

**Files:**
- Create: `omwtools/omwtools/dungeons/deployer.py`
- Create: `omwtools/omwtools/cli/cmd_dungeon.py`
- Modify: `omwtools/omwtools/cli/main.py`

- [ ] **Step 1: Write deployer.py**

```python
# omwtools/omwtools/dungeons/deployer.py
import shutil
from pathlib import Path

_MESH_SOURCE = Path(__file__).parent / "tilesets" / "meshes"


def deploy_tiles(tileset_name: str, game_dir: Path) -> list[str]:
    """
    Copy missing omwdg_*.dae files to <game_dir>/meshes/omwdg/.
    Never overwrites existing files (allows artist replacement).
    Returns list of filenames copied.
    """
    src_dir = _MESH_SOURCE / tileset_name
    dst_dir = game_dir / "meshes" / "omwdg"
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    if src_dir.exists():
        for src_file in src_dir.glob("omwdg_*.dae"):
            dst_file = dst_dir / src_file.name
            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)
                copied.append(src_file.name)
    return copied
```

- [ ] **Step 2: Add dungeon subcommand to main.py**

Open `omwtools/omwtools/cli/main.py`. In `_make_parser()`, find the last `sub.add_parser(...)` call and add after it:

```python
# Dungeon subcommand group
dg = sub.add_parser("dungeon", help="Procedural dungeon tools")
dg_sub = dg.add_subparsers(dest="dungeon_command", required=True)
dg_gen = dg_sub.add_parser("generate", help="Generate dungeon variant pool")
dg_gen.add_argument("--game", required=True,
    help="Game ID — resolves to games/<id>/ relative to repo root")
dg_gen.add_argument("--type", required=True, dest="dungeon_type",
    help="Dungeon type name (must exist in game registry)")
dg_gen.add_argument("--count", type=int, default=None,
    help="Number of variants (overrides spec pool_size)")
dg_gen.add_argument("--seed", type=int, default=0,
    help="Starting seed (default: 0)")
dg_gen.add_argument("--output", required=True,
    help="Output directory for JSON records file")
dg_gen.add_argument("--addon", default=None,
    help="Path to write compiled .omwaddon (optional; requires omw import+write)")
dg_gen.add_argument("--no-deploy", action="store_true",
    help="Skip copying tile meshes to game meshes/ dir")
```

In `main()`, add after the existing `elif` branches:

```python
elif args.command == "dungeon":
    from .cmd_dungeon import cmd_dungeon
    cmd_dungeon(args)
```

- [ ] **Step 3: Create cmd_dungeon.py**

```python
# omwtools/omwtools/cli/cmd_dungeon.py
import importlib.util
import json
import sqlite3
import sys
import tempfile
from dataclasses import replace
from pathlib import Path


def cmd_dungeon(args) -> None:
    if args.dungeon_command == "generate":
        _cmd_generate(args)


def _cmd_generate(args) -> None:
    game_id = args.game
    dungeon_type = args.dungeon_type
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_root = Path(__file__).parents[3]
    game_dir = repo_root / "games" / game_id
    if not game_dir.exists():
        print(f"Error: game directory not found: {game_dir}", file=sys.stderr)
        sys.exit(1)

    registry = _load_registry(game_dir)
    if dungeon_type not in registry["DUNGEON_TYPES"]:
        available = list(registry["DUNGEON_TYPES"].keys())
        print(f"Error: unknown type '{dungeon_type}'. Available: {available}", file=sys.stderr)
        sys.exit(1)

    spec = registry["DUNGEON_TYPES"][dungeon_type]
    tileset = registry["TILESETS"][spec.tileset]

    if args.count is not None:
        spec = replace(spec, pool_size=args.count)

    start_seed = args.seed  # default 0; use --seed N to offset the pool

    from omwtools.dungeons.pool_builder import build_pool
    from omwtools.dungeons.lua_config import generate_lua_config

    records, layouts = build_pool(spec, tileset, start_seed=start_seed)

    # Write JSON records file
    out_json = output_dir / f"{spec.game_prefix}_{dungeon_type}.json"
    out_json.write_text(json.dumps(records, indent=2))
    print(f"Written {len(records)} records to {out_json}")

    # Write Lua config
    lua_out_dir = game_dir / "scripts" / game_id
    lua_out_dir.mkdir(parents=True, exist_ok=True)
    lua_out = lua_out_dir / f"dungeon_config_{dungeon_type}.lua"
    lua_str = generate_lua_config(dungeon_type, spec, layouts, tileset, start_seed=start_seed)
    lua_out.write_text(lua_str)
    print(f"Written Lua config to {lua_out}")

    # Deploy tile meshes (unless --no-deploy)
    if not getattr(args, "no_deploy", False):
        from omwtools.dungeons.deployer import deploy_tiles
        copied = deploy_tiles(tileset.name, game_dir)
        if copied:
            print(f"Deployed {len(copied)} tile meshes to {game_dir}/meshes/omwdg/")
        else:
            print("Tile meshes already present, skipping deploy")

    # Compile .omwaddon if --addon specified
    if getattr(args, "addon", None):
        _compile_addon(out_json, Path(args.addon), game_id)


def _compile_addon(records_json: Path, addon_path: Path, mod_name: str) -> None:
    """Import JSON records into a temp DB and write as .omwaddon."""
    from omwtools.db.connection import make_db
    from omwtools.json_io.import_ import import_records_from_json
    from omwtools.cli.cmd_write import write_addon

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dungeon.db"
        conn = make_db(str(db_path))
        # Insert a mod entry (required by FK constraint)
        conn.execute(
            "INSERT INTO mods (id, filename, format_version, author, description, "
            "is_master, num_objects) VALUES (1, ?, 23, '', '', 0, 0)",
            (mod_name + ".omwaddon",)
        )
        conn.commit()
        import_records_from_json(conn, records_json.read_text(), mod_id=1)
        write_addon(conn, mod_id=1, output_path=str(addon_path))
        conn.close()
    print(f"Compiled addon: {addon_path}")


def _load_registry(game_dir: Path) -> dict:
    registry_path = game_dir / "dungeons" / "registry.py"
    spec = importlib.util.spec_from_file_location("registry", registry_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {"TILESETS": mod.TILESETS, "DUNGEON_TYPES": mod.DUNGEON_TYPES}
```

**Note on `write_addon`:** check whether `omwtools/omwtools/cli/cmd_write.py` exposes a callable `write_addon(conn, mod_id, output_path)` function. If not, adapt `_compile_addon` to call the existing write logic directly (read `cmd_write.py` to find the function name).

- [ ] **Step 4: Smoke-test the CLI**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run omw dungeon generate \
    --game jungle_troll_tribes \
    --type bear_den \
    --count 2 \
    --seed 0 \
    --output /tmp/test_dungeons/
```
Expected output (approx):
```
Written N records to /tmp/test_dungeons/jtt_bear_den.json
Written Lua config to .../scripts/jtt/dungeon_config_bear_den.lua
Tile meshes already present, skipping deploy   (or: Deployed N tile meshes...)
```

- [ ] **Step 5: Run full test suite**

```bash
poetry run pytest -x -q
```

- [ ] **Step 6: Commit**

```bash
git add omwtools/omwtools/dungeons/deployer.py \
        omwtools/omwtools/cli/cmd_dungeon.py \
        omwtools/omwtools/cli/main.py
git commit -m "feat: omw dungeon generate CLI — pool generation, Lua config, tile deploy, --addon"
```

---

## Task 7: Blender Placeholder Tile Meshes

**Files:**
- Create: `games/jungle_troll_tribes/dungeons/gen_dungeon_meshes.py`
- Create: `omwtools/omwtools/dungeons/tilesets/meshes/cave/*.dae` (6 files, via Blender)

- [ ] **Step 1: Write gen_dungeon_meshes.py**

```python
# games/jungle_troll_tribes/dungeons/gen_dungeon_meshes.py
"""
Blender Python script — generates 6 cave tile placeholder meshes.
Run: blender --background --python gen_dungeon_meshes.py
Output: omwtools/omwtools/dungeons/tilesets/meshes/cave/
"""
import bpy
import math
from pathlib import Path

OUT_DIR = Path(__file__).parents[3] / "omwtools" / "omwtools" / "dungeons" / "tilesets" / "meshes" / "cave"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TILE = 4.0
H = 3.0


def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.object.select_all(action='DESELECT')


def export(name: str):
    bpy.ops.object.select_all(action='SELECT')
    path = str(OUT_DIR / f"omwdg_{name}.dae")
    bpy.ops.wm.collada_export(filepath=path, selected=True)
    print(f"Exported: {path}")


def make_floor():
    clear()
    bpy.ops.mesh.primitive_plane_add(size=TILE, location=(0, 0, 0))
    export("cave_floor")


def make_wall():
    clear()
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -TILE / 2, H / 2))
    ob = bpy.context.active_object
    ob.scale = (TILE, 1, H)
    bpy.ops.object.transform_apply(scale=True)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    export("cave_wall")


def make_corner():
    """L-shaped corner: two wall panels at 90 degrees."""
    clear()
    # South face
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -TILE / 2, H / 2))
    ob1 = bpy.context.active_object
    ob1.scale = (TILE, 1, H)
    bpy.ops.object.transform_apply(scale=True)
    ob1.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    # West face
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-TILE / 2, 0, H / 2))
    ob2 = bpy.context.active_object
    ob2.scale = (TILE, 1, H)
    bpy.ops.object.transform_apply(scale=True)
    ob2.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    bpy.ops.object.transform_apply(rotation=True)
    export("cave_corner")


def make_pillar():
    clear()
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H)
    bpy.ops.object.transform_apply(scale=True)
    export("cave_pillar")


def make_doorway():
    """Arch frame: two vertical posts and a lintel."""
    clear()
    # Left post
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(-0.85, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H / 0.3)
    bpy.ops.object.transform_apply(scale=True)
    # Right post
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(0.85, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H / 0.3)
    bpy.ops.object.transform_apply(scale=True)
    # Lintel
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(0, 0, H - 0.15))
    ob = bpy.context.active_object
    ob.scale = (TILE / 0.3, 1, 1)
    bpy.ops.object.transform_apply(scale=True)
    export("cave_doorway")


def make_ceiling():
    clear()
    bpy.ops.mesh.primitive_plane_add(size=TILE, location=(0, 0, H))
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.editmode_toggle()
    export("cave_ceiling")


make_floor()
make_wall()
make_corner()
make_pillar()
make_doorway()
make_ceiling()
print("Done — 6 cave tile meshes generated.")
```

- [ ] **Step 2: Run the Blender script**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/games/jungle_troll_tribes/dungeons
blender --background --python gen_dungeon_meshes.py
```

- [ ] **Step 3: Verify output**

```bash
ls /home/mike/Documents/grimoires/openmw-ai-cs/omwtools/omwtools/dungeons/tilesets/meshes/cave/
```
Expected: 6 `.dae` files with `omwdg_` prefix

- [ ] **Step 4: Commit**

```bash
git add games/jungle_troll_tribes/dungeons/gen_dungeon_meshes.py \
        omwtools/omwtools/dungeons/tilesets/
git commit -m "feat: Blender placeholder tile meshes for cave tileset"
```

---

## Task 8: JTT Lua Dungeon Integration

**Files:**
- Modify: `games/jungle_troll_tribes/scripts/jtt/global.lua`
- Modify: `games/jungle_troll_tribes/scripts/jtt/player.lua`
- Modify: `games/jungle_troll_tribes/records/09_environment.json`

**OpenMW Lua API notes:**
- `world.players[1]` — correct way to get the player actor (NOT `world.activeActors[1]`)
- `actor:teleport(cellName, position, rotation)` — `cellName` is the CELL's `cell_name` field, which equals `cell_id` (set this way in `cell_builder.build()`)
- `world.createObject(recordId, count)` — creates an object, returns it; then call `obj:teleport(...)` to place it
- `core.registerGlobalEventHandler(name, fn)` — registers a global script event handler

- [ ] **Step 1: Generate the dungeon pool first**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run omw dungeon generate \
    --game jungle_troll_tribes \
    --type bear_den \
    --count 8 \
    --seed 0 \
    --output ../games/jungle_troll_tribes/records/
```
This creates `records/jtt_bear_den.json` and `scripts/jtt/dungeon_config_bear_den.lua`.

- [ ] **Step 2: Add ACTI records for entrance/exit markers**

Open `games/jungle_troll_tribes/records/09_environment.json`. Inside the JSON array add:

```json
{"rec_type": "ACTI", "record_id": "jtt_dungeon_entrance", "mesh": "omwdg\\cave_doorway.dae", "name": "Cave Entrance", "script": ""},
{"rec_type": "ACTI", "record_id": "jtt_dungeon_exit",     "mesh": "omwdg\\cave_doorway.dae", "name": "Cave Exit",     "script": ""}
```

- [ ] **Step 3: Add dungeon handlers to global.lua**

Append to the bottom of `games/jungle_troll_tribes/scripts/jtt/global.lua`:

```lua
-- ============================================================
-- DUNGEON SYSTEM
-- ============================================================

local JTT_DungeonState = {}

local function loadDungeonConfig(typeName)
    local ok, cfg = pcall(require, "scripts.jtt.dungeon_config_" .. typeName)
    if not ok then
        util.log("JTT: dungeon config not found: " .. typeName)
        return nil
    end
    -- cfg is the table returned by the Lua module; it has a key matching the type name
    return cfg and cfg[typeName] or nil
end

local function onJTTEnterDungeon(data)
    local typeName = data.dungeon_type
    local cfg = loadDungeonConfig(typeName)
    if not cfg then return end

    local variants = cfg.variants
    local idx = math.random(1, #variants)
    local variant = variants[idx]
    local player = world.players[1]  -- correct OpenMW API for player

    local pos = util.vector3(variant.entrance_pos.x, variant.entrance_pos.y, variant.entrance_pos.z)
    player:teleport(variant.cell_id, pos, util.transform.identity)

    -- spawned = list of objects placed by PopulateDungeon, used for cleanup on exit
    JTT_DungeonState[variant.cell_id] = { variant = variant, dungeon_type = typeName, spawned = {} }

    core.sendGlobalEvent("JTT_PopulateDungeon", {
        cell_id      = variant.cell_id,
        dungeon_type = typeName,
        anchors      = variant.anchors,
    })
end

local function onJTTPopulateDungeon(data)
    local cfg = loadDungeonConfig(data.dungeon_type)
    if not cfg then return end

    local cellId  = data.cell_id
    local anchors = data.anchors
    local state   = JTT_DungeonState[cellId]

    for _, anchor in ipairs(anchors) do
        local pos = util.vector3(anchor.x, anchor.y, anchor.z)

        if #cfg.creatures > 0 then
            local count = math.random(cfg.creatures_per_room[1], cfg.creatures_per_room[2])
            for _ = 1, count do
                local creatureId = cfg.creatures[math.random(1, #cfg.creatures)]
                local obj = world.createObject(creatureId, 1)
                local jitter = util.vector3(math.random(-2, 2), math.random(-2, 2), 0)
                obj:teleport(cellId, pos + jitter, util.transform.identity)
                if state then table.insert(state.spawned, obj) end
            end
        end

        if #cfg.containers > 0 then
            local roll = math.random(cfg.loot_per_room[1], cfg.loot_per_room[2])
            if roll > 0 then
                local contId = cfg.containers[math.random(1, #cfg.containers)]
                local lootObj = world.createObject(contId, 1)
                lootObj:teleport(cellId, pos + util.vector3(1.5, 0, 0), util.transform.identity)
                if state then table.insert(state.spawned, lootObj) end
            end
        end
    end
end

local function onJTTExitDungeon(data)
    local cellId = data.cell_id
    local state  = JTT_DungeonState[cellId]
    if not state then return end

    -- Despawn all objects spawned during this dungeon visit (actors + containers)
    for _, obj in ipairs(state.spawned) do
        if obj and obj:isValid() then
            obj:remove()
        end
    end

    -- Teleport player back to exterior
    local ext    = state.variant.exit_exterior
    local player = world.players[1]
    local pos    = util.vector3(ext.x, ext.y, ext.z)
    local target = (ext.cell == "" or ext.cell == "default") and "" or ext.cell
    player:teleport(target, pos, util.transform.identity)

    JTT_DungeonState[cellId] = nil
end

core.registerGlobalEventHandler("JTT_EnterDungeon",    onJTTEnterDungeon)
core.registerGlobalEventHandler("JTT_PopulateDungeon", onJTTPopulateDungeon)
core.registerGlobalEventHandler("JTT_ExitDungeon",     onJTTExitDungeon)
```

- [ ] **Step 4: Wire dungeon exit in player.lua**

In `games/jungle_troll_tribes/scripts/jtt/player.lua`, add an `onActivate` handler. Read the existing return table first — the handler must be added to it:

```lua
-- Add this function before the return statement:
local function onActivate(object, activator)
    local id = tostring(object.recordId):lower()
    if id == "jtt_dungeon_exit" then
        core.sendGlobalEvent("JTT_ExitDungeon", { cell_id = object.cell.name })
    end
    -- jtt_dungeon_entrance activation is handled by exterior bear den activators
    -- (each exterior activator fires JTT_EnterDungeon with its dungeon_type)
end

-- In the return table, add:
-- onActivate = onActivate,
```

**Note on exterior entrance wiring:** For each exterior bear den activator (the `jtt_bear_den` ACTI placed in the world via Lua spawning in `global.lua`), add an `onActivate` in `player.lua` that detects its record ID and fires:
```lua
core.sendGlobalEvent("JTT_EnterDungeon", { dungeon_type = "bear_den" })
```
The exterior activator record ID pattern (e.g. `jtt_bear_den_entrance`) determines which dungeon type to enter. Add a mapping table in `player.lua`:

```lua
local DUNGEON_ACTIVATORS = {
    jtt_bear_den_entrance = "bear_den",
    -- add spider_cave and troll_lair when those activators are added to the world
}
```

- [ ] **Step 5: Run full test suite**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest -x -q
```

- [ ] **Step 6: Commit**

```bash
git add games/jungle_troll_tribes/scripts/jtt/global.lua \
        games/jungle_troll_tribes/scripts/jtt/player.lua \
        games/jungle_troll_tribes/records/09_environment.json \
        games/jungle_troll_tribes/records/jtt_bear_den.json \
        games/jungle_troll_tribes/scripts/jtt/dungeon_config_bear_den.lua
git commit -m "feat: JTT dungeon Lua integration — entry/exit/populate + bear_den pool"
```

---

## Manual Verification Checklist

After all tasks complete, rebuild JTT and verify in OpenMW:

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
bash ../games/jungle_troll_tribes/build.sh
flatpak run --command=openmw org.openmw.OpenMW --skip-menu --new-game
```

- [ ] Game loads without errors
- [ ] Player spawns in exterior world
- [ ] Activating a bear den entrance fires `JTT_EnterDungeon` and teleports into cave cell
- [ ] Cave floor, walls, ceiling geometry renders correctly
- [ ] Bears/wolves spawn near anchor positions
- [ ] Activating exit marker teleports player back to exterior (4096, 4096)
- [ ] Re-entering a bear den produces a different layout (different random seed)
- [ ] Creatures from previous visit are despawned on re-entry
- [ ] No OpenMW errors in `~/.var/app/org.openmw.OpenMW/data/openmw/logs/openmw.log`
