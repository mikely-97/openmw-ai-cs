"""Blender Python script: Create troll body mesh rigged to Bip01 skeleton.

Imports the template BasicPlayerBody.dae for its armature, deletes the template
mesh, builds a new troll-proportioned body from primitives, skins it to the
Bip01 bones, applies green troll material, and exports to jtt/troll_body.dae.

Run: blender --background --python gen_troll_body.py
"""
import bpy
import bmesh
import os
from mathutils import Vector, Matrix

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_BODY = os.path.join(SCRIPT_DIR, "meshes", "BasicPlayerBody.dae")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "meshes", "jtt")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "troll_body.dae")

# ── Clean scene ──
bpy.ops.wm.read_factory_settings(use_empty=True)
for obj in bpy.data.objects:
    bpy.data.objects.remove(obj, do_unlink=True)

# ── Import template to get the Bip01 armature ──
print("[troll] Importing template armature...")
bpy.ops.wm.collada_import(filepath=TEMPLATE_BODY)

arm_obj = None
for obj in list(bpy.data.objects):
    if obj.type == 'MESH':
        # Delete template body mesh — we'll build our own
        bpy.data.objects.remove(obj, do_unlink=True)
    elif obj.type == 'ARMATURE':
        arm_obj = obj

if not arm_obj:
    print("[troll] ERROR: No armature found!")
    exit(1)

print(f"[troll] Armature: {arm_obj.name}, {len(arm_obj.data.bones)} bones")

# ── Bone position helpers ──
def bone_pos(name):
    """Get bone head position in armature space."""
    b = arm_obj.data.bones.get(name)
    if b:
        return b.head_local.copy()
    return Vector((0, 0, 0))

# Key bone positions (in armature local space, units ~ cm)
PELVIS = bone_pos("Bip01_Pelvis")     # ~(0, 2.3, 65.8)
SPINE = bone_pos("Bip01_Spine")       # ~(0, 3.4, 79.0)
SPINE2 = bone_pos("Bip01_Spine2")     # ~(0, 0.8, 101.9)
NECK = bone_pos("Bip01_Neck")         # ~(0, -0.3, 113.3)
HEAD = bone_pos("Bip01_Head")         # ~(0, 2.5, 120.1)
L_UPPER = bone_pos("Bip01_L_Upperarm")
R_UPPER = bone_pos("Bip01_R_Upperarm")
L_FORE = bone_pos("Bip01_L_Forearm")
R_FORE = bone_pos("Bip01_R_Forearm")
L_HAND = bone_pos("Bip01_L_Hand")
R_HAND = bone_pos("Bip01_R_Hand")
L_THIGH = bone_pos("Bip01_L_Thigh")
R_THIGH = bone_pos("Bip01_R_Thigh")
L_CALF = bone_pos("Bip01_L_Calf")
R_CALF = bone_pos("Bip01_R_Calf")
L_FOOT = bone_pos("Bip01_L_Foot")
R_FOOT = bone_pos("Bip01_R_Foot")

print(f"[troll] Head at {HEAD}, Pelvis at {PELVIS}")

# ── Build troll body mesh from primitives ──
def add_body_segment(bm_target, center, radius_x, radius_y, height, segments=12):
    """Add a rounded cylinder (capsule-like) body segment."""
    # Create ellipsoid via UV sphere scaled
    temp_mesh = bpy.data.meshes.new("_temp")
    temp_obj = bpy.data.objects.new("_temp", temp_mesh)
    bpy.context.collection.objects.link(temp_obj)
    bpy.context.view_layer.objects.active = temp_obj

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=max(6, segments//2),
                               radius=1.0)
    # Scale to ellipsoid
    for v in bm.verts:
        v.co.x *= radius_x
        v.co.y *= radius_y
        v.co.z *= height / 2.0
        v.co += center
    bm.to_mesh(temp_mesh)
    bm.free()

    # Merge into target bmesh
    bm_target.from_mesh(temp_mesh)

    # Cleanup
    bpy.data.objects.remove(temp_obj, do_unlink=True)
    bpy.data.meshes.remove(temp_mesh)

