# Record Types Reference

This document describes every ESM record type that Asset Forge supports:
what the record represents in-game, which assets it requires, what fields
the generated `manifest.json` will suggest, and any caveats to be aware of.

---

## ESM format primer

ESM (Elder Scrolls Master) is the binary data format used to define every
object in the game world. Each **record** has a four-character type code
(e.g. `WEAP`, `CONT`) and a set of typed sub-records (fields). Asset Forge
generates the *file assets* those records reference — meshes, textures, icons,
sounds — and outputs a `manifest.json` with suggested values for the record
fields themselves.

**Asset field conventions used throughout this document:**

| Field name | Type | Meaning |
|---|---|---|
| `mModel` | path string | Relative path to the 3D mesh inside `meshes/` |
| `mIcon` | path string | Relative path to the inventory icon inside `icons/` |
| `mScript` | ID string | Script attached to this object (not generated) |
| `mEnchant` | ID string | Enchantment ID (not generated) |

Paths are always relative to the game's **Data Files** root.

---

## Static world objects

### STAT — Static

A purely visual, non-interactive world decoration. No inventory presence,
no scripting, no physics interaction beyond collision.

**When to use it:** architectural elements, rocks, rubble, plants, furniture
that players can't pick up, ambient clutter.

**Generated assets:**
- 3D mesh (`.dae`)
- PBR diffuse texture

**No icon** — STAT objects never appear in inventory.

**Manifest fields:**

| Field | Example |
|---|---|
| `mModel` | `meshes/forge/crumbling_column.dae` |

**Caveats:**
- Collision is derived from the mesh geometry. Keep polygon count reasonable;
  Blender's decimation modifier can reduce it after generation.
- STAT objects can't be enabled/disabled by scripts. Use ACTI for that.

---

### ACTI — Activator

Identical to STAT in asset terms, but the record supports a script and can
be activated by the player (triggering the script). Levers, pressure plates,
shrines, magic circles.

**Generated assets:**
- 3D mesh (`.dae`)
- PBR diffuse texture

**Manifest fields:**

| Field | Example |
|---|---|
| `mModel` | `meshes/forge/stone_lever.dae` |
| `mScript` | *(set manually)* |

---

### CONT — Container

A world object the player can open to access its inventory. Chests, barrels,
sacks, crates, urns.

**Generated assets:**
- 3D mesh (`.dae`) — closed form only
- PBR diffuse texture

**No icon** — containers are not carried in inventory.

**Manifest fields:**

| Field | Example | Notes |
|---|---|---|
| `mModel` | `meshes/forge/iron_chest.dae` | — |
| `mScript` | *(set manually)* | Optional trap/lock script |
| `weight` | `18.0` | Carry capacity in kg |
| `flags` | `0` | Bit 1 = Organic (no placing), Bit 2 = Respawn |

**Caveats:**
- The pipeline generates the **closed** mesh only. An open-state mesh for
  the lid animation requires separate modelling and is not auto-generated.
  Most container implementations use a single static mesh with a scripted
  inventory UI rather than a physical lid animation.

---

### DOOR — Door

A door mesh with open and close sounds. Can teleport the player between
cells (interior ↔ exterior) or simply animate open/closed in-place.

**Generated assets:**
- 3D mesh (`.dae`)
- PBR diffuse texture
- `open` sound (`.wav`)
- `close` sound (`.wav`)

**Manifest fields:**

| Field | Example |
|---|---|
| `mModel` | `meshes/forge/iron_prison_door.dae` |
| `mOpenSound` | `sound/forge/iron_prison_door_open.wav` |
| `mCloseSound` | `sound/forge/iron_prison_door_close.wav` |
| `mScript` | *(set manually)* |

**Caveats:**
- Door meshes should be oriented so that the hinge axis is along the world
  Z-axis. Blender's COLLADA exporter outputs Z-up by default, which is correct.
- The rotation animation (open sweep angle) is defined in the record data,
  not in the mesh. The generated mesh does not include animation keyframes.

