"""
Blender script — generates 10 pre-built cave room variants + 1 corridor piece.
Run: blender --background --python gen_room_meshes.py
Output: games/jungle_troll_tribes/meshes/omwdg/cave_room_{a-j}.dae
                                               cave_corridor.dae
Requires cave_stone.png already present in the output directory.
"""
import bpy
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR   = REPO_ROOT / "games" / "jungle_troll_tribes" / "meshes" / "omwdg"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ROOM   = 1024.0   # room footprint (square), = 4 × tile_size
H      = 256.0    # room height
DOOR_W = 256.0    # doorway opening width (= 1 tile)
DOOR_H = 200.0    # doorway opening height (< H so there's a lintel)
WALL_T = 24.0     # wall thickness


# ─── Material ────────────────────────────────────────────────────────────────

def make_material():
    """Load cave_stone.png (already in OUT_DIR) and make a Lambert material."""
    tex_path = OUT_DIR / "cave_stone.png"
    img = bpy.data.images.load(str(tex_path))
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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def apply_mat(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def add_box(cx, cy, cz, sx, sy, sz, mat):
    """Cube with given half-extents sx/sy/sz, centred at (cx,cy,cz)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    ob = bpy.context.active_object
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(ob, mat)
    return ob


def add_plane(cx, cy, cz, sx, sy, mat, flip_normals=False):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, cz))
    ob = bpy.context.active_object
    ob.scale = (sx, sy, 1)
    bpy.ops.object.transform_apply(scale=True)
    if flip_normals:
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.editmode_toggle()
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
    fp = str(OUT_DIR / f"cave_{name}.dae")
    bpy.ops.wm.collada_export(filepath=fp, selected=True, use_texture_copies=False)
    # Replace absolute image path with relative filename so OSG can find it
    # regardless of sandbox/host path differences.
    import re
    txt = Path(fp).read_text()
    txt = re.sub(r'<init_from>[^<]*cave_stone\.png</init_from>',
                 '<init_from>textures/omwdg/cave_stone.png</init_from>', txt)
    Path(fp).write_text(txt)
    print(f"Exported: {fp}")


# ─── Room base ───────────────────────────────────────────────────────────────

def make_room_shell(mat):
    """
    Floor + ceiling + 4 walls with doorway openings.
    All geometry centred at origin; room spans ±512 in X/Y, 0..256 in Z.
    Doorway: 256 wide × 200 tall centred on each wall.
    """
    hs  = ROOM / 2        # 512 — half-span
    dw2 = DOOR_W / 2      # 128 — half door width
    pw  = hs - dw2        # 384 — pillar width
    lh  = H - DOOR_H      # 56  — lintel height

    # Floor
    add_plane(0, 0, 0, ROOM, ROOM, mat)
    # Ceiling (normals down)
    add_plane(0, 0, H, ROOM, ROOM, mat, flip_normals=True)

    for (axis, sign) in [('x', +1), ('x', -1), ('y', +1), ('y', -1)]:
        # Two side pillars flanking the doorway
        for pside in (-1, +1):
            pc = pside * (dw2 + pw / 2)   # pillar centre offset
            if axis == 'x':
                add_box(sign * hs, pc, H / 2, WALL_T, pw, H, mat)
            else:
                add_box(pc, sign * hs, H / 2, pw, WALL_T, H, mat)
        # Lintel above doorway
        if lh > 0:
            cz = DOOR_H + lh / 2
            if axis == 'x':
                add_box(sign * hs, 0, cz, WALL_T, DOOR_W, lh, mat)
            else:
                add_box(0, sign * hs, cz, DOOR_W, WALL_T, lh, mat)


# ─── Room variants ────────────────────────────────────────────────────────────

def variant_a(mat):
    """Bare cave room."""
    clear(); make_room_shell(mat)
    uv_all(); export("room_a")

def variant_b(mat):
    """Central stone pillar."""
    clear(); make_room_shell(mat)
    add_box(0, 0, H / 2, 64, 64, H, mat)
    uv_all(); export("room_b")

def variant_c(mat):
    """Two offset pillars."""
    clear(); make_room_shell(mat)
    for px in (-256, 256):
        add_box(px, 0, H / 2, 64, 64, H, mat)
    uv_all(); export("room_c")

def variant_d(mat):
    """Rock ledge platform on east side."""
    clear(); make_room_shell(mat)
    add_box(280, 0, 48, 200, 500, 96, mat)
    uv_all(); export("room_d")

def variant_e(mat):
    """Four stalactite columns from ceiling."""
    clear(); make_room_shell(mat)
    for (sx, sy) in ((-220, -220), (220, 220), (-220, 220), (220, -220)):
        add_box(sx, sy, H - 60, 28, 28, 120, mat)
    uv_all(); export("room_e")

def variant_f(mat):
    """Raised altar block at north end."""
    clear(); make_room_shell(mat)
    add_box(0, 350, 48, 280, 150, 96, mat)
    uv_all(); export("room_f")

def variant_g(mat):
    """Four corner pillars."""
    clear(); make_room_shell(mat)
    for (px, py) in ((-300, -300), (-300, 300), (300, -300), (300, 300)):
        add_box(px, py, H / 2, 56, 56, H, mat)
    uv_all(); export("room_g")

def variant_h(mat):
    """Central cross-shaped rock formation."""
    clear(); make_room_shell(mat)
    add_box(0, 0, H / 4, 320, 56, H / 2, mat)
    add_box(0, 0, H / 4, 56, 320, H / 2, mat)
    uv_all(); export("room_h")

def variant_i(mat):
    """Wide flat boulder in centre."""
    clear(); make_room_shell(mat)
    add_box(0, 0, 56, 450, 350, 112, mat)
    uv_all(); export("room_i")

def variant_j(mat):
    """Three stalactites + one floor stalagmite."""
    clear(); make_room_shell(mat)
    for (sx, sy) in ((-100, -100), (100, 200), (-200, 150)):
        add_box(sx, sy, H - 50, 24, 24, 100, mat)
    add_box(0, -200, 80, 36, 36, 160, mat)   # stalagmite from floor
    uv_all(); export("room_j")


# ─── Corridor piece ───────────────────────────────────────────────────────────

def make_corridor(mat):
    """
    256×256×256 corridor: floor + ceiling + E/W side walls; open N/S.
    Rotate 90° around Z in cell_builder for E-W corridor tiles.
    """
    clear()
    add_plane(0, 0, 0, 256, 256, mat)                   # floor
    add_plane(0, 0, H, 256, 256, mat, flip_normals=True)  # ceiling
    add_box( 128, 0, H / 2, WALL_T, 256, H, mat)         # east wall
    add_box(-128, 0, H / 2, WALL_T, 256, H, mat)         # west wall
    uv_all()
    export("corridor")


# ─── Main ────────────────────────────────────────────────────────────────────

mat = make_material()
for fn in (variant_a, variant_b, variant_c, variant_d, variant_e,
           variant_f, variant_g, variant_h, variant_i, variant_j):
    fn(mat)
make_corridor(mat)
print("Done — 10 room variants + corridor generated.")
