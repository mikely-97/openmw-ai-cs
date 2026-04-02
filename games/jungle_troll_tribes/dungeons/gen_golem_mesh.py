"""
Blender script — generates a blocky stone golem mesh.
Run: blender --background --python gen_golem_mesh.py
Output: games/jungle_troll_tribes/meshes/jtt/golem.dae

Geometry (all units in OpenMW world units):
  Total height ~320 units (1.3× scale in-game = ~416 world units)
  Proportions: squat, heavy, clearly constructed from stone slabs.
  Centred at origin, base at z=0 so it rests on the floor.
"""
import bpy
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT   = Path(__file__).parents[3]
OUT_DIR     = REPO_ROOT / "games" / "jungle_troll_tribes" / "meshes" / "jtt"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Material ────────────────────────────────────────────────────────────────

def make_material():
    tex_path = REPO_ROOT / "games" / "jungle_troll_tribes" / "meshes" / "omwdg" / "cave_stone.png"
    img = bpy.data.images.load(str(tex_path))
    mat = bpy.data.materials.new("golem_stone")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    tex  = nodes.new('ShaderNodeTexImage')
    tex.image = img
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 1.0
    # Slightly darker/greyer than cave walls
    bsdf.inputs['Base Color'].default_value = (0.35, 0.35, 0.35, 1.0)
    out  = nodes.new('ShaderNodeOutputMaterial')
    links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat


# ─── Helpers ─────────────────────────────────────────────────────────────────

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def apply_mat(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def add_box(cx, cy, cz, sx, sy, sz, mat):
    """Box centred at (cx,cy,cz), full extents sx×sy×sz."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    ob = bpy.context.active_object
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(ob, mat)
    return ob


def uv_all():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.editmode_toggle()


def export(name: str):
    bpy.ops.object.select_all(action='SELECT')
    fp = str(OUT_DIR / f"{name}.dae")
    bpy.ops.wm.collada_export(filepath=fp, selected=True, use_texture_copies=False)
    import re
    txt = Path(fp).read_text()
    txt = re.sub(r'<init_from>[^<]*cave_stone\.png</init_from>',
                 '<init_from>textures/omwdg/cave_stone.png</init_from>', txt)
    Path(fp).write_text(txt)
    print(f"Exported: {fp}")


# ─── Golem geometry ───────────────────────────────────────────────────────────
#
# Proportions (all in Blender units = OpenMW world units at scale 1.0):
#
#   legs:  2× pillars  60w × 60d × 90h, centres at ±35, z=0..90
#   pelvis: slab       130w × 80d × 40h, z=90..130
#   torso: slab        140w × 90d × 100h, z=130..230
#   shoulders: slab    160w × 70d × 30h,  z=230..260  (wider than torso)
#   head:  block        90w × 80d × 70h,  z=260..330
#   arms:  2× pillars   40w × 40d × 130h, centres at ±110, z=100..230
#   fists: 2× blocks    55w × 55d × 55h,  centres at ±110, z=45..100
#
# All pieces centred at x=0, y=0 laterally (except legs/arms at ±offset).

def make_golem(mat):
    clear()

    # Legs
    add_box(-35, 0,  45, 60, 60,  90, mat)   # left leg
    add_box( 35, 0,  45, 60, 60,  90, mat)   # right leg

    # Pelvis
    add_box(0, 0, 110, 130, 80, 40, mat)

    # Torso
    add_box(0, 0, 180, 140, 90, 100, mat)

    # Shoulders (wider plate)
    add_box(0, 0, 245, 160, 70, 30, mat)

    # Head
    add_box(0, 0, 295, 90, 80, 70, mat)

    # Arms
    add_box(-110, 0, 165, 40, 40, 130, mat)  # left arm
    add_box( 110, 0, 165, 40, 40, 130, mat)  # right arm

    # Fists
    add_box(-110, 0,  72, 55, 55, 55, mat)   # left fist
    add_box( 110, 0,  72, 55, 55, 55, mat)   # right fist

    uv_all()
    export("golem")


# ─── Main ────────────────────────────────────────────────────────────────────

mat = make_material()
make_golem(mat)
print("Done — golem.dae exported.")
