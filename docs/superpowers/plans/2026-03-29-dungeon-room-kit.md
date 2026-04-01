# Dungeon Room Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-tile dungeon assembly with pre-built room meshes (BGS dungeon-kit style) so each room is one complete mesh with textures, while corridors keep existing tile pieces.

**Architecture:** 10 Blender-authored room variants (1024×1024×256 hollow box with 4 doorway openings) are placed one-per-room as single STAT refs. Corridors between rooms still use the existing floor/wall/ceiling tiles. The cell builder gains a `build_roomkit()` path; `pool_builder` and `cmd_dungeon` detect the new `RoomKit` type via `isinstance`.

**Tech Stack:** Python 3.12, Blender 3.0 Python API (bpy), omwtools CLI, OpenMW Lua

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `games/jungle_troll_tribes/dungeons/gen_room_meshes.py` | Create | Blender script: 10 room variants + corridor mesh |
| `omwtools/omwtools/dungeons/room_kit.py` | Create | `RoomVariant` + `RoomKit` dataclasses |
| `omwtools/omwtools/dungeons/room_builder.py` | Create | `stat_records_roomkit()` + `build_roomkit()` |
| `omwtools/tests/unit/test_room_builder.py` | Create | Tests for room_builder |
| `omwtools/omwtools/dungeons/pool_builder.py` | Modify | Add `build_pool_roomkit()` |
| `omwtools/omwtools/cli/cmd_dungeon.py` | Modify | Route to roomkit path when TILESETS entry is RoomKit |
| `omwtools/omwtools/dungeons/lua_config.py` | Modify | Accept `RoomKit | TileSet` (duck-typed, same `.tile_size`) |
| `games/jungle_troll_tribes/dungeons/tilesets/cave_roomkit.py` | Create | Cave RoomKit definition |
| `games/jungle_troll_tribes/dungeons/registry.py` | Modify | Import + register cave_roomkit; update bear_den tileset ref |
| `games/jungle_troll_tribes/dungeons/types/bear_den.py` | Modify | `room_size=(4,4)`, `tileset="cave_roomkit"` |
| `games/jungle_troll_tribes/records/19_dungeons.json` | Regenerate | `omw dungeon generate --game jungle_troll_tribes --type bear_den` |

---

## Mesh Design Reference

```
Room (top-down view, 1024×1024):
┌────┤  ├────┐   ← North wall with 256-wide doorway
│    │  │    │
├────┘  └────┤   ← Doorways on all 4 sides
│            │
├────┐  ┌────┤
│    │  │    │
└────┤  ├────┘
```

- Room mesh: 10 variants, all 1024×1024×256, placed at room `centre_tile * tile_size`
- Doorway: 256 wide × 200 tall centered on each wall (remaining 56 units = lintel)
- Corridor: existing `cave_floor.dae` + `cave_ceiling.dae` + wall tiles
- Tile size: 256 units; rooms are 4×4 tiles; room_size fixed to (4,4) in spec

---

## Task 1: Blender Room Mesh Script

**Files:**
- Create: `games/jungle_troll_tribes/dungeons/gen_room_meshes.py`

- [ ] **Step 1: Write the script**

