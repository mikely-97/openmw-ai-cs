# Asset Forge

AI-powered pipeline that converts a text description and a record type into a
complete game asset bundle — 3D mesh, PBR texture, inventory icon, and sound
effects — entirely from local models.

```
forge generate WEAP "An ancient elven longsword with silver filigree"
```

```
output/ancient_elven_longsword/
├── ancient_elven_longsword.dae    ← COLLADA mesh, textured
├── ancient_elven_longsword_d.png  ← PBR diffuse texture
├── ancient_elven_longsword.png    ← inventory icon (RGBA, transparent BG)
└── manifest.json                  ← record field defaults + asset paths
```

---

## How it works

Every generation request goes through four stages:

1. **Plan** — Claude reads the type and description, then fills out a structured
   `AssetPlan`: which assets to generate, exact prompts for each tool, and
   suggested record field values (weight, value, subtype, …).

2. **Image** — Stable Diffusion generates a clean reference render of the object
   (used to condition Hunyuan3D) and a separate inventory icon.

3. **Mesh** — Hunyuan3D takes the reference image + a shape prompt and produces
   a 3D mesh, exported directly as COLLADA (`.dae`). Blender then applies the
   texture, UV-unwraps if needed, and re-exports a clean file.

4. **Audio** — AudioCraft AudioGen produces `.wav` sound effects where the
   record type needs them (door open/close, light source ambience, …).

See [docs/architecture.md](docs/architecture.md) for the full data-flow diagram.

---

## Claude Code — autonomous game generation

Asset Forge is designed to be driven by **Claude Code** operating as an
autonomous software agent. Rather than running individual `forge generate`
commands yourself, Claude Code can orchestrate the entire game-development
pipeline end-to-end:

```
Claude Code (agent)
  │
  ├─ Designs game concept → writes JSON record files
  │   (FACT, RACE, CLAS, SPEL, WEAP, NPC_, CELL, … all 39 omwtools types)
  │
  ├─ forge plan TYPE "description"     ← produces AssetPlan JSON per object
  │
  ├─ forge generate TYPE "description" ← produces mesh/texture/icon/sounds
  │
  ├─ omw import records/*.json         ← loads records into SQLite
  │
  ├─ omw validate                      ← checks referential integrity
  │
  └─ omw write → game.omwgame          ← emits binary content file
```

### Demo: Jungle Troll Tribes

The `games/jungle_troll_tribes/` directory in this repository was created
entirely by Claude Code in a single session, without any manual authoring:

- **113 records** across **31 record types** (FACT, RACE, CLAS, GLOB, SPEL,
  ENCH, WEAP, ARMO, CLOT, INGR, ALCH, MISC, BOOK, STAT, ACTI, CONT, LIGH,
  DOOR, CREA, NPC_, SOUN, SNDG, REGN, LEVC, LEVI, DIAL, INFO, SCPT, CELL,
  SKIL, MGEF)
- **Four troll tribes** with distinct factions, classes, spells, and AI
- **Full cell layout** — exterior jungle map + interior Elder's Hut
- **Survival scripts** tracking hunger/warmth globals
- **Levelled lists, dialogue, region weather, sound generators**

Claude Code wrote all 16 record JSON files, the `build.sh` pipeline script,
and (when SD + Hunyuan3D are running) will generate `forge plan` asset bundles
for every static object, weapon, creature, and NPC in the mod.

### Running the demo

```bash
cd games/jungle_troll_tribes
bash build.sh
```

This produces `jungle_troll_tribes.omwgame` — a self-contained OpenMW game
file (no Morrowind.esm required). Configure OpenMW with:

```ini
# openmw.cfg
content=jungle_troll_tribes.omwgame
```

### Driving forge from Claude Code

To have Claude Code generate an asset and import it:

