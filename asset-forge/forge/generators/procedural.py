"""
Procedural mesh generator — converts a ProceduralSpec into a Blender Python
script, runs it via Blender --background, and returns a rigged, animated
COLLADA .dae file.

No VRAM required.  No manual rigging.  Runs in seconds on CPU.

Key invariant: because we *generate* the geometry we *know* the geometry.
  • Vertex-group weights are defined (not inferred) per-primitive.
  • Bone positions equal the joints between the primitives that produced them.
  • Animations are closed-form IK / sinusoidal formulas on known bone lengths.
"""
from __future__ import annotations

from pathlib import Path

from . import blender as blender_gen
from ..types.procedural import AnimationSpec, ProceduralSpec


# ── Public entry point ────────────────────────────────────────────────────────

def generate_mesh(spec: ProceduralSpec, output_path: Path, timeout: int = 120) -> Path:
    """
    Build a COLLADA .dae from *spec* via Blender --background.

    Args:
        spec:        Fully-populated ProceduralSpec from the orchestrator.
        output_path: Destination path (must end in .dae).
        timeout:     Blender subprocess timeout in seconds.

    Returns:
        Path to the written .dae file.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".dae":
        raise ValueError(f"output_path must end in .dae, got: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    script = _build_script(spec, output_path)
    blender_gen.run_script(script, timeout=timeout)
    return output_path


# ── Script builder ────────────────────────────────────────────────────────────

def _build_script(spec: ProceduralSpec, output_path: Path) -> str:
    sections: list[str] = [
        _header(),
        _clear_scene(),
        _build_primitives(spec),
        _apply_smooth_shading(),
        _uv_unwrap(),
    ]

    has_rig = spec.skeleton_template != "none" or bool(spec.custom_bones)
    if has_rig:
        sections.append(_build_armature(spec))
        sections.append(_parent_mesh_to_armature())

    for anim in spec.animations:
        sections.append(_build_animation(anim, spec))

    sections.append(_export_collada(output_path))
    return "\n\n".join(sections)


# ── Script sections ───────────────────────────────────────────────────────────

def _header() -> str:
    return """\
import bpy
import math"""


def _clear_scene() -> str:
    return """\
# ── Clear default scene ──────────────────────────────────────────────────────
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()"""


def _build_primitives(spec: ProceduralSpec) -> str:
    """
    Create each primitive, assign its vertex-group, then:
      1. Join all regular (non-cutter) primitives into one mesh object.
      2. Apply boolean-difference/intersect cutters against the joined mesh.
    """
    lines: list[str] = ["# ── Build primitives ────────────────────────────────────────────────────────"]
    lines.append("_parts = []   # (object_name, bone_name | None) for regular parts")
    lines.append("_cutters = [] # (object_name, op) for boolean cutters")
    lines.append("")

    for i, prim in enumerate(spec.primitives):
        obj_name = f"_prim_{i}"
        lines.append(f"# Primitive {i}: {prim.type}" + (f" → bone '{prim.bone}'" if prim.bone else " (unweighted)"))
        lines.append(_primitive_add_call(prim, obj_name))
        lines.append(f"{obj_name} = bpy.context.active_object")
        lines.append(f"{obj_name}.name = {obj_name!r}")

        if prim.boolean_op:
            lines.append(f"_cutters.append(({obj_name!r}, {prim.boolean_op!r}))")
        else:
            # Assign all vertices to the bone's vertex group (weight 1.0)
            if prim.bone:
                lines.append(f"_vg = {obj_name}.vertex_groups.new(name={prim.bone!r})")
                lines.append(f"_vg.add([v.index for v in {obj_name}.data.vertices], 1.0, 'REPLACE')")
            lines.append(f"_parts.append({obj_name!r})")
        lines.append("")

    lines += [
        "# ── Join regular parts into one mesh ─────────────────────────────────────────",
        "bpy.ops.object.select_all(action='DESELECT')",
        "for _n in _parts:",
        "    bpy.data.objects[_n].select_set(True)",
        "bpy.context.view_layer.objects.active = bpy.data.objects[_parts[0]]",
        "bpy.ops.object.join()",
        "mesh_obj = bpy.context.active_object",
        "mesh_obj.name = 'GeneratedMesh'",
        "",
        "# ── Apply boolean cutters ────────────────────────────────────────────────────",
        "for _cname, _cop in _cutters:",
        "    _cobj = bpy.data.objects[_cname]",
        "    _mod = mesh_obj.modifiers.new(name='BoolCut', type='BOOLEAN')",
        "    _mod.operation = _cop.upper()",
        "    _mod.object = _cobj",
        "    bpy.context.view_layer.objects.active = mesh_obj",
        "    bpy.ops.object.modifier_apply(modifier=_mod.name)",
        "    bpy.data.objects.remove(_cobj, do_unlink=True)",
    ]

    return "\n".join(lines)


def _primitive_add_call(prim, obj_name: str) -> str:
    """Return the bpy.ops call that creates *prim* as the active object."""
    px, py, pz = prim.position
    sx, sy, sz = prim.scale
    rx, ry, rz = prim.rotation_euler

    loc = f"location=({px}, {py}, {pz})"
    rot = f"rotation=({rx}, {ry}, {rz})"

    if prim.type == "cube":
        add = f"bpy.ops.mesh.primitive_cube_add(size=1, {loc}, {rot})"
    elif prim.type == "cylinder":
        add = f"bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.5, depth=1, {loc}, {rot})"
    elif prim.type == "sphere":
        add = f"bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.5, {loc})"
    elif prim.type == "cone":
        add = f"bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.5, radius2=0, depth=1, {loc}, {rot})"
    elif prim.type == "torus":
        add = f"bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.15, {loc})"
    elif prim.type == "plane":
        add = f"bpy.ops.mesh.primitive_plane_add(size=1, {loc}, {rot})"
    else:
        raise ValueError(f"Unknown primitive type: {prim.type!r}")

    scale_line = (
        f"bpy.context.active_object.scale = ({sx}, {sy}, {sz})\n"
        "bpy.ops.object.transform_apply(scale=True)"
    )
    return f"{add}\n{scale_line}"


def _apply_smooth_shading() -> str:
    return """\