```python
"""
Blender script — generates 10 pre-built cave room variants + 1 corridor piece.
Run: blender --background --python gen_room_meshes.py
Output: games/jungle_troll_tribes/meshes/omwdg/cave_room_{a-j}.dae
                                               cave_corridor.dae
Requires cave_stone.png already present in the output directory.
"""
import bpy
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR   = REPO_ROOT / "games" / "jungle_troll_tribes" / "meshes" / "omwdg"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ROOM   = 1024.0   # room footprint (square), = 4 × tile_size
H      = 256.0    # room height
DOOR_W = 256.0    # doorway opening width (= 1 tile)
DOOR_H = 200.0    # doorway opening height (< H so there's a lintel)
WALL_T = 24.0     # wall thickness


# ─── Material ────────────────────────────────────────────────────────────────

def make_material():
    """Load cave_stone.png (already in OUT_DIR) and make a Lambert material."""
    tex_path = OUT_DIR / "cave_stone.png"
    img = bpy.data.images.load(str(tex_path))
    mat = bpy.data.materials.new("cave_rock")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    tex  = nodes.new('ShaderNodeTexImage')
    tex.image = img
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.95
    out  = nodes.new('ShaderNodeOutputMaterial')
    links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat


# ─── Helpers ─────────────────────────────────────────────────────────────────

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def apply_mat(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def add_box(cx, cy, cz, sx, sy, sz, mat):
    """Cube with given half-extents sx/sy/sz, centred at (cx,cy,cz)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    ob = bpy.context.active_object
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(ob, mat)
    return ob


def add_plane(cx, cy, cz, sx, sy, mat, flip_normals=False):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, cz))
    ob = bpy.context.active_object
    ob.scale = (sx, sy, 1)
    bpy.ops.object.transform_apply(scale=True)
    if flip_normals:
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.editmode_toggle()
    apply_mat(ob, mat)
    return ob


def uv_all():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.editmode_toggle()


def fix_tex_path(dae_path: str):
    """Replace any absolute cave_stone path with a relative filename."""
    txt = Path(dae_path).read_text()
    txt = re.sub(
        r'<init_from>[^<]*cave_stone[^<]*</init_from>',
        '<init_from>cave_stone.png</init_from>',
        txt,
    )
    Path(dae_path).write_text(txt)


def export(name: str):
    bpy.ops.object.select_all(action='SELECT')
    fp = str(OUT_DIR / f"cave_{name}.dae")
    bpy.ops.wm.collada_export(filepath=fp, selected=True, use_texture_copies=False)
    fix_tex_path(fp)
    print(f"Exported: {fp}")


# ─── Room base ───────────────────────────────────────────────────────────────

def make_room_shell(mat):
    """
    Floor + ceiling + 4 walls with doorway openings.
    All geometry centred at origin; room spans ±512 in X/Y, 0..256 in Z.
    Doorway: 256 wide × 200 tall centred on each wall.
    """
    hs     = ROOM / 2        # 512 — half-span
    dw2    = DOOR_W / 2      # 128 — half door width
    pw     = hs - dw2        # 384 — pillar width
    lh     = H - DOOR_H      # 56  — lintel height

    # Floor
    add_plane(0, 0, 0, ROOM, ROOM, mat)
    # Ceiling (normals down)
    add_plane(0, 0, H, ROOM, ROOM, mat, flip_normals=True)

    for (axis, sign) in [('x', +1), ('x', -1), ('y', +1), ('y', -1)]:
        # Two side pillars flanking the doorway
        for pside in (-1, +1):
            pc = pside * (dw2 + pw / 2)  # pillar centre offset
            if axis == 'x':
                add_box(sign * hs, pc, H / 2, WALL_T, pw, H, mat)
            else:
                add_box(pc, sign * hs, H / 2, pw, WALL_T, H, mat)
        # Lintel above doorway
        if lh > 0:
            cz = DOOR_H + lh / 2
            if axis == 'x':
                add_box(sign * hs, 0, cz, WALL_T, DOOR_W, lh, mat)
            else:
                add_box(0, sign * hs, cz, DOOR_W, WALL_T, lh, mat)


# ─── Room variants ────────────────────────────────────────────────────────────

def variant_a(mat):
    """Bare cave room."""
    clear(); make_room_shell(mat)
    uv_all(); export("room_a")

def variant_b(mat):
    """Central stone pillar."""
    clear(); make_room_shell(mat)
    add_box(0, 0, H / 2, 64, 64, H, mat)
    uv_all(); export("room_b")

def variant_c(mat):
    """Two offset pillars."""
    clear(); make_room_shell(mat)
    for px in (-256, 256):
        add_box(px, 0, H / 2, 64, 64, H, mat)
    uv_all(); export("room_c")

def variant_d(mat):
    """Rock ledge platform on east side."""
    clear(); make_room_shell(mat)
    add_box(280, 0, 48, 200, 500, 96, mat)
    uv_all(); export("room_d")

def variant_e(mat):
    """Four stalactite columns from ceiling."""
    clear(); make_room_shell(mat)
    for (sx, sy) in ((-220, -220), (220, 220), (-220, 220), (220, -220)):
        add_box(sx, sy, H - 60, 28, 28, 120, mat)
    uv_all(); export("room_e")

def variant_f(mat):
    """Raised altar block at north end."""
    clear(); make_room_shell(mat)
    add_box(0, 350, 48, 280, 150, 96, mat)
    uv_all(); export("room_f")

def variant_g(mat):
    """Four corner pillars."""
    clear(); make_room_shell(mat)
    for (px, py) in ((-300, -300), (-300, 300), (300, -300), (300, 300)):
        add_box(px, py, H / 2, 56, 56, H, mat)
    uv_all(); export("room_g")

def variant_h(mat):
    """Central cross-shaped rock formation."""
    clear(); make_room_shell(mat)
    add_box(0, 0, H / 4, 320, 56, H / 2, mat)
    add_box(0, 0, H / 4, 56, 320, H / 2, mat)
    uv_all(); export("room_h")

def variant_i(mat):
    """Wide flat boulder in centre."""
    clear(); make_room_shell(mat)
    add_box(0, 0, 56, 450, 350, 112, mat)
    uv_all(); export("room_i")

def variant_j(mat):
    """Three stalactites + one floor stalagmite."""
    clear(); make_room_shell(mat)
    for (sx, sy) in ((-100, -100), (100, 200), (-200, 150)):
        add_box(sx, sy, H - 50, 24, 24, 100, mat)
    add_box(0, -200, 80, 36, 36, 160, mat)   # stalagmite from floor
    uv_all(); export("room_j")


# ─── Corridor piece ───────────────────────────────────────────────────────────

def make_corridor(mat):
    """
    256×256×256 corridor: floor + ceiling + E/W side walls; open N/S.
    Rotate 90° around Z in cell_builder for E-W corridor tiles.
    """
    clear()
    add_plane(0, 0, 0, 256, 256, mat)                  # floor
    add_plane(0, 0, H, 256, 256, mat, flip_normals=True) # ceiling
    add_box( 128, 0, H / 2, WALL_T, 256, H, mat)        # east wall
    add_box(-128, 0, H / 2, WALL_T, 256, H, mat)        # west wall
    uv_all()
    export("corridor")


# ─── Main ────────────────────────────────────────────────────────────────────

mat = make_material()
for fn in (variant_a, variant_b, variant_c, variant_d, variant_e,
           variant_f, variant_g, variant_h, variant_i, variant_j):
    fn(mat)
make_corridor(mat)
print("Done — 10 room variants + corridor generated.")
```

