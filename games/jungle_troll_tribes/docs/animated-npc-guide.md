# Programmatic Generation of Animated NPC Models for OpenMW

A practical guide from zero to a walking, collidable troll NPC — generated entirely in code.

---

## What you get at the end

A custom race NPC that:
- renders with your own body geometry
- animates using OpenMW's Bip01 skeleton (walk, idle, combat, death)
- appears in an exterior cell with AI wander behaviour
- is fully defined in JSON records, built via `omw import` / `omw write`

No hand-modelling required. No Blender GUI. Everything runs headless.

---

## The pipeline at a glance

```
gen_troll_body.py          gen_meshes.py
(Blender headless)         (Blender headless)
       │                          │
       ▼                          ▼
meshes/jtt/troll_body.dae   meshes/jtt/*.dae
  (rigged to Bip01)          (static objects)
       │
       ▼
records/17_body_parts.json  ← BODY record, part_index=4
records/11_npcs.json        ← NPC_ record, race=troll
       │
       ▼
omw import → omw write → jungle_troll_tribes.omwgame
       │
       ▼
flatpak run org.openmw.OpenMW --skip-menu --new-game
```

Two Blender scripts, a handful of JSON records, one build command.

---

## Part 1: The skeleton you must not ignore

OpenMW animates humanoid NPCs with a fixed skeleton called **Bip01**. The skeleton lives in two files that you copy verbatim from `template.omwgame`:

| File | Size | Role |
|------|------|------|
| `meshes/BasicPlayer.dae` | ~54 MB | Bip01 skeleton + all animation keyframes |
| `meshes/BasicPlayer.txt` | ~21 KB | Animation action definitions |
| `meshes/BasicPlayerBody.dae` | ~591 KB | Reference body mesh rigged to Bip01 |

These three files must live in your game's `meshes/` root (not in a subdirectory). OpenMW hard-codes the lookup paths.

```bash
# Copy from the template game data — adjust path to your OpenMW install
cp template.omwgame/data/meshes/BasicPlayer.dae    meshes/
cp template.omwgame/data/meshes/BasicPlayer.txt    meshes/
cp template.omwgame/data/meshes/BasicPlayerBody.dae meshes/
```

Without `BasicPlayer.dae`, body part meshes pile at world origin — the skeleton they attach to doesn't exist.

### Bone name reference

The key Bip01 bones and their approximate positions (in armature-local units, ~cm):

```
Bip01_Head       ~(0,  2.5, 120)   ← head attachment
Bip01_Neck       ~(0, -0.3, 113)
Bip01_Spine2     ~(0,  0.8, 102)   ← upper chest
Bip01_Spine1     ~(0,  2.0,  90)
Bip01_Spine      ~(0,  3.4,  79)
Bip01_Pelvis     ~(0,  2.3,  66)   ← root of legs
Bip01_L_Upperarm / Bip01_R_Upperarm
Bip01_L_Forearm  / Bip01_R_Forearm
Bip01_L_Hand     / Bip01_R_Hand
Bip01_L_Thigh    / Bip01_R_Thigh
Bip01_L_Calf     / Bip01_R_Calf
Bip01_L_Foot     / Bip01_R_Foot
```

Read actual positions at runtime from the imported armature — don't hardcode them:

```python
def bone_pos(arm_obj, name):
    b = arm_obj.data.bones.get(name)
    return b.head_local.copy() if b else Vector((0, 0, 0))
```

---

## Part 2: Static placeholder meshes

Most game objects (weapons, armour, environment props, creatures) don't need a skeleton. They're STAT/WEAP/ARMO/CREA records that reference a `.dae` file with no rigging.

`gen_meshes.py` generates all 37 of these in one Blender headless pass.

### Pattern

Every mesh follows the same three-step pattern:

```python
def mk_bone_club():
    clear()                                          # 1. wipe scene
    m = mat("club", 0.82, 0.78, 0.65)               # 2. create material
    bpy.ops.mesh.primitive_cylinder_add(             # 3. add primitives
        vertices=6, radius=6, depth=88,
        location=(0, 0, 44))
    apply_mat(bpy.context.active_object, m)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=8, ring_count=6,
        radius=20, location=(0, 0, 100))
    apply_mat(bpy.context.active_object, m)
    export("bone_club.dae")                          # 4. export COLLADA
```

### Scale reference

OpenMW game units: **1 unit ≈ 1.4 cm**. Player height ≈ 140 units.

