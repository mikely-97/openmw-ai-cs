"""
Orchestrator — uses Claude to translate (type, description) → AssetPlan.

Claude is given:
  - The full ESM type catalogue with asset requirements
  - The AssetPlan JSON schema as a tool it must call
  - The user's description

It returns a fully populated AssetPlan whose procedural_spec describes the
mesh in terms of stereometric primitives, an optional skeleton template, and
optional NLA animation actions — all ready for Blender to execute without any
manual work.
"""
from __future__ import annotations

import json
import textwrap

import anthropic

from .config import settings
from .types.esm import ASSET_REQUIREMENTS, ESMType, get_requirements
from .types.plan import AssetPlan

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


# ── System prompt ──────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    type_docs = []
    for esm_type, req in ASSET_REQUIREMENTS.items():
        flags = []
        if req.needs_3d_model:
            flags.append("procedural mesh (→ ProceduralSpec)")
        if req.needs_icon:
            flags.append("inventory icon (→ SD)")
        if req.needs_texture:
            flags.append("PBR texture (→ SD, prompt in procedural_spec.texture_prompt)")
        if req.needs_open_sound:
            flags.append("open sound (→ AudioGen)")
        if req.needs_close_sound:
            flags.append("close sound (→ AudioGen)")
        if req.needs_ambient_sound:
            flags.append("ambient sound (→ AudioGen)")
        if req.needs_body_parts:
            flags.append("skeleton_template='biped_npc', animations=['idle','walk']")
        if req.needs_rigging:
            flags.append("full rig required — choose biped_npc / quadruped / custom")
        if req.is_terrain_texture:
            flags.append("terrain texture only (procedural_spec=null)")

        type_docs.append(
            f"  {esm_type.value}: {', '.join(flags) or 'no assets'}\n"
            f"    Note: {req.notes}"
        )

    return textwrap.dedent(f"""
        You are the asset-planning orchestrator for the OpenMW Asset Forge pipeline.

        Your job: given an OpenMW record type and a description, produce a complete
        AssetPlan by calling the `create_asset_plan` tool.

        ═══════════════════════════════════════════════════
        MESH GENERATION: STEREOMETRIC PRIMITIVES VIA BLENDER
        ═══════════════════════════════════════════════════
        ALL meshes are built from geometric primitives (cube, cylinder, sphere,
        cone, torus, plane) inside Blender's Python API.  No AI image-to-3D tool
        is used.  You describe the geometry parametrically; Blender executes it.

        ProceduralSpec fields:

          primitives  — ordered list of Primitive objects:
            type          : "cube" | "cylinder" | "sphere" | "cone" | "torus" | "plane"
            position      : [X, Y, Z] in Blender units (≈ metres), Z-up
            scale         : [X, Y, Z] — stretches the unit primitive
                            For cylinder/cone: scale X/Y = radius, Z = half-height
                            For cube:          scale X/Y/Z = half-extents
                            For sphere:        scale X = Y = Z = radius
            rotation_euler: [X, Y, Z] radians
            bone          : bone name this primitive's vertices are weighted to (or null)
            boolean_op    : "difference" | "intersect" | null
                            difference = drill/cut this shape out of the preceding mesh

          skeleton_template:
            "none"       — static mesh (STAT, WEAP, MISC, BOOK, ALCH, LOCK, PROB,
                            APPA, REPA, INGR, LIGH, CONT, DOOR, ACTI, LTEX)
            "biped_npc"  — full Morrowind Bip01 skeleton (NPC_, BODY, ARMO, CLOT)
            "quadruped"  — 4-legged skeleton (animal CREA)
            "custom"     — supply custom_bones list (unusual CREA, snake, etc.)

          bone_length_overrides — dict of scale multipliers for template bones:
            keys: "thigh", "shin", "upperarm", "forearm", "spine", "neck", "head"

          custom_bones — list of BoneSpec (name, head, tail, parent) for skeleton_template="custom"

          animations — list of AnimationSpec:
            rotation_keyframe  DOOR open / CONT lid / ACTI lever
              axis_z=1, angle_deg=90, frame_end=30
            breathing          NPC_ / CREA idle (spine oscillation)
              amplitude=0.02, period_s=4.0, total_frames=120
            biped_walk         NPC_ / humanoid CREA walk cycle (closed-form IK)
              step_length=0.35, freq_hz=1.2, step_height=0.08, thigh_len=0.42,
              shin_len=0.38, total_frames=60
            quadruped_walk     animal CREA diagonal-trot walk cycle
              step_length=0.30, freq_hz=1.4, step_height=0.06,
              upper_leg_len=0.30, lower_leg_len=0.28, total_frames=60
            arm_swing          attack / casting animation
              amplitude_deg=80, total_frames=30, bone_side=1 (0=L, 1=R)
            spine_wave         snake slither / tentacle
              amplitude_deg=20, wave_speed=2.0, total_frames=60

          texture_prompt — SD prompt for the PBR diffuse texture
            Describe surface material: "rough oak wood planks, dark grain",
            "rusted iron, pitted surface", "worn leather, stitched seams"

        ═══════════════════════════════════════════════════
        INVENTORY ICON (sd_icon_prompt)
        ═══════════════════════════════════════════════════
        • Isometric or slightly angled view, white/transparent background
        • Game art style, crisp edges
        • Example: "RPG inventory icon, iron longsword, isometric view,
          white background, fantasy game art, clean edges"
        • null for: STAT, ACTI, CONT, DOOR, BODY, NPC_, CREA, LTEX

        ═══════════════════════════════════════════════════
        AUDIO (audio_prompts)
        ═══════════════════════════════════════════════════
        • Describe the acoustic event precisely, include material and action
        • "heavy wooden door slowly creaking open, old hinges"

        ═══════════════════════════════════════════════════
        ESM TYPE → REQUIRED ASSETS
        ═══════════════════════════════════════════════════
        {chr(10).join(type_docs)}

        ═══════════════════════════════════════════════════
        GEOMETRY GUIDELINES
        ═══════════════════════════════════════════════════
        Morrowind assets are LOW POLY (300–2 000 triangles).  Approximate, don't
        over-detail.  Use boolean difference sparingly (hollow chests, window holes).

        Coordinate system — Blender, Z-up, Y-forward:
          • Character stands along Z axis, feet at Z=0, head at Z≈1.75
          • Items lie on the XY plane centred at origin
          • Doors rotate around their Z axis at the hinge edge

        BIPED_NPC bone names (must match exactly for Morrowind to load):
          Bip01  Bip01 Pelvis  Bip01 Spine  Bip01 Spine1  Bip01 Spine2
          Bip01 Neck  Bip01 Head
          Bip01 L/R Clavicle  Bip01 L/R UpperArm  Bip01 L/R Forearm  Bip01 L/R Hand
          Bip01 L/R Thigh  Bip01 L/R Calf  Bip01 L/R Foot  Bip01 L/R Toe0
          Weapon Bone  Shield Bone

        IMPORTANT RULES
        • procedural_spec must be null ONLY for LTEX.
        • Every primitive's bone field must match a bone that exists in the chosen
          skeleton_template (or be null for static assets).
        • Primitives are Z-up: cylinders grow along Z, spheres at centre.
        • object_id must be lowercase snake_case derived from the description.
        • ESM defaults should be realistic for Morrowind's scale
          (weight in kg, value in septims).
        • Weapon/Armor/Apparatus subtypes must come from the canonical subtype lists.
        • Always include at least idle + walk animations for NPC_ and CREA types.
        • For DOOR: always include rotation_keyframe animations named "open" and "close".
        • For CONT: include a rotation_keyframe animation named "open" for the lid.
    """).strip()