- [ ] **Step 2: Run the script**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/games/jungle_troll_tribes
blender --background --python dungeons/gen_room_meshes.py
```

Expected output: `Exported: .../cave_room_a.dae` ... `cave_room_j.dae` ... `cave_corridor.dae`

- [ ] **Step 3: Verify files exist**

```bash
ls games/jungle_troll_tribes/meshes/omwdg/cave_room_*.dae games/jungle_troll_tribes/meshes/omwdg/cave_corridor.dae
```

Expected: 11 files listed

- [ ] **Step 4: Verify texture path in one DAE**

```bash
grep 'init_from' games/jungle_troll_tribes/meshes/omwdg/cave_room_a.dae
```

Expected: `<init_from>cave_stone.png</init_from>`

- [ ] **Step 5: Commit**

```bash
git add games/jungle_troll_tribes/dungeons/gen_room_meshes.py games/jungle_troll_tribes/meshes/omwdg/cave_room_*.dae games/jungle_troll_tribes/meshes/omwdg/cave_corridor.dae
git commit -m "feat: add dungeon room kit — 10 cave room variants + corridor mesh"
```

---

## Task 2: RoomKit Dataclasses

**Files:**
- Create: `omwtools/omwtools/dungeons/room_kit.py`
- Test: `omwtools/tests/unit/test_room_builder.py` (partial — write fixture here)

- [ ] **Step 1: Write the failing test**

```python
# omwtools/tests/unit/test_room_builder.py
from omwtools.dungeons.room_kit import RoomKit, RoomVariant

def test_roomkit_get_variant_cycles():
    kit = RoomKit(
        name="cave",
        tile_size=256.0,
        room_tiles=4,
        room_height=256.0,
        variants=[
            RoomVariant(mesh="omwdg\\cave_room_a.dae", stat_id="tst_cave_room_a"),
            RoomVariant(mesh="omwdg\\cave_room_b.dae", stat_id="tst_cave_room_b"),
        ],
        corridor_mesh="omwdg\\cave_corridor.dae",
        corridor_stat_id="tst_cave_corridor",
    )
    assert kit.room_size == 1024.0    # tile_size * room_tiles
    assert len(kit.variants) == 2
    assert kit.corridor_stat_id == "tst_cave_corridor"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest tests/unit/test_room_builder.py::test_roomkit_get_variant_cycles -v
```

Expected: FAIL — `ImportError: cannot import name 'RoomKit'`

- [ ] **Step 3: Write the dataclasses**

```python
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

    @property
    def room_size(self) -> float:
        """Room footprint in world units."""
        return self.tile_size * self.room_tiles
```

- [ ] **Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/unit/test_room_builder.py::test_roomkit_get_variant_cycles -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add omwtools/omwtools/dungeons/room_kit.py omwtools/tests/unit/test_room_builder.py
git commit -m "feat: add RoomKit/RoomVariant dataclasses"
```

---

## Task 3: Room Builder

**Files:**
- Create: `omwtools/omwtools/dungeons/room_builder.py`
- Modify: `omwtools/tests/unit/test_room_builder.py`

The room builder places **one room mesh per room** and **corridor tile pieces for corridor_tiles only**. It does NOT place floor/ceiling/wall tiles inside rooms (the room mesh covers those). Boundary tiles adjacent only to room tiles are skipped (the room mesh walls handle those). Corridor boundary tiles use existing `cave_wall.dae` via the `TileSet` — OR we just use the flat wall tiles passed separately.