| Object | Typical radius / depth |
|--------|------------------------|
| Troll hut | radius=190, depth=120 |
| Totem pole | radius=18, depth=260 |
| Weapon (club) | radius=6, depth=88 |
| Pickable item (berry) | radius=4–12 |

### Run it

```bash
blender --background --python gen_meshes.py
```

Writes 37 `.dae` files to `meshes/jtt/`. Takes ~15 seconds.

### Mesh path convention for static objects

Static records (STAT, WEAP, ARMO, CONT, LIGH, DOOR, CREA, etc.) use paths **including** the `meshes\` prefix:

```json
{ "rec_type": "STAT", "record_id": "jtt_totem_pole",
  "mesh": "meshes\\jtt\\totem_pole.dae" }
```

OpenMW does **not** prepend anything. You give the full relative path from the data directory.

---

## Part 3: Rigged NPC body mesh

A rigged body is fundamentally different from a static prop. It needs:

1. A mesh built in the coordinate space of the Bip01 armature
2. Vertex groups named after Bip01 bones
3. An Armature modifier pointing at the Bip01 object
4. Both mesh + armature exported together as COLLADA

`gen_troll_body.py` does all of this.

### Step-by-step walkthrough

#### 1. Import the template body — for the skeleton only

```python
bpy.ops.wm.collada_import(filepath=TEMPLATE_BODY)

# Delete the template mesh — keep only the armature
for obj in list(bpy.data.objects):
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)
    elif obj.type == 'ARMATURE':
        arm_obj = obj
