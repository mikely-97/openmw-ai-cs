# Architecture

## Overview

Asset Forge is a thin orchestration layer around four AI/3D tools. It never
trains models or stores weights itself — it calls out to locally running
services and combines their outputs into a deployable asset bundle.

```
CLI (forge generate TYPE "description")
│
▼
┌─────────────────────────────────────────────┐
│  Orchestrator  (forge/orchestrator.py)       │
│                                              │
│  Calls Claude with:                          │
│  • Full ESM type catalogue + requirements    │
│  • AssetPlan JSON schema as a forced tool    │
│  → Returns: AssetPlan (all prompts + ESM     │
│    defaults, typed and validated by Pydantic)│
└─────────────┬───────────────────────────────┘
              │ AssetPlan
              ▼
┌─────────────────────────────────────────────┐
│  Pipeline runner  (forge/pipeline.py)        │
│  Executes steps in order, logs via Rich      │
└──┬──────────┬──────────┬────────────────────┘
   │          │          │
   ▼          ▼          ▼
 SD API   Hunyuan3D   AudioCraft
(images)   (mesh)     (sounds)
   │          │
   └────┬─────┘
        │ mesh + texture
        ▼
     Blender
  (UV, texture apply,
   COLLADA sanitize)
        │
        ▼
  AssetBundle → manifest.json
```

---

## Module map

```
forge/
├── cli.py            Entry point. Typer commands: generate, plan, types, check.
│                     Parses args, calls pipeline.run() or orchestrator.plan_assets().
│
├── config.py         Pydantic-settings singleton. Reads .env / env vars.
│                     Imported by every other module as `from .config import settings`.
│
├── orchestrator.py   Claude API client.
│                     Builds system prompt encoding all ESM type knowledge.
│                     Forces Claude to call the `create_asset_plan` tool →
│                     returns a validated AssetPlan.
│
├── pipeline.py       Sequential executor.
│                     Calls generators in order, feeds outputs between steps,
│                     builds AssetBundle, writes manifest.
│
├── types/
│   ├── esm.py        ESMType enum, per-type AssetRequirements dataclasses,
│   │                 and all subtype enums (WeaponSubtype, ArmorSubtype, …).
│   └── plan.py       AssetPlan Pydantic model — the contract between the
│                     orchestrator and the pipeline.
│
├── generators/
│   ├── image.py      Stable Diffusion A1111 API client.
│   │                 Functions: generate_reference_image, generate_icon, generate_texture.
│   ├── mesh.py       Hunyuan3D Gradio client (via gradio_client).
│   │                 Function: generate_mesh → .dae file.
│   │                 Falls back to Blender for format conversion if needed.
│   ├── audio.py      AudioCraft AudioGen wrapper.
│   │                 Lazy-loads model on first call. Optional extras group.
│   └── blender.py    Blender subprocess runner.
│                     Generates and executes Python scripts inside Blender's
│                     embedded interpreter via --background --python.
│
└── output/
    └── bundle.py     AssetBundle dataclass. Collects paths as pipeline runs.
                      Writes manifest.json. Optionally copies files into a
                      game data directory layout.
```

---

## Execution order

For a typical `WEAP` generation:

```
Step 1  orchestrator.plan_assets(WEAP, description)
        → Claude → AssetPlan {
            object_id:           "ancient_elven_longsword"
            sd_reference_prompt: "ancient elven longsword, studio lighting, …"
            hunyuan3d_prompt:    "longsword, straight blade, crossguard, …"
            sd_icon_prompt:      "RPG inventory icon, elven sword, …"
            audio_prompts:       []          ← WEAP has no sounds
            esm_defaults:        { weight: 5.0, value: 800, … }
          }

Step 2  generators/image.py → generate_reference_image()
        POST /sdapi/v1/txt2img { tiling: false, size: 512 }
        → reference.png  (used as Hunyuan3D image conditioning)

Step 3  generators/mesh.py → generate_mesh()
        gradio_client.predict(image=reference.png, text=hunyuan3d_prompt)
        → ancient_elven_longsword.dae

Step 4  generators/image.py → generate_texture()
        POST /sdapi/v1/txt2img { tiling: true, size: 512 }
        → ancient_elven_longsword_d.png

Step 5  generators/blender.py → apply_texture_and_export()
        blender --background --python <script>
        • Imports .dae
        • Smart-projects UV if missing
        • Assigns diffuse texture via Principled BSDF
        • Exports clean .dae (triangulated, Z-up)

Step 6  generators/image.py → generate_icon()
        POST /sdapi/v1/txt2img { size: 128 }
        → ancient_elven_longsword.png (RGBA, white BG removed)

Step 7  (skipped — no audio_prompts for WEAP)

Step 8  output/bundle.py → write_manifest()
        → manifest.json
```

For a `DOOR`, step 7 runs twice: once for the open sound, once for the close
sound. For `LTEX`, steps 2–3 and 5–6 are skipped entirely (terrain textures
have no mesh or icon).

---

## The AssetPlan contract

The `AssetPlan` Pydantic model is the single handoff point between the
orchestrator and the pipeline. If a field is `None`, the corresponding
pipeline step is skipped:

| Field | None means |
|---|---|
| `sd_reference_prompt` | Skip reference image + texture generation |
| `hunyuan3d_prompt` | Skip mesh generation |
| `sd_icon_prompt` | Skip icon generation |
| `audio_prompts = []` | Skip all audio generation |

This means the same pipeline code handles all 19 record types correctly
without any type-specific branching — the branching lives entirely in the
orchestrator's system prompt and in `forge/types/esm.py`.

---

## Service communication

| Service | Protocol | Client code |
|---|---|---|
| Stable Diffusion | HTTP REST (A1111 API) | `httpx` in `generators/image.py` |
| Hunyuan3D | HTTP (Gradio API) | `gradio_client` in `generators/mesh.py` |
| AudioCraft | In-process Python import | `audiocraft` in `generators/audio.py` |
| Blender | Subprocess (`--background --python`) | `subprocess` in `generators/blender.py` |
| Claude | HTTPS (Anthropic API) | `anthropic` SDK in `orchestrator.py` |

SD and Hunyuan3D are external processes because their CUDA dependency stacks
(custom ops, specific torch versions) conflict with each other and with the
core pipeline's venv. AudioCraft is bundled as an optional extras group
because it shares a compatible torch version with the rest of the project.

---

## Adding a new record type

1. Add an entry to `ESMType` in `forge/types/esm.py`.
2. Add a matching `AssetRequirements` entry in `ASSET_REQUIREMENTS`.
3. Update the orchestrator system prompt section in `orchestrator.py`
   (it is regenerated from `ASSET_REQUIREMENTS` automatically).
4. That's it — the pipeline handles it without further changes.