**Simpler approach:** `build_roomkit()` accepts the `RoomKit` for room meshes and a `TileSet` for corridor tile pieces. This reuses all existing cave tile meshes for corridors.

- [ ] **Step 1: Write failing tests**

```python
# Add to omwtools/tests/unit/test_room_builder.py
import random
from omwtools.dungeons.room_kit import RoomKit, RoomVariant
from omwtools.dungeons.tile_spec import TileSet, TileDef
from omwtools.dungeons.dungeon_spec import DungeonSpec
from omwtools.dungeons.generator import generate
from omwtools.dungeons.room_builder import stat_records_roomkit, build_roomkit

KIT = RoomKit(
    name="cave",
    tile_size=256.0,
    room_tiles=4,
    room_height=256.0,
    variants=[
        RoomVariant(mesh="omwdg\\cave_room_a.dae", stat_id="tst_room_a"),
        RoomVariant(mesh="omwdg\\cave_room_b.dae", stat_id="tst_room_b"),
    ],
    corridor_mesh="omwdg\\cave_corridor.dae",
    corridor_stat_id="tst_corridor",
)

CORRIDOR_TILES = TileSet(
    name="cave",
    tile_size=256.0,
    room_height=256.0,
    tiles={
        "floor":   TileDef(mesh="omwdg\\cave_floor.dae",   stat_id="tst_floor"),
        "wall":    TileDef(mesh="omwdg\\cave_wall.dae",    stat_id="tst_wall"),
        "corner":  TileDef(mesh="omwdg\\cave_corner.dae",  stat_id="tst_corner"),
        "pillar":  TileDef(mesh="omwdg\\cave_pillar.dae",  stat_id="tst_pillar"),
        "doorway": TileDef(mesh="omwdg\\cave_doorway.dae", stat_id="tst_doorway"),
        "ceiling": TileDef(mesh="omwdg\\cave_ceiling.dae", stat_id="tst_ceiling"),
    },
)

SPEC = DungeonSpec(
    name="test_cave", game_prefix="tst", tileset="cave_roomkit",
    room_count=(2, 3), room_size=(4, 4), pool_size=1,
    exterior_return_pos={"cell": "", "x": 0, "y": 0, "z": 0},
    creature_pool=[], creatures_per_room=(0, 0),
    loot_containers=[], loot_per_room=(0, 0),
)


def test_stat_records_roomkit():
    stats = stat_records_roomkit(KIT)
    ids = {s["record_id"] for s in stats}
    assert "tst_room_a" in ids
    assert "tst_room_b" in ids
    assert "tst_corridor" in ids
    assert all(s["rec_type"] == "STAT" for s in stats)


def test_build_roomkit_has_one_ref_per_room():
    layout = generate(SPEC, seed=0)
    cell = build_roomkit(layout, KIT, CORRIDOR_TILES, "tst_cell_0", seed=0)
    refs = cell["refs"]
    room_refs = [r for r in refs
                 if r["object_id"] in {"tst_room_a", "tst_room_b"}]
    assert len(room_refs) == len(layout.rooms)


def test_build_roomkit_no_room_tiles_in_corridor_refs():
    layout = generate(SPEC, seed=0)
    cell = build_roomkit(layout, KIT, CORRIDOR_TILES, "tst_cell_0", seed=0)
    refs = cell["refs"]
    # Corridor floor refs must all be at corridor tile positions
    ts = KIT.tile_size
    floor_refs = [r for r in refs if r["object_id"] == "tst_floor"]
    floor_positions = {(r["pos"][0] / ts, r["pos"][1] / ts) for r in floor_refs}
    for tx, ty in floor_positions:
        assert (int(tx), int(ty)) in layout.corridor_tiles, \
            f"Floor tile at ({tx},{ty}) is not a corridor tile"


def test_build_roomkit_cell_is_interior():
    layout = generate(SPEC, seed=0)
    cell = build_roomkit(layout, KIT, CORRIDOR_TILES, "tst_cell_0", seed=0)
    assert cell["rec_type"] == "CELL"
    assert cell["cell_flags"] & 1  # CELL_INTERIOR bit
    assert cell["ambient"]["ambient"] == 0xFFFFFFFF
```

- [ ] **Step 2: Run to verify they fail**

```bash
poetry run pytest tests/unit/test_room_builder.py -v -k "not test_roomkit_get_variant_cycles"
```

Expected: FAIL — `ImportError: cannot import name 'stat_records_roomkit'`

- [ ] **Step 3: Write the room builder**

