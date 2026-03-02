# Generators

This document describes each of the four generation backends in detail:
how they work, how they're called, what they produce, and how to tune them.

---

## Stable Diffusion (image generator)

**Module:** `forge/generators/image.py`
**Protocol:** HTTP POST to the A1111-compatible REST API
**Used for:** reference images, inventory icons, PBR diffuse textures

### Why Stable Diffusion for images?

The pipeline uses SD for two distinct purposes:

1. **Reference image** — a clean studio render of the object, used as the
   image-conditioning input to Hunyuan3D. A good reference image dramatically
   improves mesh quality and geometry accuracy versus text-only generation.

2. **Icon + texture** — 2D assets used directly in-game, generated with
   purpose-specific prompt suffixes.

### API

Asset Forge calls one endpoint:

```
POST {SD_API_URL}/sdapi/v1/txt2img
```

All three image types share the same underlying call; the differences are in
the payload:

| Parameter | Reference image | Icon | Texture |
|---|---|---|---|
| `size` | 512×512 | 128×128 (default) | 512×512 (default) |
| `tiling` | `false` | `false` | `true` |
| Prompt suffix | *(none)* | `game icon, transparent background, clean edges` | `seamless texture, tileable, PBR diffuse, flat lighting` |
| Post-processing | none | white→alpha removal | none |

### Checkpoint choice

The SD checkpoint loaded in the WebUI affects quality significantly. The
orchestrator generates prompts that work across most realistic-style
checkpoints. Recommended starting points:

- **SDXL 1.0 base** — high detail for reference images
- **DreamShaper XL** — strong on fantasy items
- **Juggernaut XL** — photorealistic materials (good for texture generation)

Set `SD_MODEL_CHECKPOINT` in `.env` to override the currently loaded checkpoint
on a per-run basis.

### Prompt anatomy

The orchestrator writes prompts for each image type. You can preview them
with `forge plan <TYPE> "<description>"` before running.

**Reference image prompt structure:**
```
<material description>, <object description>, clean studio shot,
white background, detailed, <style qualifier>, fantasy RPG
```

**Icon prompt structure:**
```
RPG inventory icon, <object description>, isometric view,
white background, fantasy game art, clean edges
```

**Texture prompt structure:**
```
<material>, seamless texture, tileable, PBR diffuse,
no seams, uniform lighting, flat material
```

### White background removal (icons)

After generating an icon, Asset Forge converts pixels above a brightness
threshold (R, G, B > 240) to transparent alpha. This is a simple heuristic
that works well for studio-lit single-object renders but may leave fringing
artefacts on very bright objects. For production-quality icons, run the output
through a proper background removal tool (e.g. `rembg`).

### Tuning

| Setting | Effect |
|---|---|
| `sd_steps` in AssetPlan | More steps = better quality, slower. 20–30 is usually sufficient. |
| `sd_cfg_scale` in AssetPlan | Higher = more literal adherence to prompt. 6–8 is a good range. |
| `SD_TIMEOUT` in `.env` | Increase if steps are high and GPU is slow. |

---

## Hunyuan3D (mesh generator)

**Module:** `forge/generators/mesh.py`
**Protocol:** Gradio API (`gradio_client`)
**Used for:** 3D mesh generation → COLLADA `.dae`

### How it works

Hunyuan3D-2 is a two-stage diffusion model:

1. **Shape stage** — a 3D diffusion model conditioned on the reference image
   and/or a text prompt generates an occupancy field, then extracts a triangle
   mesh from it (marching cubes / DMTet).

2. **Texture stage** — a separate diffusion model projects appearance from the
   reference image onto the mesh surface, producing a UV-mapped PBR material.

Asset Forge calls only the **shape stage** by default and handles textures
itself via the Stable Diffusion seamless-texture pass + Blender UV application.
This avoids the ~24.5 GB VRAM requirement of the full Hunyuan3D pipeline.

To use Hunyuan3D's own texture stage instead, start the server with
`--enable-tex` and modify `generators/mesh.py` to call the `/texture` Gradio
endpoint after shape generation.

### Gradio API call

```python
client.predict(
    image=handle_file("reference.png"),  # optional but recommended
    text="longsword, straight blade, crossguard, wrapped handle",
    steps=50,
    guidance_scale=5.5,
    seed=-1,               # -1 = random
    octree_resolution=256, # mesh detail level
    export_format="dae",   # request COLLADA directly
    api_name="/shape_generation",
)
```

The Gradio server returns a file path to the generated mesh. Asset Forge
copies it to the output directory.

### Format fallback

If the server returns a format other than `.dae` (e.g. `.glb`), Asset Forge
automatically calls Blender to convert it:

```
blender --background --python convert.py
# convert.py: import .glb → export .dae
```

### VRAM requirements

| Mode | VRAM |
|---|---|
| Shape only (default) | ~11.5 GB |
| Shape + Hunyuan3D texture | ~24.5 GB |

Use `--low-vram-mode` in `start_hunyuan3d.sh` to reduce shape-stage VRAM to
~6–8 GB at a quality cost.

### Mesh quality parameters

| Parameter | Effect |
|---|---|
| `hunyuan3d_steps` in AssetPlan | More steps = more detail. 30–50 is typical. 100 for final production. |
| `guidance_scale` | Higher = closer to reference image. 5–7 is typical. |
| `octree_resolution` | 256 = standard. 512 = high detail (more VRAM). |

### Prompt writing for Hunyuan3D