```bash
# Claude Code runs:
forge plan WEAP "A crude bone club made from a large femur"
# → asset_plans/WEAP_bone_club.json  (AssetPlan, no services needed)

forge generate WEAP "A crude bone club made from a large femur"
# → output/bone_club/{bone_club.dae, bone_club_d.png, bone_club.png, manifest.json}

omw --db game.db import output/bone_club/manifest.json --mod-id 1
omw --db game.db write --output game.omwgame --mod-id 1
```

`forge plan` works without SD, Hunyuan3D, or AudioCraft — Claude produces the
full `AssetPlan` (prompts, ESM field defaults, audio specs) as structured JSON.
This is useful for Claude Code to pre-plan all assets before any generation
services are available.

---

## Record types

Asset Forge knows about 19 record types drawn from the ESM game-data format.
Each type has a fixed set of assets it requires:

| Category | Types |
|---|---|
| Static world objects | `STAT`, `ACTI`, `CONT`, `DOOR` |
| Light sources | `LIGH` |
| Inventory items | `MISC`, `BOOK`, `ALCH`, `INGR` |
| Tools | `LOCK`, `PROB`, `APPA`, `REPA` |
| Weapons | `WEAP` |
| Armour / clothing | `ARMO`, `CLOT` |
| Terrain | `LTEX` |
| Characters | `NPC_`, `CREA`, `BODY` |

Run `forge types` for a full table of what each type generates.
See [docs/record-types.md](docs/record-types.md) for the complete reference.

---

## Requirements

### Hardware
- NVIDIA GPU, CUDA 12.1+
- VRAM: 12 GB minimum (shape only); 25 GB for full mesh + texture in Hunyuan3D