```python
# omwtools/omwtools/dungeons/room_builder.py
import random
from .dungeon_spec import DungeonLayout
from .room_kit import RoomKit
from .tile_spec import TileSet, WALL_ROTATIONS, BASE_TILE
from .cell_builder import _make_ref, _REF_DEFAULTS   # reuse private helpers


def stat_records_roomkit(kit: RoomKit) -> list[dict]:
    """STAT records for all room variants + corridor piece."""
    records = [
        {"rec_type": "STAT", "record_id": v.stat_id, "mesh": v.mesh, "flags": 0}
        for v in kit.variants
    ]
    records.append(
        {"rec_type": "STAT", "record_id": kit.corridor_stat_id,
         "mesh": kit.corridor_mesh, "flags": 0}
    )
    return records


def build_roomkit(
    layout: DungeonLayout,
    kit: RoomKit,
    corridor_tiles: TileSet,
    cell_id: str,
    seed: int = 0,
) -> dict:
    """
    Build a CELL record using the room-kit approach:
    - One pre-built room mesh per room (randomly chosen variant)
    - Corridor floor/ceiling tiles only for corridor_tiles
    - Boundary walls only where adjacent to corridor tiles
    - Entrance + exit ACTI refs at first/last room centres
    """
    rng = random.Random(seed)
    ts  = kit.tile_size
    prefix = layout.spec.game_prefix
    refs: list[dict] = []
    ref_num = 1

    # ── Room meshes (one per room) ──────────────────────────────────────────
    for room in layout.rooms:
        cx, cy = room.centre_tile
        variant = rng.choice(kit.variants)
        refs.append(_make_ref(ref_num, variant.stat_id, cx * ts, cy * ts, 0.0, 0.0))
        ref_num += 1

    # ── Corridor floor + ceiling ────────────────────────────────────────────
    for tx, ty in sorted(layout.corridor_tiles):
        floor_def = corridor_tiles.get_tile("floor")
        refs.append(_make_ref(ref_num, floor_def.stat_id, tx * ts, ty * ts, 0.0, 0.0))
        ref_num += 1
        ceil_def = corridor_tiles.get_tile("ceiling")
        refs.append(_make_ref(ref_num, ceil_def.stat_id, tx * ts, ty * ts,
                               kit.room_height, 0.0))
        ref_num += 1

    # ── Corridor boundary walls (skip tiles adjacent only to room tiles) ────
    floor_tiles = layout.floor_tiles
    corridor_set = layout.corridor_tiles
    for (tx, ty), tile_type in sorted(layout.boundary_tiles.items()):
        cardinal = [(tx, ty-1), (tx, ty+1), (tx+1, ty), (tx-1, ty)]
        if not any(nb in corridor_set for nb in cardinal):
            continue  # adjacent only to room tiles — room mesh handles this
        base = BASE_TILE.get(tile_type)
        if base not in corridor_tiles.tiles:
            continue
        tile_def = corridor_tiles.get_tile(tile_type)
        rot_z = WALL_ROTATIONS.get(tile_type, 0.0)
        refs.append(_make_ref(ref_num, tile_def.stat_id, tx * ts, ty * ts, 0.0, rot_z))
        ref_num += 1

    # ── Entrance ACTI ───────────────────────────────────────────────────────
    etx, ety = layout.entrance_tile
    refs.append(_make_ref(ref_num, f"{prefix}_dungeon_entrance",
                           etx * ts, ety * ts, 0.0, 0.0))
    ref_num += 1

    # ── Exit ACTI ───────────────────────────────────────────────────────────
    xtx, xty = layout.exit_tile
    refs.append(_make_ref(ref_num, f"{prefix}_dungeon_exit",
                           xtx * ts, xty * ts, 0.0, 0.0))
    ref_num += 1

    # ── Bone torches — one per room ────────────────────────────────────────
    for room in layout.rooms:
        cx, cy = room.centre_tile
        refs.append(_make_ref(ref_num, f"{prefix}_bone_torch",
                               cx * ts, cy * ts, ts * 0.5, 0.0))
        ref_num += 1

    return {
        "rec_type": "CELL",
        "record_id": cell_id,
        "cell_name": cell_id,
        "cell_flags": 1,
        "grid_x": 0,
        "grid_y": 0,
        "ambient": {"ambient": 0xFFFFFFFF, "sunlight": 0, "fog": 0, "fog_density": 0.0},
        "region": "",
        "ref_num_counter": 0,
        "water_height": -1.0,
        "flags": 0,
        "refs": refs,
    }
```

**Note:** `_make_ref` and `_REF_DEFAULTS` are private but stable — importing them avoids duplication. If this causes issues, copy the ~10 lines from `cell_builder.py`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/unit/test_room_builder.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Run full test suite**