```

You're stealing the Bip01 armature's bone positions. You don't care about the human body mesh that came with it.

#### 2. Read bone positions into Python variables

```python
PELVIS = bone_pos(arm_obj, "Bip01_Pelvis")
SPINE  = bone_pos(arm_obj, "Bip01_Spine")
HEAD   = bone_pos(arm_obj, "Bip01_Head")
L_UPPER = bone_pos(arm_obj, "Bip01_L_Upperarm")
# ... etc.
```

All geometry is built relative to these positions, so the troll body fits the skeleton regardless of which version of BasicPlayerBody.dae you started with.

#### 3. Build body from ellipsoid segments

```python
def add_body_segment(bm_target, center, radius_x, radius_y, height, segments=12):
    """Add a UV sphere scaled to an ellipsoid, merged into bm_target."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments,
                              v_segments=max(6, segments//2), radius=1.0)
    for v in bm.verts:
        v.co.x *= radius_x
        v.co.y *= radius_y
        v.co.z *= height / 2.0
        v.co += center
    bm.to_mesh(temp_mesh)
    bm_target.from_mesh(temp_mesh)
    bm.free()
```

One segment per body region — head, neck, upper chest, mid torso, belly, pelvis, upper arms, forearms, hands, thighs, calves, feet. Overlapping segments are merged with `bmesh.ops.remove_doubles`.

Troll proportions used in JTT:

| Region | radius_x | radius_y | height |
|--------|----------|----------|--------|
| Head | 8.0 | 8.5 | 14.0 |
| Chest | 16.0 | 11.0 | 16.0 |
| Upper arm | 5.0 | 5.0 | (bone length × 0.9) |
| Thigh | 6.5 | 6.5 | (bone length × 0.9) |

#### 4. Weight vertices by proximity

Instead of painting weights by hand, assign them algorithmically — each vertex goes to the nearest bone region, with weight falling off linearly within the bone's radius:

```python
BONE_REGIONS = {
    "Bip01_Head":    {"center": HEAD + Vector((0,1,5)), "radius": 12.0},
    "Bip01_Spine2":  {"center": midpoint(SPINE2, NECK), "radius": 18.0},
    "Bip01_L_Thigh": {"center": midpoint(L_THIGH, L_CALF), "radius": 14.0},
    # ...
}

for vi, vert in enumerate(me.vertices):
    weights = {}
    for bone_name, region in BONE_REGIONS.items():
        dist = (vert.co - region["center"]).length
        if dist < region["radius"]:
            weights[bone_name] = 1.0 - (dist / region["radius"])

    # Normalize and assign
    total = sum(weights.values())
    for bone_name, w in weights.items():
        troll_obj.vertex_groups[bone_name].add([vi], w / total, 'REPLACE')
```

This produces adequate deformation for blocky, primitive-based geometry. For smooth organic shapes you'd want heat diffusion or manual painting — but for placeholder trolls it works fine.

#### 5. Wire the armature modifier

```python
troll_obj.parent = arm_obj
mod = troll_obj.modifiers.new("Armature", 'ARMATURE')
mod.object = arm_obj
```

#### 6. Export mesh + armature together

```python
bpy.ops.wm.collada_export(
    filepath=OUTPUT_FILE,
    apply_modifiers=True,
    selected=True,
    include_armatures=True,
    deform_bones_only=True,   # omit control/helper bones
)
```

`deform_bones_only=True` keeps the export clean — only the Bip01 deform bones are written, not IK targets or helper objects.

### Run it

```bash
blender --background --python gen_troll_body.py
```

Output: `meshes/jtt/troll_body.dae` (~200–400 KB). Takes ~30 seconds.

---

## Part 4: BODY records

A BODY record maps a mesh file to a specific body slot on a specific race.

```json
{
  "rec_type": "BODY",
  "record_id": "jtt_troll_body",
  "mesh": "jtt/troll_body.dae",
  "name": "troll",
  "part_index": 4,
  "vampire": 0,
  "part_flags": 0,
  "part_type": 0,
  "flags": 0
}
```

### Critical path difference

BODY mesh paths **do NOT include `meshes\`**. OpenMW prepends `meshes/` automatically for body parts only:

```
STAT mesh:  "meshes\\jtt\\totem_pole.dae"   ← full path
BODY mesh:  "jtt/troll_body.dae"             ← no meshes\ prefix
```

Get this wrong and the NPC renders invisible with no error message.

### Part indices

| Index | Body part | Bip01 bones |
|-------|-----------|-------------|
| 0 | Head | Bip01_Head |
| 1 | Hair | Bip01_Head |
| 2 | Neck | Bip01_Neck |
| 3 | Chest | Bip01_Spine, Bip01_Spine1, Bip01_Spine2 |
| 4 | Groin / lower body | Bip01_Pelvis, legs |
| 5 | Skirt | Bip01_Pelvis |
| 6 | Right hand | Bip01_R_Hand |
| 7 | Left hand | Bip01_L_Hand |
| 8 | Right wrist | Bip01_R_Forearm |
| 9 | Left wrist | Bip01_L_Forearm |
| 10 | Shield | Bip01_L_Forearm |
| 11 | Right forearm | Bip01_R_Forearm |
| 12 | Left forearm | Bip01_L_Forearm |
| 13 | Right upper arm | Bip01_R_Upperarm |
| 14 | Left upper arm | Bip01_L_Upperarm |
| 15 | Right foot | Bip01_R_Foot |
| 16 | Left foot | Bip01_L_Foot |
| 17 | Right ankle | Bip01_R_Calf |
| 18 | Left ankle | Bip01_L_Calf |
| 19 | Right knee | Bip01_R_Calf |
| 20 | Left knee | Bip01_L_Calf |
| 21 | Right upper leg | Bip01_R_Thigh |
| 22 | Left upper leg | Bip01_L_Thigh |
| 23 | Right pauldron | Bip01_R_Upperarm |
| 24 | Left pauldron | Bip01_L_Upperarm |
| 25 | Weapon | Bip01_R_Hand |
| 26 | Tail | (custom bone) |

### Minimal viable body setup

The single-BODY approach: one BODY record at part_index=4 (groin) covering the entire body. OpenMW uses it for the full silhouette. This is what JTT uses:

```json
[{
  "rec_type": "BODY",
  "record_id": "jtt_troll_body",
  "mesh": "jtt/troll_body.dae",
  "name": "troll",
  "part_index": 4,
  "part_type": 0,
  "flags": 0
}]
```

`name` must match the race ID (case-insensitive). OpenMW looks up body parts by race when rendering an NPC.

---

## Part 5: NPC_ records

```json
{
  "rec_type": "NPC_",
  "record_id": "jtt_forest_warrior",
  "name": "Forest Troll Warrior",
  "mesh": "",
  "race": "troll",
  "class_id": "troll_warrior",
  "faction": "forest_trolls",
  "head": "",
  "hair": "",
  "script": "",
  "npc_flags": 16,
  "npdt_autocalc": {
    "level": 5,
    "disposition": 50,
    "reputation": 0,
    "rank": 0,
    "gold": 20
  },
  "inventory": [
    {"count": 1, "item_id": "jtt_bone_club"},
    {"count": 1, "item_id": "jtt_tribal_loincloth"}
  ],
  "spells": [],
  "ai_data": {
    "hello": 0,
    "fight": 70,
    "flee": 20,
    "alarm": 80,
    "services": 0
  },
  "ai_packages": [
    {"type": "AI_W", "raw_hex": "0001050000000000000000000100"}
  ],
  "transport": [],
  "flags": 0
}
```

### Field notes

**`npc_flags: 16`** — This is `NPC_FLAG_AUTOCALC` (bit 0x0010). Stats are computed from level and class. Without it, you must supply a full 52-byte NPDT stat block with all skills and attributes. Use `16` for autocalc unless you're authoring a specific named character.

**`head` and `hair`** — For the Player NPC, empty strings are fine (the player has no visible head in first-person). For all other NPCs you need valid BODY record IDs here **or OpenMW will freeze** when the NPC enters view. If your race only has a full-body BODY record (part_index=4), set head/hair to the same body record ID:

```json
"head": "jtt_troll_body",
"hair": "jtt_troll_body"
```

**`hello: 0`** — This is not optional in a standalone game without `base_anim.nif` and the full Morrowind audio set. Any NPC with `hello > 0` will trigger OpenMW's dialogue greeting system, which attempts to play a voice line. That lookup chain eventually faults in a standalone game. Keep `hello: 0`; players can still initiate dialogue by clicking.

**`ai_packages` / AI_W hex** — The wander package is 14 bytes (28 hex chars):

```
0001 05 0000 0000 0000 0000 0100 00
│    │  └──── idle chances (8 bytes) ────┘  └trailing
│    └ wander distance tier (0=minimal)
└ range (1 = small radius)
```

Always append the trailing `00` byte. 13-byte (26 char) strings will be rejected.

---

## Part 6: Required engine records

A fully standalone `.omwgame` (no dependency on Morrowind.esm) needs these records before any NPC will work:

### VFX statics (always required)

```json
[
  {"rec_type":"STAT","record_id":"VFX_DefaultHit",  "mesh":""},
  {"rec_type":"STAT","record_id":"VFX_DefaultCast", "mesh":""},
  {"rec_type":"STAT","record_id":"VFX_DefaultArea",  "mesh":""}
]
```

Empty mesh strings are fine. OpenMW just needs the record to exist.

### Marker statics

```json
[
  {"rec_type":"STAT","record_id":"divinemarker",  "mesh":"meshes\\marker_divine.dae"},
  {"rec_type":"STAT","record_id":"doormarker",    "mesh":"meshes\\marker_door.dae"},
  {"rec_type":"STAT","record_id":"northmarker",   "mesh":"meshes\\marker_north.dae"},
  {"rec_type":"STAT","record_id":"templemarker",  "mesh":"meshes\\marker_temple.dae"},
  {"rec_type":"STAT","record_id":"travelmarker",  "mesh":"meshes\\marker_travel.dae"}
]
```

Copy the marker meshes from template or generate minimal ones with `gen_meshes.py`. Without them, OpenMW logs errors when placing door and travel markers.

### Startup scripts

```json
[
  {"rec_type":"SCPT","record_id":"Main",
   "source":"Begin Main\n; game init\nEnd Main\n"},
  {"rec_type":"SCPT","record_id":"EnableMenus",
   "source":"Begin EnableMenus\nEnd EnableMenus\n"}
]
```

OpenMW calls `startScript("Main")` at new-game init. Without it, the fallback init path requires VFX statics (see above) and can crash on certain engine paths.

### GMSTs and engine globals

Export all 1521 GMSTs from a working `template.omwgame`:

```bash
omw dump --rec-type GMST > records/00a_engine_gmst.json
```

Add 10 engine GLOBs manually:

```json
[
  {"rec_type":"GLOB","record_id":"Month",      "type":"l","value":1.0},
  {"rec_type":"GLOB","record_id":"Day",        "type":"l","value":1.0},
  {"rec_type":"GLOB","record_id":"Year",       "type":"l","value":427.0},
  {"rec_type":"GLOB","record_id":"GameHour",   "type":"f","value":8.0},
  {"rec_type":"GLOB","record_id":"DaysPassed", "type":"l","value":0.0},
  {"rec_type":"GLOB","record_id":"CharGenState","type":"f","value":1.0},
  {"rec_type":"GLOB","record_id":"Random100",  "type":"f","value":0.0},
  {"rec_type":"GLOB","record_id":"PCRace",     "type":"l","value":0.0},
  {"rec_type":"GLOB","record_id":"PCVampire",  "type":"l","value":0.0},
  {"rec_type":"GLOB","record_id":"PCWerewolf", "type":"l","value":0.0}
]
```

`CharGenState=1.0` skips character creation and drops the player directly into the world.

---

## Part 7: Build and test

### build.sh

```bash
#!/bin/bash
set -e
DB="jungle_troll_tribes.db"
OMWGAME="jungle_troll_tribes.omwgame"

rm -f "$DB" "$OMWGAME"

# Seed the mods table (required before import — foreign key constraint)
omw --db "$DB" query "INSERT INTO mods (id, filename, load_order, is_master, author, description, version) VALUES (1, '$OMWGAME', 1, 0, 'dev', 'JTT', '0.1')"

# Import all record JSON files in order
for f in records/*.json; do
  omw --db "$DB" import "$f"
done

# Write the game file
omw --db "$DB" write --output "$OMWGAME"

echo "Done: $OMWGAME"
```

### Generate meshes first

```bash
# Static meshes (weapons, environment, creatures, placeholder body parts)
blender --background --python gen_meshes.py

# Rigged troll body (requires BasicPlayerBody.dae present in meshes/)
blender --background --python gen_troll_body.py
```

### Launch

```bash
flatpak run --command=openmw org.openmw.OpenMW \
  --skip-menu \
  --new-game
```

### openmw.cfg

```ini
data=/path/to/games/jungle_troll_tribes
content=jungle_troll_tribes.omwgame
```

Only one content line. No Morrowind.esm.

---

## Part 8: Troubleshooting checklist

| Symptom | Cause | Fix |
|---------|-------|-----|
| NPC body parts at origin | Missing BasicPlayer.dae | Copy from template |
| NPC invisible | BODY mesh path includes `meshes\` prefix | Remove prefix from BODY records only |
| Game freezes when NPC enters view | `head` or `hair` field is empty string on non-Player NPC | Set to a valid BODY record ID |
| Game freezes when clicking NPC | `hello > 0` in ai_data | Set `hello: 0` |
| Wander package rejected | AI_W hex is 26 chars (13 bytes) | Append `00` → 28 chars (14 bytes) |
| Container rejected | `cont_flags: 0` | Set `cont_flags: 8` (normal container bit) |
| OpenMW floats at sea level | No LAND records | Generate flat LAND or use CELL with interior flag |
| NPC stats ignored | `npc_flags: 0` instead of `16` | Set `npc_flags: 16` for autocalc |
| TES3 duplicate record error | TES3 header imported as typed record | `import_.py` must skip `rec_type == "TES3"` |

---

## Part 9: Going further

### Multiple body parts

For races with separate head mesh, hair mesh, and body mesh — add three BODY records:

```json
[
  {"rec_type":"BODY","record_id":"jtt_troll_head",
   "mesh":"jtt/troll_head.dae","name":"troll","part_index":0},
  {"rec_type":"BODY","record_id":"jtt_troll_hair",
   "mesh":"jtt/troll_hair.dae","name":"troll","part_index":1},
  {"rec_type":"BODY","record_id":"jtt_troll_groin",
   "mesh":"jtt/troll_body.dae","name":"troll","part_index":4}
]
```

Then wire NPC_ records:
```json
"head": "jtt_troll_head",
"hair": "jtt_troll_hair"
```

### Better vertex weights

The proximity-based weighting in `gen_troll_body.py` works for blocky shapes. For smoother deformation at joints, switch to heat diffusion skinning after mesh creation:

```python
bpy.ops.object.select_all(action='DESELECT')
arm_obj.select_set(True)
troll_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.parent_set(type='ARMATURE_AUTO')  # heat diffuse weights
```

This requires the mesh to be manifold (no open edges) and can be slow on dense meshes.

### Procedural variation

Generate multiple NPC variants from a single base mesh by parameterising body proportions:

```python
TROLL_TYPES = {
    "warrior": {"chest_rx": 16, "chest_h": 18, "thigh_r": 7.0},
    "shaman":  {"chest_rx": 12, "chest_h": 14, "thigh_r": 5.0},
    "elder":   {"chest_rx": 11, "chest_h": 12, "thigh_r": 4.5},
}

for troll_type, params in TROLL_TYPES.items():
    build_troll_body(params, output=f"meshes/jtt/troll_body_{troll_type}.dae")
```

Each variant gets its own BODY record and the NPCs reference the right one via race or directly via a custom BODY record ID.