### System packages
- Python 3.10–3.12
- [Poetry](https://python-poetry.org/docs/#installation)
- Blender 3.6+ (must be on `$PATH` or set `BLENDER_PATH`)
- `ffmpeg` (required by AudioCraft)

### External services — set up once, run locally
| Service | Purpose | Default port |
|---|---|---|
| [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | Images & textures | 7860 |
| [Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) | 3D mesh generation | 8080 |

Both run as local HTTP servers with no data leaving your machine.

---

## Installation

### 1 — Clone and install Python dependencies

```bash
git clone https://github.com/yourname/asset-forge
cd asset-forge

# Core pipeline (Claude orchestrator + SD + Hunyuan3D + Blender clients)
poetry install

# Audio support (heavy — needs CUDA PyTorch)
# Install PyTorch with CUDA first, then the extras group:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
poetry install -E audio
```

### 2 — Set up Stable Diffusion

```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui ~/sd-webui
cd ~/sd-webui
# Download at least one checkpoint into models/Stable-diffusion/
# then launch:
bash webui.sh --api --nowebui
```

The script `scripts/start_stable_diffusion.sh` wraps this with sensible flags.

### 3 — Set up Hunyuan3D

```bash
git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git ~/hunyuan3d
cd ~/hunyuan3d
python -m venv .venv && source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
pip install git+https://github.com/NVlabs/nvdiffrast.git  # needed for texturing
pip install -e .
```

Model weights (~10 GB) download automatically on first run from HuggingFace.
The script `scripts/start_hunyuan3d.sh` launches the Gradio server.

### 4 — Configure

```bash
cp .env.example .env
$EDITOR .env   # at minimum: set ANTHROPIC_API_KEY
```

See [docs/configuration.md](docs/configuration.md) for every option.

### 5 — Verify

```bash
forge check
```

This pings SD, Hunyuan3D, Blender, AudioCraft, and the Anthropic API in one go.

---

## Usage

### Generate an asset

```bash
forge generate <TYPE> "<description>" [options]
```

**Examples:**

```bash
# Weapon
forge generate WEAP "A bone-handled hunting knife with a serrated edge"

# Container
forge generate CONT "A heavy iron strongbox with a combination lock wheel"

# Light source
forge generate LIGH "An iron wall sconce holding a cluster of tallow candles"

# Door
forge generate DOOR "A grand stone archway door carved with serpent reliefs"

# Terrain texture
forge generate LTEX "Mossy cobblestone path, worn smooth, damp"

# Potion
forge generate ALCH "A squat clay bottle sealed with black wax, labelled in red"

# Static decoration
forge generate STAT "A collapsed stone column, half-buried in sand"
```

**Options:**

| Flag | Description |
|---|---|
| `--output PATH` / `-o` | Override output directory (default: `./output`) |
| `--install PATH` / `-i` | Copy finished assets into a game data directory |
| `--skip-mesh` | Skip Hunyuan3D + reference image (texture/icon only) |
| `--skip-audio` | Skip AudioCraft (useful if audio extras not installed) |

### Preview a plan without generating

Asks Claude to produce the full `AssetPlan` JSON — prompts, ESM defaults,
audio specs — without calling any generator:

```bash
forge plan WEAP "A rusty iron dagger"
```

### List types and their asset requirements

```bash
forge types
```

### Check all services

```bash
forge check
```

---

## Output

Every run writes to `output/<object_id>/`:

```
output/
└── iron_strongbox/
    ├── iron_strongbox.dae        COLLADA mesh (textured, triangulated, Z-up)
    ├── iron_strongbox_d.png      PBR diffuse texture (512×512 or 1024×1024)
    ├── iron_strongbox.png        Inventory icon (128×128, RGBA)
    ├── reference.png             SD reference image used to condition Hunyuan3D
    ├── sounds/
    │   └── iron_strongbox_open.wav   (DOOR / LIGH types only)
    └── manifest.json
```

### manifest.json

```jsonc
{
  "object_id": "iron_strongbox",
  "object_type": "CONT",
  "subtype": null,
  "needs_manual_rigging": false,
  "esm_defaults": {
    "display_name": "Iron Strongbox",
    "weight": 18.0,
    "value": 120,
    "extras": { "capacity": 200.0 }
  },
  "assets": {
    "mesh":    "iron_strongbox/iron_strongbox.dae",
    "texture": "iron_strongbox/iron_strongbox_d.png",
    "icon":    null,
    "sounds":  {}
  },
  "openmw_paths": {
    "mModel": "meshes/forge/iron_strongbox.dae",
    "texture_diffuse": "textures/forge/iron_strongbox_d.png"
  },
  "warnings": []
}
```

`openmw_paths` contains the paths as they should appear in the `.esp` record
fields, relative to the game's Data Files root.

---

## Known limitations

| Limitation | Detail |
|---|---|
| **Character rigging** | `NPC_`, `CREA`, `BODY` — Hunyuan3D outputs static meshes only. Binding the mesh to an animation skeleton requires a manual pass in Blender (Rigify) or an external auto-rigging service (Mixamo). The pipeline generates the mesh and texture and flags the bundle with a warning. |
| **Wearable body-part seams** | `ARMO` / `CLOT` wearable body-part meshes must topologically match the base body at the neck, wrist, and waist seams. Only the held/ground mesh is auto-generated. |
| **Animations** | Not generated. Characters reuse existing animation skeletons. |
| **AudioCraft licence** | Model weights are CC-BY-NC 4.0. Non-commercial use only. |
| **VRAM** | Full Hunyuan3D pipeline (shape + PBR texture) requires ~25 GB VRAM. Use `--low-vram-mode` in `start_hunyuan3d.sh` to fit on 12 GB at reduced quality. |

---

## Documentation index

| File | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Data-flow diagram, module responsibilities, execution order |
| [docs/record-types.md](docs/record-types.md) | Every ESM type: what it is, what assets it needs, all field definitions |
| [docs/generators.md](docs/generators.md) | SD, Hunyuan3D, AudioCraft, Blender — API details and tuning |
| [docs/configuration.md](docs/configuration.md) | Every `.env` variable, its type, default, and effect |

---

## Licence

MIT — see [LICENCE](LICENCE).
Individual tool licences apply: SD WebUI (AGPL-3.0), Hunyuan3D-2 (Tencent community licence), AudioCraft weights (CC-BY-NC 4.0).