```bash
poetry run pytest -x -q
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add omwtools/omwtools/dungeons/room_builder.py omwtools/tests/unit/test_room_builder.py
git commit -m "feat: add room_builder — build_roomkit() places one mesh per room"
```

---

## Task 4: Pool Builder + cmd_dungeon Wiring

**Files:**
- Modify: `omwtools/omwtools/dungeons/pool_builder.py`
- Modify: `omwtools/omwtools/cli/cmd_dungeon.py`
- Modify: `omwtools/omwtools/dungeons/lua_config.py`

### pool_builder.py

- [ ] **Step 1: Add `build_pool_roomkit()`**

Open `omwtools/omwtools/dungeons/pool_builder.py`. The current file is:

```python
# omwtools/omwtools/dungeons/pool_builder.py
from .dungeon_spec import DungeonSpec, DungeonLayout
from .tile_spec import TileSet
from .generator import generate
from .cell_builder import build, stat_records


def build_pool(
    spec: DungeonSpec,
    tileset: TileSet,
    start_seed: int = 0,
) -> tuple[list[dict], list[DungeonLayout], list[str]]:
    ...
```

Add after the existing function:

```python
from .room_kit import RoomKit
from .room_builder import stat_records_roomkit, build_roomkit


def build_pool_roomkit(
    spec: DungeonSpec,
    kit: RoomKit,
    corridor_tiles: TileSet,
    start_seed: int = 0,
) -> tuple[list[dict], list[DungeonLayout], list[str]]:
    """Like build_pool() but uses the room-kit builder."""
    # STAT records: room variants + corridor + corridor tile pieces
    from .cell_builder import stat_records as tile_stat_records
    stats = stat_records_roomkit(kit) + tile_stat_records(corridor_tiles)
    # Deduplicate by record_id (corridor TileSet and RoomKit share no IDs)
    seen: set[str] = set()
    unique_stats = []
    for s in stats:
        if s["record_id"] not in seen:
            seen.add(s["record_id"])
            unique_stats.append(s)

    cells: list[dict] = []
    layouts: list[DungeonLayout] = []
    cell_ids: list[str] = []
    for i in range(spec.pool_size):
        seed = start_seed + i
        cell_id = f"{spec.game_prefix}_{spec.name}_{seed}"
        cell_ids.append(cell_id)
        layout = generate(spec, seed)
        layouts.append(layout)
        cells.append(build_roomkit(layout, kit, corridor_tiles, cell_id, seed=seed))
    return unique_stats + cells, layouts, cell_ids
```

### lua_config.py

- [ ] **Step 2: Remove TileSet import coupling**

Current line 2: `from .tile_spec import TileSet`
Current line 23: `ts = tileset.tile_size`

The `RoomKit` also has `.tile_size`, so the code works unchanged. Just update the type hint:

Replace:
```python
from .tile_spec import TileSet

def generate_lua_config(
    type_name: str,
    spec: DungeonSpec,
    layouts: list[DungeonLayout],
    tileset: TileSet,
    cell_ids: list[str],
) -> str:
```

With:
```python
def generate_lua_config(
    type_name: str,
    spec: DungeonSpec,
    layouts: list[DungeonLayout],
    tileset,        # TileSet or RoomKit — both have .tile_size
    cell_ids: list[str],
) -> str:
```

