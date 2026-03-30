"""
Blender Python script — generates 6 cave tile meshes with procedural stone texture.
Run: blender --background --python gen_dungeon_meshes.py
Output meshes: omwtools/omwtools/dungeons/tilesets/meshes/cave/
Output texture: games/jungle_troll_tribes/textures/omwdg/cave_stone.png
"""
import bpy
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR  = REPO_ROOT / "omwtools" / "omwtools" / "dungeons" / "tilesets" / "meshes" / "cave"
TEX_DIR  = REPO_ROOT / "games" / "jungle_troll_tribes" / "textures" / "omwdg"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TEX_DIR.mkdir(parents=True, exist_ok=True)

TILE = 256.0
H    = 256.0
TEX_VFS_PATH = "cave_stone.png"   # relative to DAE — OSG resolves textures next to the mesh


# ─── Texture ──────────────────────────────────────────────────────────────────

def generate_rock_texture():
    """Procedural grey-brown stone using mathutils.noise turbulence."""
    from mathutils import noise as mnoise
    size = 512
    img = bpy.data.images.new("cave_stone", size, size)
    px = []
    for y in range(size):
        for x in range(size):
            u = x / size * 5.0
            v = y / size * 5.0
            # Large-scale rock variation
            base = (mnoise.turbulence((u, v, 0.4), 5, True) + 1.0) * 0.5
            # Fine surface detail
            fine = (mnoise.turbulence((u * 3, v * 3, 1.8), 3, True) + 1.0) * 0.5
            # Crack-like veins
            vein = (mnoise.turbulence((u * 6, v * 6, 3.0), 2, True) + 1.0) * 0.5
            vein = 1.0 - min(1.0, abs(vein - 0.5) * 6.0)   # thin dark lines
            val = base * 0.6 + fine * 0.3 + vein * 0.1
            # Dark grey-brown stone palette
            r = min(1.0, 0.20 + val * 0.44)
            g = min(1.0, 0.17 + val * 0.38)
            b = min(1.0, 0.14 + val * 0.31)
            px += [r, g, b, 1.0]
    img.pixels = px
    tex_path = TEX_DIR / "cave_stone.png"
    img.filepath_raw = str(tex_path)
    img.file_format = 'PNG'
    img.save()
    print(f"Texture saved: {tex_path}")
    return img


def make_material(img):
    mat = bpy.data.materials.new("cave_rock")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    tex  = nodes.new('ShaderNodeTexImage')
    tex.image = img
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.95
    out  = nodes.new('ShaderNodeOutputMaterial')
    links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat


# ─── Helpers ──────────────────────────────────────────────────────────────────

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def apply_mat(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def uv_unwrap_active():
    """Smart UV project on the active object (must be in object mode)."""
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.editmode_toggle()


def fix_tex_path(dae_path: str):
    """Replace whatever absolute path Blender wrote with the OpenMW VFS path."""
    txt = Path(dae_path).read_text()
    txt = re.sub(
        r'<init_from>[^<]*cave_stone[^<]*</init_from>',
        f'<init_from>{TEX_VFS_PATH}</init_from>',
        txt,
    )
    Path(dae_path).write_text(txt)


def export(name: str):
    bpy.ops.object.select_all(action='SELECT')
    filepath = str(OUT_DIR / f"omwdg_{name}.dae")
    bpy.ops.wm.collada_export(
        filepath=filepath,
        selected=True,
        use_texture_copies=True,   # embeds texture ref; fix_tex_path corrects the path
    )
    fix_tex_path(filepath)
    print(f"Exported: {filepath}")


# ─── Tile meshes ──────────────────────────────────────────────────────────────

rock_img = generate_rock_texture()
mat = make_material(rock_img)


def make_floor():
    clear()
    bpy.ops.mesh.primitive_plane_add(size=TILE, location=(0, 0, 0))
    ob = bpy.context.active_object
    apply_mat(ob, mat)
    uv_unwrap_active()
    export("cave_floor")


def make_wall():
    """Solid stone cube — visible from any direction, no backface-culling issues."""
    clear()
    bpy.ops.mesh.primitive_cube_add(size=TILE, location=(0, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H / TILE)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(ob, mat)
    uv_unwrap_active()
    export("cave_wall")


def make_corner():
    clear()
    bpy.ops.mesh.primitive_cube_add(size=TILE, location=(0, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H / TILE)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(ob, mat)
    uv_unwrap_active()
    export("cave_corner")


def make_pillar():
    clear()
    bpy.ops.mesh.primitive_cube_add(size=TILE * 0.3, location=(0, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H / (TILE * 0.3))
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(ob, mat)
    uv_unwrap_active()
    export("cave_pillar")


def make_doorway():
    """Two frame posts + lintel; UV-unwrap all at once."""
    clear()
    pw = TILE * 0.15
    for loc in [(-TILE * 0.4, 0, H / 2), (TILE * 0.4, 0, H / 2)]:
        bpy.ops.mesh.primitive_cube_add(size=pw, location=loc)
        ob = bpy.context.active_object
        ob.scale = (1, 1, H / pw)
        bpy.ops.object.transform_apply(scale=True)
        apply_mat(ob, mat)
    bpy.ops.mesh.primitive_cube_add(size=pw, location=(0, 0, H - pw / 2))
    ob = bpy.context.active_object
    ob.scale = (TILE / pw, 1, 1)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(ob, mat)
    # UV all selected objects together
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.editmode_toggle()
    export("cave_doorway")


def make_ceiling():
    clear()
    bpy.ops.mesh.primitive_plane_add(size=TILE, location=(0, 0, H))
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.editmode_toggle()
    ob = bpy.context.active_object
    apply_mat(ob, mat)
    uv_unwrap_active()
    export("cave_ceiling")


make_floor()
make_wall()
make_corner()
make_pillar()
make_doorway()
make_ceiling()
print("Done — 6 cave tile meshes generated with rock texture.")