# ── Smooth shading ───────────────────────────────────────────────────────────
bpy.context.view_layer.objects.active = mesh_obj
bpy.ops.object.shade_smooth()"""


def _uv_unwrap() -> str:
    return """\
# ── UV unwrap ────────────────────────────────────────────────────────────────
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')"""


# ── Skeleton ──────────────────────────────────────────────────────────────────

# Morrowind Bip01 humanoid skeleton — approximate T-pose, Blender units (≈ m).
# Bone = (head_xyz, tail_xyz, parent_name | None)
_BIPED_NPC_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    # (name, head, tail, parent)
    ("Bip01",              (0,     0,    0   ), (0,    0,    0.10), None),
    ("Bip01 Pelvis",       (0,     0,    0.85), (0,    0,    1.00), "Bip01"),
    ("Bip01 Spine",        (0,     0,    1.00), (0,    0,    1.10), "Bip01 Pelvis"),
    ("Bip01 Spine1",       (0,     0,    1.10), (0,    0,    1.22), "Bip01 Spine"),
    ("Bip01 Spine2",       (0,     0,    1.22), (0,    0,    1.35), "Bip01 Spine1"),
    ("Bip01 Neck",         (0,     0,    1.35), (0,    0,    1.52), "Bip01 Spine2"),
    ("Bip01 Head",         (0,     0,    1.52), (0,    0,    1.75), "Bip01 Neck"),
    # Left arm
    ("Bip01 L Clavicle",   (-0.05, 0,    1.35), (-0.18, 0,  1.40), "Bip01 Spine2"),
    ("Bip01 L UpperArm",   (-0.18, 0,    1.40), (-0.48, 0,  1.38), "Bip01 L Clavicle"),
    ("Bip01 L Forearm",    (-0.48, 0,    1.38), (-0.78, 0,  1.36), "Bip01 L UpperArm"),
    ("Bip01 L Hand",       (-0.78, 0,    1.36), (-0.92, 0,  1.36), "Bip01 L Forearm"),
    ("Bip01 L Finger0",    (-0.92, 0,    1.36), (-1.00, 0,  1.36), "Bip01 L Hand"),
    # Right arm
    ("Bip01 R Clavicle",   (0.05,  0,    1.35), (0.18,  0,  1.40), "Bip01 Spine2"),
    ("Bip01 R UpperArm",   (0.18,  0,    1.40), (0.48,  0,  1.38), "Bip01 R Clavicle"),
    ("Bip01 R Forearm",    (0.48,  0,    1.38), (0.78,  0,  1.36), "Bip01 R UpperArm"),
    ("Bip01 R Hand",       (0.78,  0,    1.36), (0.92,  0,  1.36), "Bip01 R Forearm"),
    ("Bip01 R Finger0",    (0.92,  0,    1.36), (1.00,  0,  1.36), "Bip01 R Hand"),
    # Left leg
    ("Bip01 L Thigh",      (-0.10, 0,    0.88), (-0.10, 0,  0.46), "Bip01 Pelvis"),
    ("Bip01 L Calf",       (-0.10, 0,    0.46), (-0.10, 0,  0.08), "Bip01 L Thigh"),
    ("Bip01 L Foot",       (-0.10, 0,    0.08), (-0.10, 0.16, 0.02), "Bip01 L Calf"),
    ("Bip01 L Toe0",       (-0.10, 0.16, 0.02), (-0.10, 0.28, 0.02), "Bip01 L Foot"),
    # Right leg
    ("Bip01 R Thigh",      (0.10,  0,    0.88), (0.10,  0,  0.46), "Bip01 Pelvis"),
    ("Bip01 R Calf",       (0.10,  0,    0.46), (0.10,  0,  0.08), "Bip01 R Thigh"),
    ("Bip01 R Foot",       (0.10,  0,    0.08), (0.10,  0.16, 0.02), "Bip01 R Calf"),
    ("Bip01 R Toe0",       (0.10,  0.16, 0.02), (0.10,  0.28, 0.02), "Bip01 R Foot"),
    # Weapon / shield attachment points
    ("Weapon Bone",        (-0.92, 0,    1.36), (-0.92, -0.30, 1.36), "Bip01 L Hand"),
    ("Shield Bone",        (0.92,  0,    1.36), (0.92,  -0.30, 1.36), "Bip01 R Hand"),
]