(Remove the `TileSet` import entirely since it's no longer needed here.)

### cmd_dungeon.py

- [ ] **Step 3: Route to room-kit path**

In `_cmd_generate()`, the registry lookup is:
```python
tileset = registry["TILESETS"][spec.tileset]
```

Replace the block from `records, layouts, cell_ids = build_pool(...)` through the Lua config call:

```python
    kit_or_tileset = registry["TILESETS"][spec.tileset]

    from omwtools.dungeons.room_kit import RoomKit
    if isinstance(kit_or_tileset, RoomKit):
        from omwtools.dungeons.pool_builder import build_pool_roomkit
        from omwtools.dungeons.tilesets import _cave_corridor_tileset  # see Task 5
        records, layouts, cell_ids = build_pool_roomkit(
            spec, kit_or_tileset, _cave_corridor_tileset, start_seed=start_seed
        )
    else:
        from omwtools.dungeons.pool_builder import build_pool
        records, layouts, cell_ids = build_pool(
            spec, kit_or_tileset, start_seed=start_seed
        )

    from omwtools.dungeons.lua_config import generate_lua_config
    ...
```

**Note:** `_cave_corridor_tileset` is a shared TileSet for corridor pieces — defined in Task 5 alongside the cave RoomKit definition. The import path is updated there.

- [ ] **Step 4: Run tests**

```bash
poetry run pytest -x -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add omwtools/omwtools/dungeons/pool_builder.py \
        omwtools/omwtools/cli/cmd_dungeon.py \
        omwtools/omwtools/dungeons/lua_config.py
git commit -m "feat: wire pool_builder and cmd_dungeon for RoomKit path"
```

---

## Task 5: Cave RoomKit Definition + Registry

**Files:**
- Create: `games/jungle_troll_tribes/dungeons/tilesets/cave_roomkit.py`
- Modify: `games/jungle_troll_tribes/dungeons/registry.py`
- Modify: `games/jungle_troll_tribes/dungeons/types/bear_den.py`

- [ ] **Step 1: Create cave_roomkit.py**

```python
# games/jungle_troll_tribes/dungeons/tilesets/cave_roomkit.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[4] / "omwtools"))

from omwtools.dungeons.room_kit import RoomKit, RoomVariant
from omwtools.dungeons.tile_spec import TileSet, TileDef

# 10 pre-built room variants
cave_roomkit = RoomKit(
    name="cave",
    tile_size=256.0,
    room_tiles=4,
    room_height=256.0,
    variants=[
        RoomVariant(mesh="omwdg\\cave_room_a.dae", stat_id="jtt_cave_room_a"),
        RoomVariant(mesh="omwdg\\cave_room_b.dae", stat_id="jtt_cave_room_b"),
        RoomVariant(mesh="omwdg\\cave_room_c.dae", stat_id="jtt_cave_room_c"),
        RoomVariant(mesh="omwdg\\cave_room_d.dae", stat_id="jtt_cave_room_d"),
        RoomVariant(mesh="omwdg\\cave_room_e.dae", stat_id="jtt_cave_room_e"),
        RoomVariant(mesh="omwdg\\cave_room_f.dae", stat_id="jtt_cave_room_f"),
        RoomVariant(mesh="omwdg\\cave_room_g.dae", stat_id="jtt_cave_room_g"),
        RoomVariant(mesh="omwdg\\cave_room_h.dae", stat_id="jtt_cave_room_h"),
        RoomVariant(mesh="omwdg\\cave_room_i.dae", stat_id="jtt_cave_room_i"),
        RoomVariant(mesh="omwdg\\cave_room_j.dae", stat_id="jtt_cave_room_j"),
    ],
    corridor_mesh="omwdg\\cave_corridor.dae",
    corridor_stat_id="jtt_cave_corridor",
)

# Existing tile pieces — reused for corridor sections between rooms
cave_corridor_tiles = TileSet(
    name="cave",
    tile_size=256.0,
    room_height=256.0,
    tiles={
        "floor":   TileDef(mesh="omwdg\\cave_floor.dae",   stat_id="jtt_cave_floor"),
        "wall":    TileDef(mesh="omwdg\\cave_wall.dae",    stat_id="jtt_cave_wall"),
        "corner":  TileDef(mesh="omwdg\\cave_corner.dae",  stat_id="jtt_cave_corner"),
        "pillar":  TileDef(mesh="omwdg\\cave_pillar.dae",  stat_id="jtt_cave_pillar"),
        "doorway": TileDef(mesh="omwdg\\cave_doorway.dae", stat_id="jtt_cave_doorway"),
        "ceiling": TileDef(
            mesh="omwdg\\cave_ceiling.dae",
            stat_id="jtt_cave_ceiling",
            z_offset=256.0,
        ),
    },
)
```

- [ ] **Step 2: Update registry.py**

Replace current `registry.py` content:

```python
# games/jungle_troll_tribes/dungeons/registry.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3] / "omwtools"))

from omwtools.dungeons.tile_spec import TileSet
from omwtools.dungeons.room_kit import RoomKit
from omwtools.dungeons.dungeon_spec import DungeonSpec
from .tilesets.cave import cave
from .tilesets.cave_roomkit import cave_roomkit
from .types.bear_den import bear_den
from .types.spider_cave import spider_cave
from .types.troll_lair import troll_lair

TILESETS: dict[str, TileSet | RoomKit] = {
    "cave": cave,
    "cave_roomkit": cave_roomkit,
}
DUNGEON_TYPES: dict[str, DungeonSpec] = {
    "bear_den": bear_den,
    "spider_cave": spider_cave,
    "troll_lair": troll_lair,
}
```

- [ ] **Step 3: Update bear_den.py — fix room_size and tileset**

```python
# games/jungle_troll_tribes/dungeons/types/bear_den.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[4] / "omwtools"))
from omwtools.dungeons.dungeon_spec import DungeonSpec

bear_den = DungeonSpec(
    name="bear_den", game_prefix="jtt", tileset="cave_roomkit",
    room_count=(1, 3), room_size=(4, 4), pool_size=8,
    exterior_return_pos={"cell": "", "x": 4096, "y": 4096, "z": 210},
    creature_pool=["jtt_bear", "jtt_wolf"],
    creatures_per_room=(1, 2),
    loot_containers=["jtt_loot_small", "jtt_loot_medium"],
    loot_per_room=(0, 1),
)
```

- [ ] **Step 4: Fix cmd_dungeon.py import of corridor tiles**

The `_cave_corridor_tileset` import in Task 4 needs updating. In `cmd_dungeon.py`, after loading the registry, also load the corridor tiles from the kit definition:

```python
    if isinstance(kit_or_tileset, RoomKit):
        from omwtools.dungeons.pool_builder import build_pool_roomkit
        # Load corridor TileSet from the game's cave_roomkit module
        corridor_tiles = registry.get("CORRIDOR_TILES", {}).get(spec.tileset)
        if corridor_tiles is None:
            print(f"Error: no CORRIDOR_TILES entry for tileset '{spec.tileset}'",
                  file=sys.stderr)
            sys.exit(1)
        records, layouts, cell_ids = build_pool_roomkit(
            spec, kit_or_tileset, corridor_tiles, start_seed=start_seed
        )
```

And add to `registry.py`:

```python
from .tilesets.cave_roomkit import cave_corridor_tiles

CORRIDOR_TILES: dict[str, TileSet] = {
    "cave_roomkit": cave_corridor_tiles,
}
```

And update `_load_registry()` in cmd_dungeon.py to return the new key:

```python
    return {
        "TILESETS": reg_mod.TILESETS,
        "DUNGEON_TYPES": reg_mod.DUNGEON_TYPES,
        "CORRIDOR_TILES": getattr(reg_mod, "CORRIDOR_TILES", {}),
    }
```

- [ ] **Step 5: Run tests**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run pytest -x -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add games/jungle_troll_tribes/dungeons/tilesets/cave_roomkit.py \
        games/jungle_troll_tribes/dungeons/registry.py \
        games/jungle_troll_tribes/dungeons/types/bear_den.py \
        omwtools/omwtools/cli/cmd_dungeon.py \
        omwtools/omwtools/dungeons/pool_builder.py
git commit -m "feat: cave RoomKit definition, registry wiring, bear_den uses cave_roomkit"
```

---

## Task 6: Generate Dungeons + Rebuild Game

**Files:**
- Regenerate: `games/jungle_troll_tribes/records/19_dungeons.json`

- [ ] **Step 1: Generate dungeon pool**

```bash
cd /home/mike/Documents/grimoires/openmw-ai-cs/omwtools
poetry run omw dungeon generate \
  --game jungle_troll_tribes \
  --type bear_den \
  --output ../games/jungle_troll_tribes/records/ \
  --no-deploy
```

Expected:
```
Written 14 records to .../jtt_bear_den.json
Written Lua config to .../dungeon_config_bear_den.lua
```

- [ ] **Step 2: Rename output to digit-prefixed filename**

```bash
mv -f ../games/jungle_troll_tribes/records/jtt_bear_den.json \
      ../games/jungle_troll_tribes/records/19_dungeons.json
```

- [ ] **Step 3: Verify refs in generated JSON**

```bash
python3 -c "
import json
data = json.load(open('../games/jungle_troll_tribes/records/19_dungeons.json'))
cells = [r for r in data if r['rec_type'] == 'CELL']
c = cells[0]
refs = c['refs']
room_refs = [r for r in refs if 'cave_room' in r['object_id']]
torch_refs = [r for r in refs if 'torch' in r['object_id']]
print(f'Cells: {len(cells)}, Total refs: {len(refs)}')
print(f'Room mesh refs: {len(room_refs)} — e.g. {room_refs[0][\"object_id\"]}')
print(f'Torch refs: {len(torch_refs)}')
print(f'Ambient: {hex(c[\"ambient\"][\"ambient\"])}')
"
```

Expected: room mesh refs ≥ 1, ambient = `0xffffffff`

- [ ] **Step 4: Rebuild game**

```bash
cd ../games/jungle_troll_tribes
bash build.sh 2>&1 | tail -6
```

Expected: `Game written: .../jungle_troll_tribes.omwgame`

- [ ] **Step 5: Test in OpenMW**

Launch: `flatpak run --command=openmw org.openmw.OpenMW --skip-menu --new-game`
Press **B** → **Cave** → spawn portal → **activate** portal → enter dungeon.

Expected: textured stone rooms visible, bone torch illumination, corridor sections with floor/ceiling connecting rooms.

- [ ] **Step 6: Commit**

```bash
git add games/jungle_troll_tribes/records/19_dungeons.json \
        games/jungle_troll_tribes/scripts/jungle_troll_tribes/dungeon_config_bear_den.lua
git commit -m "feat: regenerate bear_den dungeons with room-kit (10 variants, textured)"
```