Hunyuan3D's text conditioning is weaker than image conditioning. Keep prompts
**short and geometric** — describe shape, not story:

```
# Good
"longsword, straight blade, crossguard, wrapped handle"

# Less effective
"an ancient elven weapon forged in the fires of Alinor"
```

The orchestrator follows this convention automatically. If you're running
`forge plan` and want to override a prompt manually, focus on silhouette
descriptors: large/small, round/angular, elongated/squat, number of parts.

---

## AudioCraft AudioGen (audio generator)

**Module:** `forge/generators/audio.py`
**Protocol:** In-process Python import
**Used for:** door sounds, light ambience
**Extras group:** `audio` — install with `poetry install -E audio`

### Model

AudioGen Medium (`facebook/audiogen-medium`) — 1.5B parameter autoregressive
transformer trained to generate audio from text descriptions. Weights are
downloaded from HuggingFace on first use (~2.5 GB) and cached locally.

**Licence:** CC-BY-NC 4.0 — non-commercial use only.

### How it's called

AudioGen is loaded as a Python object, not an external server. The model is
instantiated once per process and cached (subsequent calls reuse it):

```python
model = AudioGen.get_pretrained("facebook/audiogen-medium")
model.set_generation_params(duration=3.0)
wav = model.generate(["heavy wooden door slowly creaking open"])
torchaudio.save("open.wav", wav[0].cpu(), model.sample_rate)
```

Output is always 16-bit PCM WAV at the model's native sample rate (16 kHz).

### Prompt writing for AudioGen

AudioGen was trained on:
- **AudioSet** — YouTube audio clips with labels
- **BBC Sound Effects** — professional SFX library
- **Sonniss Game Effects** — game-specific SFX (ideal for our use case)
- **FSD50K**, **Clotho v2**, **VGG-Sound**, and others

Best results come from prompts that:
- Name the **material** and **action** explicitly
- Include acoustic context (reverb, room, distance)

```
# Door sounds
"heavy oak door slowly swinging open, old iron hinges, mild creak"
"iron dungeon door slamming shut, loud bang, stone room reverb"

# Light sounds
"single torch crackling and burning, quiet fire, warm ambience"
"cluster of candles flickering, soft wax popping, indoor"
```

### Duration guidelines

| Sound role | Recommended duration |
|---|---|
| Door open | 2–4 s |
| Door close | 1–3 s |
| Light ambient (looped) | 5–10 s |

AudioGen supports up to 30 s. Longer durations require more VRAM and time.
Set `duration_seconds` on each `AudioPrompt` in the plan; the orchestrator
suggests sensible defaults.

### VRAM and device

AudioGen runs on CUDA by default (`AUDIOGEN_DEVICE=cuda`). It will fall back
to CPU automatically if CUDA is unavailable, but CPU inference is very slow
(minutes per clip). Set `AUDIOGEN_DEVICE=cpu` explicitly if you have no GPU.

The medium model requires ~4 GB VRAM. If you're running Hunyuan3D
simultaneously, generate audio in a separate step using `--skip-mesh` / a
second run, or ensure you have enough total VRAM.

---

## Blender (post-processor)

**Module:** `forge/generators/blender.py`
**Protocol:** Subprocess (`blender --background --python`)
**Used for:** texture application, UV unwrapping, COLLADA sanitization

### Why subprocess?

Blender ships with its own embedded Python interpreter. Importing `bpy` from
outside Blender is not officially supported and breaks with every Blender
release. Running Blender as a subprocess with a generated script avoids this
entirely and keeps Asset Forge's venv clean.

### Scripts generated at runtime

`blender.py` contains two script templates:

**`sanitize_collada(dae_path)`**
```python
# Loads a .dae, triangulates all meshes,
# re-exports with Z-up / Y-forward orientation.
```
Called automatically after every Hunyuan3D mesh to normalise geometry.

**`apply_texture_and_export(dae_path, texture_path, out_path)`**
```python
# Loads .dae.
# Smart-UV-projects if no UV map exists.
# Creates Principled BSDF material, assigns diffuse texture.
# Exports clean .dae with embedded texture paths.
```
Called after texture generation to bind the SD texture to the mesh.

### COLLADA export settings

All Blender exports use these flags:

```python
bpy.ops.wm.collada_export(
    filepath=...,
    apply_modifiers=True,
    export_global_forward_selection='Y',   # Y-forward
    export_global_up_selection='Z',        # Z-up
    apply_global_orientation=True,
    export_triangles=True,                 # triangulate
    export_image_type='PNG',
    use_texture_copies=True,               # embed texture alongside .dae
)
```

Y-forward / Z-up matches the coordinate system expected by the game engine.
Triangulation avoids rendering artefacts from non-planar quads.

### Format conversion

If Hunyuan3D returns a format other than `.dae`, `generators/mesh.py` calls
`blender.py` with an import-and-export script. Supported source formats:

- `.glb` / `.gltf` — `bpy.ops.import_scene.gltf`
- `.obj` — `bpy.ops.wm.obj_import`
- `.fbx` — `bpy.ops.import_scene.fbx`

### Error handling

Blender errors (non-zero exit code) are caught as `BlenderError` and logged
as warnings — the pipeline continues without the Blender step rather than
aborting. The raw mesh (untextured, uncleaned) is kept as the output.

### Blender version

Tested with Blender 3.6 LTS and 4.x. The `collada_export` operator API has
been stable across both. Earlier versions (< 3.0) use a different API and
will not work.