---

### LIGH — Light source

A placeable light source. Can be static (torch sconce on a wall) or carryable
(a torch the player picks up). Carryable lights appear in inventory and
require an icon.

**Generated assets:**
- 3D mesh (`.dae`)
- PBR diffuse texture
- Inventory icon (`.png`) — only if the light is carryable (set `flags |= Carry`)
- Ambient sound (`.wav`) — optional crackling/flickering loop

**Manifest fields:**

| Field | Example | Notes |
|---|---|---|
| `mModel` | `meshes/forge/tallow_candle.dae` | — |
| `mIcon` | `icons/forge/tallow_candle.png` | Only if carryable |
| `mSound` | `sound/forge/tallow_candle_ambient.wav` | Optional |
| `weight` | `0.2` | Only relevant if carryable |
| `value` | `5` | Trade value in septims |
| `time` | `300` | Duration in seconds (−1 = infinite) |
| `radius` | `128` | Light radius in game units |
| `color` | `0xFFB060FF` | RGBA packed int (warm orange) |
| `flags` | `Carry \| Flicker` | See flag table below |

**Light flags:**

| Flag | Value | Meaning |
|---|---|---|
| `Dynamic` | 0x001 | Casts dynamic shadows |
| `Carry` | 0x002 | Can be picked up |
| `Negative` | 0x004 | Subtracts from scene light (darkness source) |
| `Flicker` | 0x008 | Flame-like flicker |
| `Fire` | 0x010 | Fire particle effect |
| `OffDefault` | 0x020 | Starts in off state |
| `FlickerSlow` | 0x040 | Slower flicker |
| `Pulse` | 0x080 | Pulse brightness |
| `PulseSlow` | 0x100 | Slower pulse |

---

## Inventory items

All inventory item types share the same asset pattern: mesh + texture + icon.
The icon appears in the player's inventory grid. The mesh appears when the
item is dropped in the world or held in third-person.

### MISC — Miscellaneous item

A catch-all for items that don't fit other categories: keys, lockpicks (non-tool
variant), gems, tokens, quest items.

| Manifest field | Example |
|---|---|
| `mModel` | `meshes/forge/silver_coin.dae` |
| `mIcon` | `icons/forge/silver_coin.png` |
| `weight` | `0.01` |
| `value` | `1` |
| `flags` | `Key` (bit 0) if it's a key |

---

### BOOK — Book or Scroll

A readable item. The mesh represents the closed book or rolled scroll as a
world/inventory object. The record also contains text content (HTML/plain text)
displayed when opened — not generated by Asset Forge.

| Manifest field | Example | Notes |
|---|---|---|
| `mModel` | `meshes/forge/leather_tome.dae` | — |
| `mIcon` | `icons/forge/leather_tome.png` | — |
| `weight` | `1.0` | — |
| `value` | `40` | — |
| `isScroll` | `false` | `true` → render as scroll, not book |
| `skillId` | `-1` | Skill index learned on read (−1 = none) |
| `mEnchant` | *(set manually)* | Optional |

---

### ALCH — Potion

A consumable with one or more magic effects. The mesh is typically a small
bottle, vial, or flask.

| Manifest field | Example |
|---|---|
| `mModel` | `meshes/forge/shadow_vial.dae` |
| `mIcon` | `icons/forge/shadow_vial.png` |
| `weight` | `0.5` |
| `value` | `60` |

Magic effects (`EFCT` sub-records) are not generated — add them manually in
the record editor.

---

### INGR — Ingredient

A raw alchemy ingredient. Up to four magic effects, each tied to a skill and
attribute. The mesh is a small organic or mineral object.

| Manifest field | Example |
|---|---|
| `mModel` | `meshes/forge/ash_pod.dae` |
| `mIcon` | `icons/forge/ash_pod.png` |
| `weight` | `0.1` |
| `value` | `3` |

---

## Tools

All tool types: mesh + texture + icon. Tools have a `quality` (float, 0–100)
and a finite number of `uses` before breaking.