# Generic quadruped — horizontal spine, Y-forward
_QUADRUPED_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",        (0,    0,    0   ), (0,    0,    0.05), None),
    ("Spine",       (0,    0.10, 0.50), (0,    0.35, 0.50), "Root"),
    ("Spine1",      (0,    0.35, 0.50), (0,    0.60, 0.50), "Spine"),
    ("Neck",        (0,    0.60, 0.50), (0,    0.75, 0.62), "Spine1"),
    ("Head",        (0,    0.75, 0.62), (0,    0.95, 0.62), "Neck"),
    ("Tail1",       (0,   -0.05, 0.45), (0,   -0.25, 0.40), "Spine"),
    ("Tail2",       (0,   -0.25, 0.40), (0,   -0.45, 0.32), "Tail1"),
    # Front legs
    ("FrontL_Upper", (-0.20, 0.50, 0.50), (-0.20, 0.50, 0.25), "Spine1"),
    ("FrontL_Lower", (-0.20, 0.50, 0.25), (-0.20, 0.50, 0.00), "FrontL_Upper"),
    ("FrontR_Upper", ( 0.20, 0.50, 0.50), ( 0.20, 0.50, 0.25), "Spine1"),
    ("FrontR_Lower", ( 0.20, 0.50, 0.25), ( 0.20, 0.50, 0.00), "FrontR_Upper"),
    # Back legs
    ("BackL_Upper",  (-0.20, 0.10, 0.50), (-0.20, 0.10, 0.25), "Spine"),
    ("BackL_Lower",  (-0.20, 0.10, 0.25), (-0.20, 0.10, 0.00), "BackL_Upper"),
    ("BackR_Upper",  ( 0.20, 0.10, 0.50), ( 0.20, 0.10, 0.25), "Spine"),
    ("BackR_Lower",  ( 0.20, 0.10, 0.25), ( 0.20, 0.10, 0.00), "BackR_Upper"),
]

