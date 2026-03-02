"""
CLI entry point — `forge` command.

Usage examples:
    forge generate WEAP "An ancient iron longsword with a cracked blade"
    forge generate CONT "A small weathered wooden chest with iron hinges"
    forge generate LIGH "A wrought-iron wall sconce holding a burning torch"
    forge generate LTEX "Rocky volcanic basalt ground, dark and cracked"

    forge types          — list all supported ESM types
    forge plan WEAP "..."  — print the AssetPlan JSON without generating anything
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from .types.esm import ASSET_REQUIREMENTS, ESMType

app = typer.Typer(
    name="forge",
    help="OpenMW Asset Forge — AI-powered 3D/2D asset generation pipeline.",
    add_completion=False,
)
console = Console()


# ── generate ──────────────────────────────────────────────────────────────────

@app.command()
def generate(
    object_type: Annotated[
        str,
        typer.Argument(help="ESM record type, e.g. WEAP, CONT, STAT, LIGH…"),
    ],
    description: Annotated[
        str,
        typer.Argument(help="Free-text description of the object."),
    ],
    output_dir: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory (default: ./output)."),
    ] = None,
    install_into: Annotated[
        Optional[Path],
        typer.Option(
            "--install",
            "-i",
            help="Copy finished assets into this OpenMW Data Files directory.",
        ),
    ] = None,
    skip_mesh: Annotated[
        bool,
        typer.Option("--skip-mesh", help="Skip 3D mesh generation."),
    ] = False,
    skip_audio: Annotated[
        bool,
        typer.Option("--skip-audio", help="Skip AudioCraft sound generation."),
    ] = False,
) -> None:
    """Generate assets for an OpenMW object."""
    try:
        esm_type = ESMType(object_type.upper())
    except ValueError:
        valid = ", ".join(t.value for t in ESMType)
        console.print(
            f"[red]Unknown type:[/red] {object_type!r}. Valid types: {valid}"
        )
        raise typer.Exit(code=1)

    from .pipeline import run

    run(
        object_type=esm_type,
        description=description,
        output_dir=output_dir,
        install_into=install_into,
        skip_mesh=skip_mesh,
        skip_audio=skip_audio,
    )


# ── plan ──────────────────────────────────────────────────────────────────────

@app.command()
def plan(
    object_type: Annotated[str, typer.Argument(help="ESM record type.")],
    description: Annotated[str, typer.Argument(help="Object description.")],
) -> None:
    """Print the AssetPlan JSON without generating any files."""
    try:
        esm_type = ESMType(object_type.upper())
    except ValueError:
        console.print(f"[red]Unknown type:[/red] {object_type!r}")
        raise typer.Exit(code=1)

    from .orchestrator import plan_assets

    console.print("[blue]Asking Claude for asset plan…[/blue]")
    asset_plan = plan_assets(esm_type, description)
    console.print_json(asset_plan.model_dump_json(indent=2))


# ── types ─────────────────────────────────────────────────────────────────────

@app.command(name="types")
def list_types() -> None:
    """List all supported ESM record types and their asset requirements."""
    table = Table(title="Supported ESM Types", show_lines=True)
    table.add_column("Type", style="cyan bold")
    table.add_column("3D Mesh", justify="center")
    table.add_column("Icon", justify="center")
    table.add_column("Texture", justify="center")
    table.add_column("Audio", justify="center")
    table.add_column("Rigging needed", justify="center")
    table.add_column("Notes", style="dim")

    yes = "[green]✓[/green]"
    no = "[dim]—[/dim]"

    for esm_type, req in ASSET_REQUIREMENTS.items():
        sounds = []
        if req.needs_open_sound:
            sounds.append("open")
        if req.needs_close_sound:
            sounds.append("close")
        if req.needs_ambient_sound:
            sounds.append("ambient")
        audio_cell = ", ".join(sounds) if sounds else no

        table.add_row(
            esm_type.value,
            yes if req.needs_3d_model else no,
            yes if req.needs_icon else no,
            yes if req.needs_texture else no,
            audio_cell,
            "[yellow]⚠[/yellow]" if (req.needs_rigging or req.needs_body_parts) else no,
            req.notes[:60] + "…" if len(req.notes) > 60 else req.notes,
        )

    console.print(table)


# ── check ─────────────────────────────────────────────────────────────────────

@app.command()
def check() -> None:
    """Verify that all external services are reachable."""
    import httpx

    from .config import settings

    ok = True

    # Stable Diffusion
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{settings.sd_api_url}/sdapi/v1/sd-models")
            r.raise_for_status()
        console.print(f"[green]✓[/green] Stable Diffusion: {settings.sd_api_url}")
    except Exception as exc:
        console.print(f"[red]✗[/red] Stable Diffusion ({settings.sd_api_url}): {exc}")
        ok = False

    # Hunyuan3D
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{settings.hunyuan3d_api_url}/")
            r.raise_for_status()
        console.print(f"[green]✓[/green] Hunyuan3D: {settings.hunyuan3d_api_url}")
    except Exception as exc:
        console.print(f"[red]✗[/red] Hunyuan3D ({settings.hunyuan3d_api_url}): {exc}")
        ok = False

    # Blender
    if settings.blender_path.exists():
        console.print(f"[green]✓[/green] Blender: {settings.blender_path}")
    else:
        console.print(f"[red]✗[/red] Blender not found at {settings.blender_path}")
        ok = False

    # AudioCraft
    try:
        import torch  # noqa: F401
        import audiocraft  # noqa: F401
        console.print("[green]✓[/green] AudioCraft: installed")
    except ImportError:
        console.print(
            "[yellow]⚠[/yellow]  AudioCraft: not installed "
            "(install with: poetry install -E audio)"
        )

    # Anthropic
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        # Minimal API call to verify key
        client.messages.create(
            model=settings.orchestrator_model,
            max_tokens=5,
            messages=[{"role": "user", "content": "hi"}],
        )
        console.print(f"[green]✓[/green] Anthropic API: key valid, model={settings.orchestrator_model}")
    except Exception as exc:
        console.print(f"[red]✗[/red] Anthropic API: {exc}")
        ok = False

    if not ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
