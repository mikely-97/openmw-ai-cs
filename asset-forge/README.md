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
