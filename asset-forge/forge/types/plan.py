"""
AssetPlan — the structured output produced by the Claude orchestrator.

Every field with a value drives a downstream generator call.
None means "skip this generator for this plan."
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .esm import ESMType
from .procedural import ProceduralSpec


class AudioPrompt(BaseModel):
    role: str = Field(description="What this sound is used for, e.g. 'open', 'close', 'ambient'")
    prompt: str = Field(description="Text prompt for AudioGen, e.g. 'heavy wooden door creaking open'")
    duration_seconds: float = Field(default=3.0, ge=0.5, le=30.0)


class ESMDefaults(BaseModel):
    """
    Suggested default values for the ESM record fields.
    All values are advisory — the user can override them when importing into the CK.
    """
    display_name: str
    weight: float | None = None
    value: int | None = None
    # Type-specific extras stored as free-form dict (e.g. weapon subtype, armor type, etc.)
    extras: dict[str, Any] = Field(default_factory=dict)


class AssetPlan(BaseModel):
    """
    Complete asset generation plan for one OpenMW object.
    Produced by the orchestrator and consumed by the pipeline runner.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    object_id: str = Field(
        description="Snake_case unique identifier, e.g. 'ancient_iron_sword'. "
                    "Used as filename stem for all generated assets.",
    )
    object_type: ESMType
    subtype: str | None = Field(
        default=None,
        description="Type-specific subtype string, e.g. WeaponSubtype.LONG_BLADE value.",
    )

    # ── Procedural 3-D mesh, rig, and animations ──────────────────────────────
    procedural_spec: ProceduralSpec | None = Field(
        default=None,
        description=(
            "Full procedural specification: primitives to build the mesh, "
            "skeleton template (or custom bones), and NLA animation actions. "
            "null only for LTEX (terrain texture — no mesh needed)."
        ),
    )

    # ── 2-D inventory icon ────────────────────────────────────────────────────
    sd_icon_prompt: str | None = Field(
        default=None,
        description="SD prompt for the inventory icon. "
                    "None if the type doesn't use an icon (e.g. STAT, CONT, DOOR).",
    )
    sd_icon_negative: str = Field(
        default="blurry, text, watermark, realistic photo, humans, shadows, background",
        description="SD negative prompt for the icon.",
    )

    # ── Audio ─────────────────────────────────────────────────────────────────
    audio_prompts: list[AudioPrompt] = Field(
        default_factory=list,
        description="AudioGen prompts. Empty for types that don't need sound.",
    )

    # ── ESM record defaults ───────────────────────────────────────────────────
    esm_defaults: ESMDefaults = Field(
        description="Suggested ESM record field values for the generated object.",
    )

    # ── SD quality settings (icon + texture) ──────────────────────────────────
    sd_steps: int = Field(default=30, ge=10, le=100)
    sd_cfg_scale: float = Field(default=7.0, ge=1.0, le=20.0)
    icon_size: int = Field(default=128, description="Icon resolution in pixels (square).")
    texture_size: int = Field(default=512, description="Texture resolution in pixels (square).")