def lerp(a, b, t):
    return a + (b - a) * t

def midpoint(a, b):
    return lerp(a, b, 0.5)

print("[troll] Building troll body mesh...")
bm = bmesh.new()

# ── Head: large, slightly forward-jutting troll head ──
head_center = HEAD + Vector((0, 1, 5))  # slightly above and forward
add_body_segment(bm, head_center, 8.0, 8.5, 14.0, segments=14)
# Jaw/chin bulge
add_body_segment(bm, HEAD + Vector((0, 5, -1)), 5.0, 4.0, 5.0, segments=10)

# ── Neck: thick troll neck ──
neck_center = midpoint(NECK, HEAD)
add_body_segment(bm, neck_center, 5.5, 5.0, 8.0, segments=10)

# ── Upper torso: broad barrel chest ──
chest_center = midpoint(SPINE2, NECK)
add_body_segment(bm, chest_center, 16.0, 11.0, 16.0, segments=14)

# ── Mid torso ──
mid_center = midpoint(SPINE, SPINE2)
add_body_segment(bm, mid_center, 14.0, 10.0, 14.0, segments=12)

# ── Lower torso / belly ──
belly_center = midpoint(PELVIS, SPINE)
add_body_segment(bm, belly_center, 13.0, 10.0, 16.0, segments=12)

# ── Pelvis / hips ──
add_body_segment(bm, PELVIS, 12.0, 9.0, 10.0, segments=12)

# ── Arms (both sides) ──
for side_bones in [(L_UPPER, L_FORE, L_HAND), (R_UPPER, R_FORE, R_HAND)]:
    upper, fore, hand = side_bones

    # Upper arm - thick
    arm_mid = midpoint(upper, fore)
    add_body_segment(bm, arm_mid, 5.0, 5.0, (upper - fore).length * 0.9, segments=10)

    # Forearm
    fore_mid = midpoint(fore, hand)
    add_body_segment(bm, fore_mid, 4.5, 4.5, (fore - hand).length * 0.9, segments=10)

    # Hand - big troll hands
    hand_extend = hand + (hand - fore).normalized() * 5
    hand_mid = midpoint(hand, hand_extend)
    add_body_segment(bm, hand_mid, 4.5, 2.5, 8.0, segments=8)

# ── Legs (both sides) ──
for side_bones in [(L_THIGH, L_CALF, L_FOOT), (R_THIGH, R_CALF, R_FOOT)]:
    thigh, calf, foot = side_bones

    # Thigh - thick
    thigh_mid = midpoint(thigh, calf)
    add_body_segment(bm, thigh_mid, 6.5, 6.5, (thigh - calf).length * 0.9, segments=10)

    # Calf
    calf_mid = midpoint(calf, foot)
    add_body_segment(bm, calf_mid, 5.0, 5.0, (calf - foot).length * 0.9, segments=10)

    # Foot
    foot_extend = foot + Vector((0, -5, -2))
    foot_mid = midpoint(foot, foot_extend)
    add_body_segment(bm, foot_mid, 5.0, 7.0, 5.0, segments=8)

# Remove doubles from overlapping segments
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.5)

print(f"[troll] Mesh: {len(bm.verts)} verts, {len(bm.faces)} faces")

# ── Create mesh object ──
troll_mesh = bpy.data.meshes.new("TrollBody")
bm.to_mesh(troll_mesh)
bm.free()

troll_obj = bpy.data.objects.new("TrollBody", troll_mesh)
bpy.context.collection.objects.link(troll_obj)
bpy.context.view_layer.objects.active = troll_obj

# ── Apply green troll material ──
mat = bpy.data.materials.new("TrollSkin")
mat.diffuse_color = (0.22, 0.40, 0.18, 1.0)  # Dark mossy green
troll_obj.data.materials.append(mat)
print("[troll] Applied TrollSkin material")

# ── Skin to armature ──
# Parent mesh to armature
troll_obj.parent = arm_obj
mod = troll_obj.modifiers.new("Armature", 'ARMATURE')
mod.object = arm_obj

