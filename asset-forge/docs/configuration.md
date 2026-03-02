# Configuration

All configuration is loaded from a `.env` file in the project root (or from
environment variables directly). Copy `.env.example` to `.env` and edit it.

```bash
cp .env.example .env
```

Settings are validated by Pydantic at startup. Missing required values
(currently only `ANTHROPIC_API_KEY`) raise an error immediately.

---

## Full reference

### Anthropic / Claude

#### `ANTHROPIC_API_KEY`
**Required.** Your Anthropic API key.
Obtain one at [console.anthropic.com](https://console.anthropic.com/).

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

#### `ORCHESTRATOR_MODEL`
**Default:** `claude-sonnet-4-6`

The Claude model used for asset planning. The orchestrator call consumes
roughly 2 000–4 000 input tokens and 1 000–2 000 output tokens per run.

Tested models:

| Model | Speed | Quality | Cost |
|---|---|---|---|
| `claude-sonnet-4-6` | Fast | Excellent | Medium |
| `claude-opus-4-6` | Slower | Best | Higher |
| `claude-haiku-4-5-20251001` | Very fast | Good | Low |

Haiku is sufficient for simple item types (MISC, INGR, STAT). Use Sonnet or
Opus for complex types where prompt quality matters more (CREA, NPC_, WEAP
with unusual subtypes).

```
ORCHESTRATOR_MODEL=claude-sonnet-4-6
```

#### `ORCHESTRATOR_MAX_TOKENS`
**Default:** `4096`

Maximum tokens for the Claude response. The `AssetPlan` JSON is typically
800–1 500 tokens. Increase this if you hit truncation errors on complex types.

```
ORCHESTRATOR_MAX_TOKENS=4096
```

---

### Stable Diffusion

#### `SD_API_URL`
**Default:** `http://localhost:7860`

Base URL of your local Stable Diffusion API server. Supports:
- [AUTOMATIC1111 SD-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [SD-WebUI Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)
- Any API-compatible fork

Start with `--api` flag to enable the REST API.

```
SD_API_URL=http://localhost:7860
```

#### `SD_MODEL_CHECKPOINT`
**Default:** *(not set — uses whatever checkpoint is currently loaded)*

If set, Asset Forge will temporarily override the loaded checkpoint for each
request and restore it afterwards. Use the filename as it appears in the
WebUI's model dropdown.

```
SD_MODEL_CHECKPOINT=dreamshaper_8.safetensors
```

Leave unset if you want to control the checkpoint manually in the WebUI.

#### `SD_TIMEOUT`
**Default:** `120.0` (seconds)

HTTP timeout for SD API calls. Increase if you use many steps or a slow GPU.
A 50-step 1024×1024 generation can take 60–90 s on a mid-range GPU.

```
SD_TIMEOUT=180.0
```

---

### Hunyuan3D

#### `HUNYUAN3D_API_URL`
**Default:** `http://localhost:8080`

Base URL of the Hunyuan3D Gradio server started by `scripts/start_hunyuan3d.sh`.
Must match the `--port` passed to `app.py`.

```
HUNYUAN3D_API_URL=http://localhost:8080
```

#### `HUNYUAN3D_TIMEOUT`
**Default:** `600.0` (seconds)

Mesh generation is slow. At 50 steps on a 24 GB GPU, expect 3–8 minutes per
mesh. Increase this if you raise `hunyuan3d_steps` beyond the default.

```
HUNYUAN3D_TIMEOUT=900.0
```

---

### AudioCraft

#### `AUDIOGEN_MODEL`
**Default:** `facebook/audiogen-medium`

HuggingFace model ID for AudioGen. Weights are downloaded on first use and
cached in `~/.cache/huggingface/`.

Available models:

| Model ID | Size | Quality |
|---|---|---|
| `facebook/audiogen-medium` | ~2.5 GB | Good — recommended |

Only the medium model is publicly available as of 2025.

```
AUDIOGEN_MODEL=facebook/audiogen-medium
```

#### `AUDIOGEN_DEVICE`
**Default:** `cuda`

PyTorch device for AudioGen inference. Falls back to `cpu` automatically
if CUDA is unavailable when set to `cuda`.

```
AUDIOGEN_DEVICE=cuda   # or: cpu
```

---

### Blender

#### `BLENDER_PATH`
**Default:** `/usr/bin/blender`

Absolute path to the Blender executable. Blender must be version 3.6 or later.

Common locations:

```bash
# Linux (package manager install)
BLENDER_PATH=/usr/bin/blender

# Linux (portable / Steam)
BLENDER_PATH=/opt/blender/blender

# Snap install
BLENDER_PATH=/snap/bin/blender
```

Verify your path:
```bash
blender --version
```

```
BLENDER_PATH=/usr/bin/blender
```

---

### Output

#### `OUTPUT_DIR`
**Default:** `./output`

Root directory where all generated asset bundles are written. Each run creates
a subdirectory named after `object_id`:

```
output/
├── ancient_iron_sword/
│   ├── ancient_iron_sword.dae
│   └── ...
└── shadow_vial/
    └── ...
```

Supports `~` expansion.

```
OUTPUT_DIR=./output
OUTPUT_DIR=~/game-assets/generated
```

---

## Per-run quality parameters

These are not `.env` settings — they live in the `AssetPlan` produced by
Claude and can be influenced by describing quality in your prompt, or by
editing the plan JSON from `forge plan` and piping it into the pipeline
(planned feature).

| Parameter | Location | Default | Effect |
|---|---|---|---|
| `sd_steps` | AssetPlan | 30 | SD inference steps |
| `sd_cfg_scale` | AssetPlan | 7.0 | SD prompt adherence |
| `hunyuan3d_steps` | AssetPlan | 50 | Hunyuan3D diffusion steps |
| `icon_size` | AssetPlan | 128 | Icon resolution (px, square) |
| `texture_size` | AssetPlan | 512 | Texture resolution (px, square) |

---

## Example .env (full)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Claude
ORCHESTRATOR_MODEL=claude-sonnet-4-6
ORCHESTRATOR_MAX_TOKENS=4096

# Stable Diffusion
SD_API_URL=http://localhost:7860
SD_MODEL_CHECKPOINT=dreamshaper_8.safetensors
SD_TIMEOUT=180.0

# Hunyuan3D
HUNYUAN3D_API_URL=http://localhost:8080
HUNYUAN3D_TIMEOUT=600.0

# AudioCraft
AUDIOGEN_MODEL=facebook/audiogen-medium
AUDIOGEN_DEVICE=cuda

# Blender
BLENDER_PATH=/usr/bin/blender

# Output
OUTPUT_DIR=./output
```