### LOCK — Lockpick

Thin metal tool for opening locked containers/doors. Quality affects success
probability.

| Manifest field | Example |
|---|---|
| `mModel` | `meshes/forge/silver_lockpick.dae` |
| `mIcon` | `icons/forge/silver_lockpick.png` |
| `weight` | `0.1` |
| `value` | `12` |
| `quality` | `0.75` |
| `uses` | `30` |

---

### PROB — Probe

Thin tool for disarming traps. Identical field structure to LOCK.

| Manifest field | Example |
|---|---|
| `mModel` | `meshes/forge/brass_probe.dae` |
| `mIcon` | `icons/forge/brass_probe.png` |
| `weight` | `0.1` |
| `value` | `15` |
| `quality` | `0.5` |
| `uses` | `25` |

---

### APPA — Alchemy Apparatus

Equipment used during alchemy to produce potions. Four distinct subtypes with
distinct silhouettes:

| Subtype | Shape description |
|---|---|
| `MortarPestle` | Squat bowl with a pestle rod |
| `Alembic` | Flask with a long curved neck |
| `Calcinator` | Wide low bowl on a stand |
| `Retort` | Round flask with a downward-curved spout |

| Manifest field | Example |
|---|---|
| `mModel` | `meshes/forge/brass_alembic.dae` |
| `mIcon` | `icons/forge/brass_alembic.png` |
| `weight` | `2.0` |
| `value` | `80` |
| `quality` | `0.6` |
| `type` | `Alembic` |

The `subtype` field in the `AssetPlan` drives which shape Hunyuan3D is prompted
to produce.

---

### REPA — Repair Hammer

Tool for restoring weapon/armour health. Typically a hammer, mallet, or
tongs.

| Manifest field | Example |
|---|---|
| `mModel` | `meshes/forge/iron_hammer.dae` |
| `mIcon` | `icons/forge/iron_hammer.png` |
| `weight` | `1.0` |
| `value` | `25` |
| `quality` | `0.5` |
| `uses` | `20` |

---

## Weapons

### WEAP — Weapon

The `subtype` field determines the shape the orchestrator requests.

**Subtypes and their expected forms:**

| Subtype | Description | Typical length |
|---|---|---|
| `ShortBlade` | One-handed, short. Daggers, knives. | 20–40 cm blade |
| `LongBlade` | One-handed, long. Swords, scimitars. | 60–90 cm blade |
| `Blunt1H` | One-handed blunt. Maces, clubs, wands. | — |
| `Blunt2H` | Two-handed blunt. Mauls, staves (hitting). | — |
| `Blunt2W` | Two-handed wide blunt. Battle staves. | — |
| `Spear` | Two-handed polearm. Spears, halberds. | Long shaft |
| `Axe1H` | One-handed axe. | — |
| `Axe2H` | Two-handed axe. | — |
| `Bow` | Ranged, requires arrow. Curved limbs + string. | — |
| `Crossbow` | Ranged, requires bolt. Horizontal stock. | — |
| `Thrown` | Single-use thrown. Throwing knives, darts. | Small |
| `Arrow` | Ammunition for Bow. Shaft + head + fletching. | Long thin |
| `Bolt` | Ammunition for Crossbow. Short and heavy. | Short |

**Manifest fields:**

| Field | Example |
|---|---|
| `mModel` | `meshes/forge/elven_longsword.dae` |
| `mIcon` | `icons/forge/elven_longsword.png` |
| `weight` | `5.0` |
| `value` | `800` |
| `type` | `LongBlade` |
| `health` | `1200` |
| `speed` | `1.0` |
| `reach` | `1.0` |
| `chop` | `[2, 12]` |
| `slash` | `[5, 15]` |
| `thrust` | `[4, 14]` |
| `flags` | `0` — bit 0 = Magical, bit 1 = Silver |
| `mEnchant` | *(set manually)* |

---

## Armour and Clothing

### ARMO — Armour