# Create vertex groups for key bones and assign weights by proximity
BONE_REGIONS = {
    "Bip01_Head": {"center": HEAD + Vector((0, 1, 5)), "radius": 12.0},
    "Bip01_Neck": {"center": midpoint(NECK, HEAD), "radius": 8.0},
    "Bip01_Spine2": {"center": midpoint(SPINE2, NECK), "radius": 18.0},
    "Bip01_Spine1": {"center": midpoint(SPINE, SPINE2), "radius": 16.0},
    "Bip01_Spine": {"center": midpoint(PELVIS, SPINE), "radius": 16.0},
    "Bip01_Pelvis": {"center": PELVIS, "radius": 14.0},
    "Bip01_L_Upperarm": {"center": midpoint(L_UPPER, L_FORE), "radius": 14.0},
    "Bip01_R_Upperarm": {"center": midpoint(R_UPPER, R_FORE), "radius": 14.0},
    "Bip01_L_Forearm": {"center": midpoint(L_FORE, L_HAND), "radius": 12.0},
    "Bip01_R_Forearm": {"center": midpoint(R_FORE, R_HAND), "radius": 12.0},
    "Bip01_L_Hand": {"center": L_HAND, "radius": 10.0},
    "Bip01_R_Hand": {"center": R_HAND, "radius": 10.0},
    "Bip01_L_Thigh": {"center": midpoint(L_THIGH, L_CALF), "radius": 14.0},
    "Bip01_R_Thigh": {"center": midpoint(R_THIGH, R_CALF), "radius": 14.0},
    "Bip01_L_Calf": {"center": midpoint(L_CALF, L_FOOT), "radius": 12.0},
    "Bip01_R_Calf": {"center": midpoint(R_CALF, R_FOOT), "radius": 12.0},
    "Bip01_L_Foot": {"center": L_FOOT, "radius": 10.0},
    "Bip01_R_Foot": {"center": R_FOOT, "radius": 10.0},
}

# Create vertex groups
for bone_name in BONE_REGIONS:
    troll_obj.vertex_groups.new(name=bone_name)

# Assign weights based on distance (closest bone gets highest weight)
me = troll_obj.data
for vi, vert in enumerate(me.vertices):
    pos = vert.co
    # Find distances to all bone regions
    weights = {}
    for bone_name, region in BONE_REGIONS.items():
        dist = (pos - region["center"]).length
        if dist < region["radius"]:
            # Weight falls off with distance
            w = max(0.0, 1.0 - (dist / region["radius"]))
            weights[bone_name] = w

    if not weights:
        # Fallback: assign to nearest bone
        min_dist = float('inf')
        nearest = "Bip01_Spine"
        for bone_name, region in BONE_REGIONS.items():
            d = (pos - region["center"]).length
            if d < min_dist:
                min_dist = d
                nearest = bone_name
        weights[nearest] = 1.0

    # Normalize and assign
    total = sum(weights.values())
    for bone_name, w in weights.items():
        vg = troll_obj.vertex_groups[bone_name]
        vg.add([vi], w / total, 'REPLACE')

print(f"[troll] Skinned {len(me.vertices)} vertices to {len(BONE_REGIONS)} bone groups")

# ── Smooth normals ──
bpy.ops.object.select_all(action='DESELECT')
troll_obj.select_set(True)
bpy.context.view_layer.objects.active = troll_obj
bpy.ops.object.shade_smooth()

# ── Export ──
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Select mesh and armature for export
bpy.ops.object.select_all(action='DESELECT')
troll_obj.select_set(True)
arm_obj.select_set(True)

print(f"[troll] Exporting to {OUTPUT_FILE}")
bpy.ops.wm.collada_export(
    filepath=OUTPUT_FILE,
    apply_modifiers=True,
    selected=True,
    include_armatures=True,
    deform_bones_only=True,
)

size = os.path.getsize(OUTPUT_FILE)
print(f"[troll] Done! troll_body.dae = {size} bytes ({size//1024}KB)")
