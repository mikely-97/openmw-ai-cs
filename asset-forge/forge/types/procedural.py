"""
Structured description of a procedurally generated 3D asset.

Claude fills in a ProceduralSpec; the procedural generator converts it to a
Blender Python script that builds the mesh, rig, and animations, then exports
a COLLADA .dae file ready for OpenMW.

Design principle: because we *generate* the geometry we also *know* the
geometry — bone positions, vertex assignments, and animation parameters are
all co-derived from the same parametric description.  No manual rigging pass
is ever required.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Primitive ──────────────────────────────────────────────────────────────────

class Primitive(BaseModel):
    """One stereometric building block of the mesh."""

    type: Literal["cube", "cylinder", "sphere", "cone", "torus", "plane"] = Field(
        description="Blender primitive type.",
    )
    bone: str | None = Field(
        default=None,
        description=(
            "Bone name whose vertex group this primitive's vertices are added to "
            "(weight 1.0).  Use Morrowind Bip01 names for NPC/ARMO/CLOT, your "
            "custom bone names for CREA, or null for unweighted static parts."
        ),
    )
    position: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 0.0),
        description="World-space position (X, Y, Z) in Blender units (≈ metres).",
    )
    scale: tuple[float, float, float] = Field(
        default=(1.0, 1.0, 1.0),
        description=(
            "Per-axis scale applied after placement. "
            "For cylinders: (radius_x, radius_y, half_height_z) if you set base "
            "radius=0.5 and depth=1 in the operator, then scale to taste."
        ),
    )
    rotation_euler: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 0.0),
        description="XYZ Euler rotation in radians.",
    )
    boolean_op: Literal["difference", "intersect"] | None = Field(
        default=None,
        description=(
            "If set, this primitive is used as a boolean cutter against the "
            "accumulated mesh built from all preceding primitives, then deleted. "
            "Useful for hollow interiors, notches, holes. "
            "null = additive (just merged into the mesh)."
        ),
    )


# ── Skeleton ───────────────────────────────────────────────────────────────────

class BoneSpec(BaseModel):
    """Explicit bone for custom rigs (CREA, unusual objects)."""

    name: str = Field(description="Bone name (must match vertex group names in primitives).")
    head: tuple[float, float, float] = Field(description="Bone root position (world space).")
    tail: tuple[float, float, float] = Field(description="Bone tip position (world space).")
    parent: str | None = Field(default=None, description="Parent bone name, or null for root.")
    envelope_radius: float = Field(
        default=0.1, ge=0.01, le=2.0,
        description="Bone envelope radius (not used for skinning, only for display).",
    )


# ── Animations ────────────────────────────────────────────────────────────────

_ANIM_PARAM_DOCS = """\
Type-specific float parameters:

  rotation_keyframe  (DOOR open, CONT lid, lever)
    axis_x / axis_y / axis_z : 0 or 1 — which axis to rotate (default axis_z=1)
    angle_deg                 : rotation amount (default 90)
    frame_end                 : last frame of the motion (default 30)

  breathing  (NPC_ / CREA idle)
    amplitude    : chest scale delta (default 0.02)
    period_s     : breath cycle in seconds (default 4.0)
    total_frames : action length in frames at 24 fps (default 120)

  biped_walk  (NPC_, humanoid CREA)
    step_length  : stride half-length in Blender units (default 0.35)
    freq_hz      : step frequency (default 1.2)
    step_height  : max foot lift (default 0.08)
    thigh_len    : thigh bone length (default 0.42)
    shin_len     : shin bone length (default 0.38)
    total_frames : action length (default 60)

  quadruped_walk  (animal CREA)
    step_length, freq_hz, step_height, total_frames — same as biped_walk
    upper_leg_len, lower_leg_len (default 0.30 each)

  arm_swing  (attack, casting)
    amplitude_deg : arm arc in degrees (default 80)
    total_frames  : action length (default 30)
    bone_side     : 0 = left, 1 = right (default 1)

  spine_wave  (snake slither, tentacle)
    amplitude_deg : max rotation per spine bone (default 20)
    wave_speed    : waves per second (default 2.0)
    total_frames  : action length (default 60)
"""


class AnimationSpec(BaseModel):
    """One NLA action baked into the COLLADA export."""

    name: str = Field(
        description="Action name written into the COLLADA: 'idle', 'walk', 'open', 'close', 'attack'…",
    )
    type: Literal[
        "rotation_keyframe",
        "breathing",
        "biped_walk",
        "quadruped_walk",
        "arm_swing",
        "spine_wave",
    ] = Field(description="Animation algorithm to use.")
    params: dict[str, float] = Field(
        default_factory=dict,
        description=_ANIM_PARAM_DOCS,
    )


# ── Top-level spec ────────────────────────────────────────────────────────────

class ProceduralSpec(BaseModel):
    """
    Complete parametric description of a procedurally generated OpenMW asset.

    Replaces Hunyuan3D entirely.  Claude produces this; the procedural generator
    converts it to a Blender Python script that outputs a rigged, animated
    COLLADA .dae with no manual work required.
    """

    primitives: list[Primitive] = Field(
        description=(
            "Ordered list of stereometric primitives.  Build complex shapes by "
            "combining and optionally boolean-subtracting these parts. "
            "The first non-cutter primitive establishes the mesh; subsequent "
            "non-cutters are joined into it.  Boolean cutters are applied in "
            "order after the base mesh is assembled."
        ),
    )

    skeleton_template: Literal["none", "biped_npc", "quadruped", "custom"] = Field(
        default="none",
        description=(
            "'none'      – static mesh, no armature (STAT, WEAP, MISC, etc.)\n"
            "'biped_npc' – full Morrowind Bip01 humanoid skeleton (NPC_, ARMO, CLOT, BODY)\n"
            "'quadruped' – generic 4-legged creature skeleton (animal CREA)\n"
            "'custom'    – use the custom_bones list (unusual CREA, special rigs)"
        ),
    )

    custom_bones: list[BoneSpec] = Field(
        default_factory=list,
        description="Explicit bone list.  Required when skeleton_template='custom'.",
    )

    bone_length_overrides: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Scale multipliers for named bones in template skeletons. "
            "E.g. {'thigh': 1.3} makes the thigh bone 30% longer. "
            "Keys are short names: 'thigh', 'shin', 'upperarm', 'forearm', "
            "'spine', 'neck', 'head'."
        ),
    )

    animations: list[AnimationSpec] = Field(
        default_factory=list,
        description=(
            "NLA actions to bake.  Empty for fully static assets. "
            "Always include at minimum 'idle' + 'walk' for NPC_ and CREA."
        ),
    )

    texture_prompt: str | None = Field(
        default=None,
        description=(
            "Stable Diffusion prompt for the PBR diffuse texture. "
            "Should describe the surface material (wood grain, rusted iron, leather…). "
            "null = skip texture generation."
        ),
    )
    texture_negative: str = Field(
        default="blurry, text, watermark, humans, shadows, background",
        description="SD negative prompt for the texture.",
    )