An equippable piece of armour. Each armour piece covers one or more body slots.

**Generated assets:**
- Ground/held mesh + texture + icon — **fully generated**
- Body-part meshes (the wearable geometry that attaches to the character
  skeleton) — **not auto-generated** — see caveats below

**Subtypes:**

| Subtype | Body slot |
|---|---|
| `Helmet` | Head |
| `Cuirass` | Chest |
| `LPauldron` | Left shoulder |
| `RPauldron` | Right shoulder |
| `Greaves` | Legs |
| `Boots` | Feet |
| `LGauntlet` | Left hand |
| `RGauntlet` | Right hand |
| `Shield` | Off-hand |
| `LBracer` | Left forearm |
| `RBracer` | Right forearm |

**Manifest fields:**

| Field | Example |
|---|---|
| `mModel` | `meshes/forge/iron_cuirass.dae` |
| `mIcon` | `icons/forge/iron_cuirass.png` |
| `weight` | `18.0` |
| `value` | `350` |
| `type` | `Cuirass` |
| `health` | `600` |
| `armorRating` | `40` |
| `mEnchant` | *(set manually)* |

**Body-part mesh caveats:**

Each armour piece needs separate **body-part** meshes for every body slot it
covers (male and female variants). These meshes must:
- Match the topology of the base body mesh at seam boundaries (neck, wrists, waist)
- Be UV-mapped onto the same texture as the armour piece
- Be weighted to the skeleton's bones

Asset Forge cannot guarantee seam alignment because it has no access to the
base body mesh topology. The pipeline sets `needs_manual_rigging = true` and
generates only the ground/held mesh. Body-part meshes must be created in
Blender using the base body as a reference.

---

### CLOT — Clothing

Identical structure to ARMO. No armour rating, but otherwise the same asset
requirements and caveats.

**Subtypes:**

| Subtype | Body slot |
|---|---|
| `Pants` | Groin/legs |
| `Shoes` | Feet |
| `Shirt` | Chest |
| `Belt` | Waist |
| `Robe` | Full body |
| `LGlove` | Left hand |
| `RGlove` | Right hand |
| `Skirt` | Lower body |
| `Ring` | Finger |
| `Amulet` | Neck |

---

## Terrain

### LTEX — Land Texture

A tileable ground texture painted onto the terrain mesh. No 3D mesh or icon.

**Generated assets:**
- Seamless tileable PBR diffuse texture only

**Manifest fields:**

| Field | Example |
|---|---|
| `texture` | `textures/forge/volcanic_obsidian_d.png` |

The texture is generated with SD's `tiling` flag enabled for seamless edges.
Recommended resolution: 512×512 or 1024×1024 pixels.

---

## Characters

All character types share the same fundamental limitation: Hunyuan3D generates
**static meshes**. Equipping a static mesh to an animation skeleton requires
skinning (assigning bone weights to vertices), which must be done manually.

Asset Forge sets `needs_manual_rigging = true` for all three types and
generates whatever static mesh + texture it can as a reference to work from.

---

### BODY — Body part

A single body-part mesh for a specific race and gender. The record defines
which body slot the mesh occupies, what gender it's for, and whether it's a
skin, clothing, or armour layer.

**Body slot types:**

| Slot | Description |
|---|---|
| `Head` | Head, including face |
| `Hair` | Hair (separate from head) |
| `Neck` | Neck connector |
| `Chest` | Torso |
| `Groin` | Lower torso |
| `Hand` | Hand (wrist to fingertips) |
| `Wrist` | Wrist connector |
| `Forearm` | Lower arm |
| `Upperarm` | Upper arm |
| `Foot` | Foot |
| `Ankle` | Ankle connector |
| `Knee` | Knee connector |
| `Upperleg` | Upper leg |
| `Clavicle` | Shoulder connector |
| `Tail` | Tail (beast races) |

**Mesh types:**