# Scale multiplier keys → bone names they affect (biped template)
_BIPED_SCALE_MAP: dict[str, list[str]] = {
    "thigh":    ["Bip01 L Thigh",    "Bip01 R Thigh"],
    "shin":     ["Bip01 L Calf",     "Bip01 R Calf"],
    "upperarm": ["Bip01 L UpperArm", "Bip01 R UpperArm"],
    "forearm":  ["Bip01 L Forearm",  "Bip01 R Forearm"],
    "spine":    ["Bip01 Spine", "Bip01 Spine1", "Bip01 Spine2"],
    "neck":     ["Bip01 Neck"],
    "head":     ["Bip01 Head"],
}


def _apply_length_overrides(
    bones: list[tuple[str, tuple, tuple, str | None]],
    overrides: dict[str, float],
    scale_map: dict[str, list[str]],
) -> list[tuple[str, tuple, tuple, str | None]]:
    """Scale bone lengths by override multipliers (stretch tail along bone axis)."""
    if not overrides:
        return bones
    affected: dict[str, float] = {}
    for key, mult in overrides.items():
        for bname in scale_map.get(key, []):
            affected[bname] = mult

    result = []
    for name, head, tail, parent in bones:
        if name in affected:
            m = affected[name]
            hx, hy, hz = head
            tx, ty, tz = tail
            dx, dy, dz = (tx - hx) * m, (ty - hy) * m, (tz - hz) * m
            tail = (hx + dx, hy + dy, hz + dz)
        result.append((name, head, tail, parent))
    return result


def _bones_to_script(bone_list: list[tuple[str, tuple, tuple, str | None]]) -> str:
    """
    Emit the edit-mode bone creation block (flat, no extra indentation).
    Topologically sorts so every parent bone is emitted before its children,
    regardless of the order Claude supplied them.
    """
    # Build a dict for quick lookup
    by_name = {name: (name, head, tail, parent) for name, head, tail, parent in bone_list}
    ordered: list[tuple] = []
    visited: set[str] = set()

    def _visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        entry = by_name.get(name)
        if entry is None:
            return
        _, _, _, parent = entry
        if parent:
            _visit(parent)
        ordered.append(entry)

    for name in by_name:
        _visit(name)

    lines = []
    for name, head, tail, parent in ordered:
        hx, hy, hz = head
        tx, ty, tz = tail
        lines.append(f"_b = _arm.edit_bones.new({name!r})")
        lines.append(f"_b.head = ({hx}, {hy}, {hz})")
        lines.append(f"_b.tail = ({tx}, {ty}, {tz})")
        if parent:
            lines.append(f"_b.parent = _arm.edit_bones[{parent!r}]")
    return "\n".join(lines)


def _build_armature(spec: ProceduralSpec) -> str:
    template = spec.skeleton_template

    if template == "biped_npc":
        bones = _apply_length_overrides(
            _BIPED_NPC_BONES, spec.bone_length_overrides, _BIPED_SCALE_MAP
        )
    elif template == "quadruped":
        bones = _apply_length_overrides(
            _QUADRUPED_BONES, spec.bone_length_overrides, {}
        )
    elif template == "custom":
        bones = [
            (b.name, b.head, b.tail, b.parent)
            for b in spec.custom_bones
        ]
    else:
        return "# skeleton_template='none' — no armature"

    bone_block = _bones_to_script(bones)

    return f"""\
# ── Build armature ───────────────────────────────────────────────────────────
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm_obj = bpy.context.active_object
arm_obj.name = 'Armature'
_arm = arm_obj.data
_arm.name = 'Armature'

# Remove default stub bone
bpy.ops.armature.select_all(action='SELECT')
bpy.ops.armature.delete()

# Create bones
{bone_block}

bpy.ops.object.mode_set(mode='OBJECT')"""


def _parent_mesh_to_armature() -> str:
    return """\
# ── Parent mesh to armature (vertex groups already assigned) ─────────────────
bpy.ops.object.select_all(action='DESELECT')
mesh_obj.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.parent_set(type='ARMATURE_NAME')

# Attach armature modifier
_arm_mod = mesh_obj.modifiers.new(name='Armature', type='ARMATURE')
_arm_mod.object = arm_obj
_arm_mod.use_vertex_groups = True
_arm_mod.use_bone_envelopes = False"""


# ── Animation sections ────────────────────────────────────────────────────────

