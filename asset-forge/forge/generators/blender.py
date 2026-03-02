"""
Blender post-processor.

Runs as a subprocess (Blender has its own embedded Python, so we never import bpy
directly). Used for:
  • COLLADA sanity-check and re-export (fixes occasional Hunyuan3D export quirks)
  • UV unwrapping after texture is applied
  • Format conversion fallback (glb/obj → dae)
  • Future: basic auto-rigging scaffold generation
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from ..config import settings


class BlenderError(RuntimeError):
    pass


def run_script(script: str, *, timeout: int = 300) -> str:
    """
    Run a Python script inside Blender (--background mode) and return stdout.
    Raises BlenderError on non-zero exit or if Blender binary is missing.
    """
    blender = settings.blender_path
    if not blender.exists():
        raise BlenderError(
            f"Blender not found at {blender}. "
            "Set BLENDER_PATH in your .env file."
        )

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(script)
        script_path = Path(f.name)

    try:
        result = subprocess.run(
            [str(blender), "--background", "--python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    finally:
        script_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise BlenderError(
            f"Blender exited with code {result.returncode}.\n"
            f"STDERR:\n{result.stderr}\n"
            f"STDOUT:\n{result.stdout}"
        )

    return result.stdout


# ── Public helpers ─────────────────────────────────────────────────────────────

def sanitize_collada(dae_path: Path) -> Path:
    """
    Re-import and re-export a COLLADA file through Blender to fix common issues:
      - Triangulate mesh
      - Ensure Z-up / Y-forward orientation (OpenMW convention)
      - Clean orphan data
    Overwrites the file in-place.
    """
    script = _sanitize_script(dae_path)
    run_script(script)
    return dae_path


def apply_texture_and_export(
    dae_path: Path,
    texture_path: Path,
    output_path: Path | None = None,
) -> Path:
    """
    Load a COLLADA mesh, assign a diffuse texture, UV-unwrap if needed,
    and re-export. Saves to output_path (or overwrites dae_path if None).
    """
    out = output_path or dae_path
    script = _apply_texture_script(dae_path, texture_path, out)
    run_script(script)
    return out


# ── Blender script templates ───────────────────────────────────────────────────

def _sanitize_script(dae_path: Path) -> str:
    return f"""\
import bpy

# ── Clear scene ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ── Import ──
bpy.ops.wm.collada_import(filepath={str(dae_path)!r})

# ── Sanity passes ──
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Triangulate
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.object.mode_set(mode='OBJECT')

    obj.select_set(False)

# ── Re-export (overwrite) ──
bpy.ops.wm.collada_export(
    filepath={str(dae_path)!r},
    apply_modifiers=True,
    export_global_forward_selection='Y',
    export_global_up_selection='Z',
    apply_global_orientation=True,

    triangulate=True,
    use_texture_copies=True,
)
print("Sanitized:", {str(dae_path)!r})
"""


def _apply_texture_script(dae_path: Path, texture_path: Path, out_path: Path) -> str:
    return f"""\
import bpy

# ── Clear scene ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ── Import mesh ──
bpy.ops.wm.collada_import(filepath={str(dae_path)!r})

for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # ── UV unwrap if no UVs exist ──
    if not obj.data.uv_layers:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')

    # ── Create material with texture ──
    mat = bpy.data.materials.new(name="ForgeMAT")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")

    tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load({str(texture_path)!r})
    mat.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    # Assign material
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    obj.select_set(False)

# ── Export ──
bpy.ops.wm.collada_export(
    filepath={str(out_path)!r},
    apply_modifiers=True,
    export_global_forward_selection='Y',
    export_global_up_selection='Z',
    apply_global_orientation=True,

    triangulate=True,
    use_texture_copies=True,
)
print("Exported with texture:", {str(out_path)!r})
"""
