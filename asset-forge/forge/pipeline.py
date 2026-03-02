"""
Pipeline runner.

Orchestrates the full asset generation flow:
    1. Orchestrator (Claude) → AssetPlan with ProceduralSpec
    2. Blender → rigged, animated 3D mesh (.dae) from stereometric primitives
    3. SD → PBR diffuse texture + inventory icon
    4. Blender → texture application + COLLADA sanitize
    5. AudioCraft → sound effects
    6. Bundle → manifest + optional install

Each step is logged to the console via Rich.
"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import settings
from .generators import audio as audio_gen
from .generators import blender as blender_gen
from .generators import image as image_gen
from .generators import procedural as procedural_gen
from .orchestrator import plan_assets
from .output.bundle import AssetBundle
from .types.esm import ESMType

console = Console()


def run(
    object_type: ESMType,
    description: str,
    output_dir: Path | None = None,
    install_into: Path | None = None,
    skip_mesh: bool = False,
    skip_audio: bool = False,
) -> AssetBundle:
    """
    Full pipeline: type + description → complete asset bundle.

    Args:
        object_type:  ESM record type.
        description:  Free-text description of the object.
        output_dir:   Override for output root (defaults to settings.output_dir).
        install_into: If set, copy final assets into this OpenMW Data Files directory.
        skip_mesh:    Skip procedural mesh generation (useful for texture-only re-runs).
        skip_audio:   Skip AudioCraft (useful if no GPU audio support).

    Returns:
        AssetBundle with all generated file paths filled in.
    """
    out_root = (output_dir or settings.output_dir).resolve()

    # ── Step 1: Plan ──────────────────────────────────────────────────────────
    console.print(Panel(
        f"[bold]Type:[/bold] {object_type.value}\n"
        f"[bold]Description:[/bold] {description}",
        title="[cyan]OpenMW Asset Forge[/cyan]",
        expand=False,
    ))

    with _spinner("Asking Claude to plan assets…"):
        plan = plan_assets(object_type, description)

    console.print(f"[green]✓[/green] Plan ready: [bold]{plan.object_id}[/bold]")

    bundle = AssetBundle(plan=plan)
    obj_dir = out_root / plan.object_id
    obj_dir.mkdir(parents=True, exist_ok=True)

    spec = plan.procedural_spec

    # ── Step 2: Procedural mesh (Blender + primitives) ────────────────────────
    if not skip_mesh and spec is not None:
        mesh_path = obj_dir / f"{plan.object_id}.dae"
        with _spinner("Building procedural mesh via Blender…"):
            procedural_gen.generate_mesh(spec, mesh_path)
        bundle.mesh_path = mesh_path
        console.print(f"[green]✓[/green] Procedural mesh → {mesh_path.name}")

    # ── Step 3: PBR diffuse texture (SD) ─────────────────────────────────────
    if spec is not None and spec.texture_prompt:
        tex_path = obj_dir / f"{plan.object_id}_d.png"
        with _spinner("Generating PBR diffuse texture via Stable Diffusion…"):
            image_gen.generate_texture(
                prompt=spec.texture_prompt,
                negative_prompt=spec.texture_negative,
                size=plan.texture_size,
                steps=plan.sd_steps,
                cfg_scale=plan.sd_cfg_scale,
                output_path=tex_path,
            )
        bundle.texture_path = tex_path
        console.print(f"[green]✓[/green] Texture → {tex_path.name}")

    # ── Step 4: Apply texture + sanitize via Blender ──────────────────────────
    if bundle.mesh_path and bundle.texture_path:
        with _spinner("Applying texture and sanitizing COLLADA via Blender…"):
            try:
                blender_gen.apply_texture_and_export(
                    dae_path=bundle.mesh_path,
                    texture_path=bundle.texture_path,
                )
            except blender_gen.BlenderError as exc:
                console.print(f"[yellow]⚠[/yellow]  Blender texture step skipped: {exc}")

    # ── Step 5: Inventory icon (SD) ───────────────────────────────────────────
    if plan.sd_icon_prompt:
        icon_path = obj_dir / f"{plan.object_id}.png"
        with _spinner("Generating inventory icon via Stable Diffusion…"):
            image_gen.generate_icon(
                prompt=plan.sd_icon_prompt,
                negative_prompt=plan.sd_icon_negative,
                size=plan.icon_size,
                steps=plan.sd_steps,
                cfg_scale=plan.sd_cfg_scale,
                output_path=icon_path,
            )
        bundle.icon_path = icon_path
        console.print(f"[green]✓[/green] Icon → {icon_path.name}")

    # ── Step 6: Audio (AudioCraft) ─────────────────────────────────────────────
    if not skip_audio and plan.audio_prompts:
        sound_dir = obj_dir / "sounds"
        with _spinner(f"Generating {len(plan.audio_prompts)} sound(s) via AudioCraft…"):
            try:
                bundle.sound_paths = audio_gen.generate_all_sounds(
                    audio_prompts=plan.audio_prompts,
                    output_dir=sound_dir,
                    stem=plan.object_id,
                )
                for role, path in bundle.sound_paths.items():
                    console.print(f"[green]✓[/green] Sound ({role}) → {path.name}")
            except RuntimeError as exc:
                console.print(f"[yellow]⚠[/yellow]  Audio skipped: {exc}")

    # ── Step 7: Manifest ──────────────────────────────────────────────────────
    manifest = bundle.write_manifest(out_root)
    console.print(f"[green]✓[/green] Manifest → {manifest.relative_to(out_root)}")

    # ── Step 8: Install (optional) ────────────────────────────────────────────
    if install_into:
        with _spinner(f"Installing assets into {install_into}…"):
            bundle.install_into_data_dir(install_into)
        console.print(f"[green]✓[/green] Installed into {install_into}")

    console.print(Panel(
        f"[bold green]Done![/bold green]  "
        f"Assets written to [bold]{out_root / plan.object_id}[/bold]",
        expand=False,
    ))

    return bundle


# ── Helpers ───────────────────────────────────────────────────────────────────

def _spinner(msg: str) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[blue]{msg}[/blue]"),
        console=console,
        transient=True,
    )