def _build_animation(anim: AnimationSpec, spec: ProceduralSpec) -> str:
    p = anim.params
    dispatch = {
        "rotation_keyframe": _anim_rotation_keyframe,
        "breathing":         _anim_breathing,
        "biped_walk":        _anim_biped_walk,
        "quadruped_walk":    _anim_quadruped_walk,
        "arm_swing":         _anim_arm_swing,
        "spine_wave":        _anim_spine_wave,
    }
    fn = dispatch.get(anim.type)
    if fn is None:
        return f"# Unknown animation type: {anim.type!r}"
    return fn(anim.name, p, spec)


def _anim_rotation_keyframe(name: str, p: dict, spec: ProceduralSpec) -> str:
    axis_x = int(p.get("axis_x", 0))
    axis_y = int(p.get("axis_y", 0))
    axis_z = int(p.get("axis_z", 1))
    angle_deg = p.get("angle_deg", 90.0)
    frame_end = int(p.get("frame_end", 30))

    return f"""\
# ── Animation: {name} (rotation_keyframe) ────────────────────────────────────
_act_{name} = bpy.data.actions.new(name={name!r})
mesh_obj.animation_data_create()
mesh_obj.animation_data.action = _act_{name}
mesh_obj.rotation_euler = (0, 0, 0)
mesh_obj.keyframe_insert(data_path="rotation_euler", frame=1)
mesh_obj.rotation_euler = (
    math.radians({angle_deg}) * {axis_x},
    math.radians({angle_deg}) * {axis_y},
    math.radians({angle_deg}) * {axis_z},
)
mesh_obj.keyframe_insert(data_path="rotation_euler", frame={frame_end})
# Make both keyframes LINEAR so the door swings smoothly
for _fc in _act_{name}.fcurves:
    for _kp in _fc.keyframe_points:
        _kp.interpolation = 'LINEAR'"""


def _anim_breathing(name: str, p: dict, spec: ProceduralSpec) -> str:
    amplitude    = p.get("amplitude",    0.02)
    period_s     = p.get("period_s",     4.0)
    total_frames = int(p.get("total_frames", 120))
    fps          = int(p.get("fps",      24))
    # Caller can override the bone via params["bone"]; otherwise fall back to
    # biped default, then auto-detect the first spine-like bone at runtime.
    explicit_bone = p.get("bone", "")

    if explicit_bone:
        bone_lookup = f'arm_obj.pose.bones.get({explicit_bone!r})'
    else:
        # At runtime: prefer Bip01 Spine2, else first bone with "spine" in name
        bone_lookup = (
            'arm_obj.pose.bones.get("Bip01 Spine2") or '
            'next((b for b in arm_obj.pose.bones if "spine" in b.name.lower() '
            'or "Spine" in b.name), None)'
        )

    return f"""\
# ── Animation: {name} (breathing) ────────────────────────────────────────────
_act_{name} = bpy.data.actions.new(name={name!r})
arm_obj.animation_data_create()
arm_obj.animation_data.action = _act_{name}
for _f in range(1, {total_frames} + 1):
    _t = (_f - 1) / {fps}
    _ph = 2 * math.pi * _t / {period_s}
    bpy.context.scene.frame_set(_f)
    _pb = {bone_lookup}
    if _pb:
        _pb.scale = (1.0, 1.0, 1.0 + {amplitude} * math.sin(_ph))
        _pb.keyframe_insert(data_path="scale", frame=_f)"""