| Type | Value | Used for |
|---|---|---|
| `Skin` | 0 | Base body skin layer |
| `Clothing` | 1 | Clothing body-part layer |
| `Armour` | 2 | Armour body-part layer |

**Manifest fields:**

| Field | Example |
|---|---|
| `mModel` | `meshes/forge/dunmer_head_f.dae` |
| `race` | `Dark Elf` |
| `part` | `Head` |
| `flags` | `Female` (bit 0) |

---

### NPC_ — Non-Player Character

An NPC is not a single mesh — it is a collection of BODY records assembled at
runtime by the engine. Asset Forge generates:
- A head and/or hair mesh + skin texture (static, reference quality)
- Suggested race, class, and faction values in the manifest

The player-visible appearance ultimately comes from the BODY records for the
NPC's race. Equipping the NPC with ARMO/CLOT records provides wearable meshes.

**Manifest fields (selected):**

| Field | Example |
|---|---|
| `mScript` | *(set manually)* |
| `race` | `Nord` |
| `class` | `Warrior` |
| `level` | `10` |
| `attributes` | `{ Strength: 65, Endurance: 60, … }` |
| `skills` | `{ LongBlade: 55, HeavyArmor: 50, … }` |
| `disposition` | `50` |
| `flags` | `Female`, `Essential`, `Respawn` bits |

---

### CREA — Creature

A creature has a single full-body mesh (unlike NPCs which are assembled from
parts). The mesh is expected to be skinned to a creature-specific skeleton.

**Creature types:**

| Type | Examples |
|---|---|
| `Creature` | Animals, monsters |
| `Daedra` | Daedric entities |
| `Undead` | Skeletons, ghosts, vampires |
| `Humanoid` | Humanoid creatures with hands |

**Flags affecting asset needs:**

| Flag | Effect |
|---|---|
| `Bipedal` | Uses humanoid skeleton; can equip weapons |
| `Swims` | Needs swim animation (not generated) |
| `Flies` | Needs fly animation (not generated) |
| `Walks` | Ground locomotion |
| `Weapon` | Can use weapons from inventory |

**Manifest fields (selected):**

| Field | Example |
|---|---|
| `mModel` | `meshes/forge/ash_ghoul.dae` |
| `type` | `Undead` |
| `level` | `12` |
| `soul` | `150` |
| `health` | `200` |
| `mana` | `0` |
| `fatigue` | `400` |
| `attack` | `[[5,20], [5,20], [5,20]]` |
| `flags` | `Walks \| Respawn` |
| `scale` | `1.0` |

---

## Summary table

| Type | Mesh | Texture | Icon | Open sound | Close sound | Ambient sound | Rigging |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| STAT | ✓ | ✓ | | | | | |
| ACTI | ✓ | ✓ | | | | | |
| CONT | ✓ | ✓ | | | | | |
| DOOR | ✓ | ✓ | | ✓ | ✓ | | |
| LIGH | ✓ | ✓ | ✓ | | | ✓ | |
| MISC | ✓ | ✓ | ✓ | | | | |
| BOOK | ✓ | ✓ | ✓ | | | | |
| ALCH | ✓ | ✓ | ✓ | | | | |
| INGR | ✓ | ✓ | ✓ | | | | |
| LOCK | ✓ | ✓ | ✓ | | | | |
| PROB | ✓ | ✓ | ✓ | | | | |
| APPA | ✓ | ✓ | ✓ | | | | |
| REPA | ✓ | ✓ | ✓ | | | | |
| WEAP | ✓ | ✓ | ✓ | | | | |
| ARMO | ✓ | ✓ | ✓ | | | | ⚠ body parts |
| CLOT | ✓ | ✓ | ✓ | | | | ⚠ body parts |
| LTEX | | ✓ | | | | | |
| BODY | ✓ | ✓ | | | | | ⚠ required |
| NPC_ | ✓ | ✓ | | | | | ⚠ required |
| CREA | ✓ | ✓ | | | | | ⚠ required |

⚠ = pipeline generates static mesh only; manual rigging pass required before use in-game.
