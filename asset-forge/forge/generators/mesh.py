"""
Hunyuan3D mesh generator.

Calls the locally running Hunyuan3D Gradio server via gradio_client.
Produces a .dae (COLLADA) file ready for OpenMW.

Setup: see scripts/start_hunyuan3d.sh
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from gradio_client import Client, handle_file
from PIL import Image

from ..config import settings

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.hunyuan3d_api_url)
    return _client


def generate_mesh(
    prompt: str,
    reference_image: Image.Image | None,
    output_path: Path,
    steps: int = 50,
) -> Path:
    """
    Generate a 3D mesh via Hunyuan3D and save it as a COLLADA .dae file.

    Args:
        prompt:          Text description of the object shape.
        reference_image: Optional conditioning image (greatly improves quality).
        output_path:     Where to save the .dae — must end in '.dae'.
        steps:           Diffusion steps (more = better quality, slower).

    Returns:
        Path to the saved .dae file.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".dae":
        raise ValueError(f"output_path must end in .dae, got: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = _get_client()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # Save reference image to a temp file if provided
        image_arg = None
        if reference_image is not None:
            ref_path = tmp / "reference.png"
            reference_image.save(ref_path, format="PNG")
            image_arg = handle_file(str(ref_path))

        # Call Hunyuan3D Gradio API.
        # The Hunyuan3D-2 gradio app exposes /generate (shape generation)
        # and /texture (texture generation) as separate endpoints.
        # We call shape first, then texture.
        result = client.predict(
            image=image_arg,
            text=prompt,
            steps=steps,
            guidance_scale=5.5,
            seed=-1,          # -1 = random
            octree_resolution=256,
            export_format="dae",  # request COLLADA directly
            api_name="/shape_generation",
        )

        # result is the path(s) returned by Gradio — normalise to a single path
        if isinstance(result, (list, tuple)):
            generated_path = Path(result[0])
        else:
            generated_path = Path(result)

        # If Hunyuan3D returned a different format, try converting via Blender
        if generated_path.suffix.lower() != ".dae":
            generated_path = _convert_to_dae(generated_path, tmp)

        shutil.copy2(generated_path, output_path)

    return output_path


def _convert_to_dae(source: Path, work_dir: Path) -> Path:
    """
    Fall-back: use Blender to convert any mesh format to COLLADA.
    Called only if Hunyuan3D didn't return .dae directly.
    """
    import subprocess

    out = work_dir / "converted.dae"
    script = _blender_convert_script(source, out)
    script_path = work_dir / "convert.py"
    script_path.write_text(script)

    from ..config import settings as cfg

    subprocess.run(
        [str(cfg.blender_path), "--background", "--python", str(script_path)],
        capture_output=True,
        check=True,
    )
    return out


def _blender_convert_script(source: Path, dest: Path) -> str:
    return f"""\
import bpy

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import source mesh (auto-detect format)
src = {str(source)!r}
if src.endswith('.glb') or src.endswith('.gltf'):
    bpy.ops.import_scene.gltf(filepath=src)
elif src.endswith('.obj'):
    bpy.ops.wm.obj_import(filepath=src)
elif src.endswith('.fbx'):
    bpy.ops.import_scene.fbx(filepath=src)
else:
    raise RuntimeError(f"Unsupported source format: {{src}}")

# Export as COLLADA
bpy.ops.wm.collada_export(
    filepath={str(dest)!r},
    apply_modifiers=True,
    export_mesh_type=0,
    export_global_forward_selection='Y',
    export_global_up_selection='Z',
    apply_global_orientation=True,
    export_object_transformation_type=0,
    export_animation_transformation_type=0,
    export_image_type='PNG',
    use_texture_copies=True,
    active_uv_only=False,
    use_object_instantiation=True,
    sort_by_name=False,
    keep_smooth_groups=True,
    export_triangles=True,
)
print("COLLADA export complete:", {str(dest)!r})
"""
