"""
Runtime configuration loaded from environment variables or a .env file.
Copy .env.example to .env and fill in your values.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Anthropic / Claude ────────────────────────────────────────────────────
    anthropic_api_key: str = Field(
        description="Anthropic API key (https://console.anthropic.com/).",
    )
    orchestrator_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model used for asset planning.",
    )
    orchestrator_max_tokens: int = Field(default=4096)

    # ── Stable Diffusion (A1111 / Forge / ComfyUI A1111-compat API) ───────────
    sd_api_url: str = Field(
        default="http://localhost:7860",
        description="Base URL of your local Stable Diffusion API server.",
    )
    sd_model_checkpoint: str | None = Field(
        default=None,
        description="Override checkpoint name (e.g. 'v1-5-pruned-emaonly.safetensors'). "
                    "Leave None to use whatever is currently loaded.",
    )
    # Recommended: a checkpoint good at objects/items (e.g. SDXL, DreamShaper, etc.)
    sd_timeout: float = Field(default=120.0)

    # ── Hunyuan3D (unused — kept for .env backwards-compatibility only) ──────────
    # Mesh generation is now handled entirely by Blender stereometric primitives.
    hunyuan3d_api_url: str = Field(
        default="http://localhost:8080",
        description="No longer used. Retained so existing .env files don't break.",
    )
    hunyuan3d_timeout: float = Field(default=600.0, description="No longer used.")

    # ── AudioCraft ────────────────────────────────────────────────────────────
    audiogen_model: str = Field(
        default="facebook/audiogen-medium",
        description="HuggingFace model ID for AudioGen.",
    )
    audiogen_device: str = Field(
        default="cuda",
        description="PyTorch device for AudioGen ('cuda' or 'cpu').",
    )

    # ── Blender ───────────────────────────────────────────────────────────────
    blender_path: Path = Field(
        default=Path("/usr/bin/blender"),
        description="Absolute path to the Blender executable.",
    )

    @field_validator("blender_path", mode="before")
    @classmethod
    def expand_blender_path(cls, v: object) -> Path:
        return Path(str(v)).expanduser()

    # ── Output ────────────────────────────────────────────────────────────────
    output_dir: Path = Field(
        default=Path("output"),
        description="Root directory for all generated assets.",
    )

    @field_validator("output_dir", mode="before")
    @classmethod
    def expand_output_dir(cls, v: object) -> Path:
        return Path(str(v)).expanduser()


# Module-level singleton — imported everywhere.
settings = Settings()  # type: ignore[call-arg]  # env vars provide required fields