def _anim_biped_walk(name: str, p: dict, spec: ProceduralSpec) -> str:
    step_length  = p.get("step_length",  0.35)
    freq_hz      = p.get("freq_hz",      1.2)
    step_height  = p.get("step_height",  0.08)
    thigh_len    = p.get("thigh_len",    0.42)
    shin_len     = p.get("shin_len",     0.38)
    total_frames = int(p.get("total_frames", 60))
    fps          = int(p.get("fps",      24))

    return f"""\
# ── Animation: {name} (biped_walk) ───────────────────────────────────────────
_act_{name} = bpy.data.actions.new(name={name!r})
arm_obj.animation_data_create()
arm_obj.animation_data.action = _act_{name}
_thigh = {thigh_len}
_shin  = {shin_len}
_step  = {step_length}
_freq  = {freq_hz}
_lift  = {step_height}
_fps   = {fps}

for _f in range(1, {total_frames} + 1):
    _t   = (_f - 1) / _fps
    _ph  = 2 * math.pi * _freq * _t
    bpy.context.scene.frame_set(_f)

    # ── Legs (2-bone IK, closed form) ────────────────────────────────────────
    for _side, _offset in (('L', 0.0), ('R', math.pi)):
        _sx = _step * math.sin(_ph + _offset)
        _sz = max(0.0, _lift * math.sin(_ph + _offset))

        _reach = math.sqrt(_sx**2 + (_thigh + _shin - _sz)**2)
        _reach = min(_reach, _thigh + _shin - 0.001)

        _cos_k = (_thigh**2 + _shin**2 - _reach**2) / (2 * _thigh * _shin)
        _cos_k = max(-1.0, min(1.0, _cos_k))
        _knee  = math.acos(_cos_k)

        _hip   = (math.atan2(_sx, _thigh + _shin - _sz)
                  - math.atan2(_shin * math.sin(_knee),
                               _thigh + _shin * math.cos(_knee)))

        _pb_thigh = arm_obj.pose.bones.get(f"Bip01 {{_side}} Thigh")
        _pb_calf  = arm_obj.pose.bones.get(f"Bip01 {{_side}} Calf")
        if _pb_thigh:
            _pb_thigh.rotation_euler = (_hip, 0, 0)
            _pb_thigh.keyframe_insert(data_path="rotation_euler", frame=_f)
        if _pb_calf:
            _pb_calf.rotation_euler  = (-(math.pi - _knee), 0, 0)
            _pb_calf.keyframe_insert( data_path="rotation_euler", frame=_f)

    # ── Arms (counter-swing) ─────────────────────────────────────────────────
    for _side, _offset in (('L', math.pi), ('R', 0.0)):
        _pb_arm = arm_obj.pose.bones.get(f"Bip01 {{_side}} UpperArm")
        if _pb_arm:
            _pb_arm.rotation_euler = (math.radians(25) * math.sin(_ph + _offset), 0, 0)
            _pb_arm.keyframe_insert(data_path="rotation_euler", frame=_f)

    # ── Spine bob ─────────────────────────────────────────────────────────────
    _pb_sp = arm_obj.pose.bones.get("Bip01 Spine")
    if _pb_sp:
        _pb_sp.rotation_euler = (math.radians(3) * math.sin(2 * _ph), 0, 0)
        _pb_sp.keyframe_insert(data_path="rotation_euler", frame=_f)"""


def _anim_quadruped_walk(name: str, p: dict, spec: ProceduralSpec) -> str:
    step_length   = p.get("step_length",   0.30)
    freq_hz       = p.get("freq_hz",       1.4)
    step_height   = p.get("step_height",   0.06)
    upper_leg_len = p.get("upper_leg_len", 0.30)
    lower_leg_len = p.get("lower_leg_len", 0.28)
    total_frames  = int(p.get("total_frames", 60))
    fps           = int(p.get("fps", 24))

    return f"""\
# ── Animation: {name} (quadruped_walk) ───────────────────────────────────────
_act_{name} = bpy.data.actions.new(name={name!r})
arm_obj.animation_data_create()
arm_obj.animation_data.action = _act_{name}
_ul   = {upper_leg_len}
_ll   = {lower_leg_len}
_step = {step_length}
_freq = {freq_hz}
_lift = {step_height}
_fps  = {fps}

_legs = [
    ("FrontL_Upper", "FrontL_Lower", 0.0),
    ("BackR_Upper",  "BackR_Lower",  0.0),
    ("FrontR_Upper", "FrontR_Lower", math.pi),
    ("BackL_Upper",  "BackL_Lower",  math.pi),
]
for _f in range(1, {total_frames} + 1):
    _t  = (_f - 1) / _fps
    _ph = 2 * math.pi * _freq * _t
    bpy.context.scene.frame_set(_f)

    for _upper_name, _lower_name, _offset in _legs:
        _sx = _step * math.sin(_ph + _offset)
        _sz = max(0.0, _lift * math.sin(_ph + _offset))
        _reach = math.sqrt(_sx**2 + (_ul + _ll - _sz)**2)
        _reach = min(_reach, _ul + _ll - 0.001)
        _cos_k = (_ul**2 + _ll**2 - _reach**2) / (2 * _ul * _ll)
        _cos_k = max(-1.0, min(1.0, _cos_k))
        _knee  = math.acos(_cos_k)
        _hip   = (math.atan2(_sx, _ul + _ll - _sz)
                  - math.atan2(_ll * math.sin(_knee), _ul + _ll * math.cos(_knee)))
        _pb_u = arm_obj.pose.bones.get(_upper_name)
        _pb_l = arm_obj.pose.bones.get(_lower_name)
        if _pb_u:
            _pb_u.rotation_euler = (_hip, 0, 0)
            _pb_u.keyframe_insert(data_path="rotation_euler", frame=_f)
        if _pb_l:
            _pb_l.rotation_euler = (-(math.pi - _knee), 0, 0)
            _pb_l.keyframe_insert(data_path="rotation_euler", frame=_f)

    # Spine sway
    _pb_sp = arm_obj.pose.bones.get("Spine")
    if _pb_sp:
        _pb_sp.rotation_euler = (0, math.radians(2) * math.sin(2 * _ph), 0)
        _pb_sp.keyframe_insert(data_path="rotation_euler", frame=_f)"""