# ── Tool schema ────────────────────────────────────────────────────────────────

def _asset_plan_tool() -> dict:
    schema = AssetPlan.model_json_schema()
    return {
        "name": "create_asset_plan",
        "description": (
            "Output the complete asset generation plan for the requested object. "
            "You MUST call this tool — do not respond in plain text."
        ),
        "input_schema": schema,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def plan_assets(object_type: ESMType, description: str) -> AssetPlan:
    """
    Ask Claude to produce an AssetPlan for the given type + description.
    Raises ValueError if Claude doesn't call the tool.
    """
    req = get_requirements(object_type)
    user_message = (
        f"Generate an asset plan for the following OpenMW object:\n\n"
        f"  Type:        {object_type.value}\n"
        f"  Description: {description}\n\n"
        f"Asset requirements for {object_type.value}:\n"
        f"  needs_3d_model:      {req.needs_3d_model}\n"
        f"  needs_icon:          {req.needs_icon}\n"
        f"  needs_texture:       {req.needs_texture}\n"
        f"  needs_open_sound:    {req.needs_open_sound}\n"
        f"  needs_close_sound:   {req.needs_close_sound}\n"
        f"  needs_ambient_sound: {req.needs_ambient_sound}\n"
        f"  needs_body_parts:    {req.needs_body_parts}\n"
        f"  needs_rigging:       {req.needs_rigging}\n"
        f"  is_terrain_texture:  {req.is_terrain_texture}\n\n"
        f"Call create_asset_plan with a fully populated plan."
    )

    response = _get_client().messages.create(
        model=settings.orchestrator_model,
        max_tokens=settings.orchestrator_max_tokens,
        system=_build_system_prompt(),
        tools=[_asset_plan_tool()],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "create_asset_plan":
            raw = block.input
            raw["object_type"] = object_type.value
            return AssetPlan.model_validate(raw)

    raise ValueError(
        f"Orchestrator did not call create_asset_plan. "
        f"Stop reason: {response.stop_reason}. "
        f"Raw content: {json.dumps([b.model_dump() for b in response.content], indent=2)}"
    )