def _anim_arm_swing(name: str, p: dict, spec: ProceduralSpec) -> str:
    amplitude_deg = p.get("amplitude_deg", 80.0)
    total_frames  = int(p.get("total_frames", 30))
    side          = "L" if int(p.get("bone_side", 1)) == 0 else "R"
    return f"""\
# ── Animation: {name} (arm_swing) ────────────────────────────────────────────
_act_{name} = bpy.data.actions.new(name={name!r})
arm_obj.animation_data_create()
arm_obj.animation_data.action = _act_{name}
_amp = math.radians({amplitude_deg})
for _f in range(1, {total_frames} + 1):
    _ph = math.pi * (_f - 1) / ({total_frames} - 1)   # 0 → π (swing and return)
    bpy.context.scene.frame_set(_f)
    _pb = arm_obj.pose.bones.get("Bip01 {side} UpperArm")
    if _pb:
        _pb.rotation_euler = (_amp * math.sin(_ph), 0, 0)
        _pb.keyframe_insert(data_path="rotation_euler", frame=_f)"""


def _anim_spine_wave(name: str, p: dict, spec: ProceduralSpec) -> str:
    amplitude_deg = p.get("amplitude_deg", 20.0)
    wave_speed    = p.get("wave_speed",    2.0)
    total_frames  = int(p.get("total_frames", 60))
    fps           = int(p.get("fps", 24))
    return f"""\
# ── Animation: {name} (spine_wave) ───────────────────────────────────────────
_act_{name} = bpy.data.actions.new(name={name!r})
arm_obj.animation_data_create()
arm_obj.animation_data.action = _act_{name}
_spine_bones = sorted(
    [b for b in arm_obj.pose.bones if 'spine' in b.name.lower() or 'Spine' in b.name],
    key=lambda b: b.name
)
_amp = math.radians({amplitude_deg})
for _f in range(1, {total_frames} + 1):
    _t  = (_f - 1) / {fps}
    bpy.context.scene.frame_set(_f)
    for _i, _pb in enumerate(_spine_bones):
        _ph = 2 * math.pi * {wave_speed} * _t + _i * math.pi / max(len(_spine_bones), 1)
        _pb.rotation_euler = (0, 0, _amp * math.sin(_ph))
        _pb.keyframe_insert(data_path="rotation_euler", frame=_f)"""


# ── Export ────────────────────────────────────────────────────────────────────

def _export_collada(output_path: Path) -> str:
    return f"""\
# ── Export COLLADA (Blender 3.0 compatible flags) ────────────────────────────
bpy.ops.wm.collada_export(
    filepath={str(output_path)!r},
    apply_modifiers=True,
    export_global_forward_selection='Y',
    export_global_up_selection='Z',
    apply_global_orientation=True,
    triangulate=True,
    use_texture_copies=True,
    include_armatures=True,
    include_animations=True,
    include_all_actions=True,
)
print("Procedural mesh exported:", {str(output_path)!r})"""
