"""
Blender script — generates 1 cave room + corridor pieces.
Run: blender --background --python gen_room_meshes.py
Output: games/jungle_troll_tribes/meshes/omwdg/cave_room_a.dae
                                               cave_corridor.dae
                                               cave_corridor_corner.dae
                                               cave_corridor_t.dae
                                               cave_corridor_cross.dae
                                               cave_doorway_cap.dae
Requires cave_stone.png already present in the output directory.

Standard connection interface (mesh_standards.py):
  opening = DOOR_W × DOOR_H = 256 × 256 (one tile, full height, NO lintel)
  inner wall face at ±HALF_OPEN = ±128 from opening centre
"""
import sys
import bpy
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mesh_standards import TILE, ROOM, H, WALL_T, DOOR_W, DOOR_H, HALF_OPEN

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR   = REPO_ROOT / "games" / "jungle_troll_tribes" / "meshes" / "omwdg"
OUT_DIR.mkdir(parents=True, exist_ok=True)


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
    """Box centred at (cx,cy,cz), full extents sx×sy×sz (spans cx±sx/2 etc.)."""
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
    import re
    txt = Path(fp).read_text()
    txt = re.sub(r'<init_from>[^<]*cave_stone\.png</init_from>',
                 '<init_from>textures/omwdg/cave_stone.png</init_from>', txt)
    Path(fp).write_text(txt)
    print(f"Exported: {fp}")


# ─── Room shell ───────────────────────────────────────────────────────────────

def make_room_shell(mat):
    """
    Single bare cave room.

    Geometry (all centred at origin, room spans ±ROOM/2 = ±512 in X/Y, 0..H in Z):
      floor   — ROOM × ROOM, z=0
      ceiling — ROOM × ROOM, z=H, normals down
      walls   — 4 walls, each with a DOOR_W × DOOR_H = 256×256 doorway opening.

    Standard interface compliance:
      DOOR_W = TILE = 256  (one full tile)
      DOOR_H = H    = 256  (full height, NO lintel)
      Pillar inner face at ±HALF_OPEN = ±128 from each doorway centre.
    """
    hs  = ROOM / 2      # 512 — room half-span
    dw2 = DOOR_W / 2    # 128 = HALF_OPEN
    pw  = hs - dw2      # 384 — pillar full width (fills wall outside doorway)

    # Pillar depth: extend outward from inner face (hs - WALL_T/2) all the way to
    # the outer edge of the adjacent corridor tile (hs + TILE/2).  This seals the
    # corner gap that would otherwise open at X > HALF_OPEN, Y > room wall outer face.
    # Depth  = WALL_T/2 + TILE/2 = 12 + 128 = 140
    # Centre = hs - WALL_T/2 + depth/2 = 500 + 70 = 570
    pd  = WALL_T / 2 + TILE / 2          # 140 — pillar depth in outward direction
    pco = hs - WALL_T / 2 + pd / 2       # 570 — pillar centre, measured from room origin

    # Floor and ceiling extend TILE/2 (128 u) beyond every wall face.
    # This is required for L-path corridors: the first corridor tile is placed
    # one full tile outside the room edge, so its floor starts 128 u beyond
    # the wall face.  Extending by TILE/2 makes room floor and corridor floor
    # meet exactly flush.  For Z-path connections the 128-unit overlap is
    # coplanar (invisible z-fighting), not a visible gap.
    add_plane(0, 0, 0,   ROOM + TILE, ROOM + TILE, mat)                    # floor
    add_plane(0, 0, H,   ROOM + TILE, ROOM + TILE, mat, flip_normals=True) # ceiling

    for (axis, sign) in [('x', +1), ('x', -1), ('y', +1), ('y', -1)]:
        # Two side pillars flanking the doorway.
        # Doorway width = DOOR_W = TILE = 256, centred on wall midpoint.
        # Pillar lateral centre = dw2 + pw/2 = 128 + 192 = 320.
        # Pillar inner face (lateral) = 320 - 192 = 128 = HALF_OPEN ✓
        # Pillar extends outward pd=140 units to seal the corridor-room corner.
        for pside in (-1, +1):
            pc = pside * (dw2 + pw / 2)   # ±320 — lateral centre
            if axis == 'x':
                add_box(sign * pco, pc, H / 2, pd, pw, H, mat)
            else:
                add_box(pc, sign * pco, H / 2, pw, pd, H, mat)
        # No lintel: DOOR_H == H → opening spans full wall height.


# ─── Room variant ─────────────────────────────────────────────────────────────

def variant_a(mat):
    """Single bare cave room — the one and only room type."""
    clear()
    make_room_shell(mat)
    uv_all()
    export("room_a")


# ─── Corridor pieces ──────────────────────────────────────────────────────────

def make_corridor(mat):
    """
    256×256×256 straight corridor: floor + ceiling + E/W walls; open N/S.

    Standard interface compliance:
      E/W wall inner face at ±HALF_OPEN = ±128 from tile centre.
      Wall centre at HALF_OPEN + WALL_T/2 = 128+12 = 140.
      Opening: DOOR_W × DOOR_H = 256×256.

    Rotate 90° around Z for an E-W corridor tile.
    """
    wall_cx = HALF_OPEN + WALL_T / 2    # 140 — inner face at 128
    clear()
    add_plane(0, 0, 0, TILE, TILE, mat)                         # floor
    add_plane(0, 0, H, TILE, TILE, mat, flip_normals=True)      # ceiling
    add_box( wall_cx, 0, H / 2, WALL_T, TILE, H, mat)           # east wall
    add_box(-wall_cx, 0, H / 2, WALL_T, TILE, H, mat)           # west wall
    uv_all()
    export("corridor")


def make_corridor_corner(mat):
    """
    L-corner: walls N (+Y) and W (-X); open S and E.

    Rotations:
      rot=0:     walls N+W  open S+E
      rot=π/2:   walls W+S  open N+E
      rot=π:     walls S+E  open N+W
      rot=3π/2:  walls E+N  open S+W
    """
    wall_cx = HALF_OPEN + WALL_T / 2    # 140
    clear()
    add_plane(0, 0, 0, TILE, TILE, mat)
    add_plane(0, 0, H, TILE, TILE, mat, flip_normals=True)
    # North wall: full tile width so it butts flush with the west wall corner.
    add_box(0,        wall_cx, H / 2, TILE + WALL_T, WALL_T, H, mat)
    add_box(-wall_cx, 0,       H / 2, WALL_T, TILE, H, mat)
    uv_all()
    export("corridor_corner")


def make_corridor_t(mat):
    """
    T-junction: one south wall; open N, E, W.

    Rotations:
      rot=0:     wall S  (open N+E+W)
      rot=π/2:   wall E  (open N+S+W)
      rot=π:     wall N  (open S+E+W)
      rot=3π/2:  wall W  (open N+S+E)
    """
    wall_cx = HALF_OPEN + WALL_T / 2    # 140
    clear()
    add_plane(0, 0, 0, TILE, TILE, mat)
    add_plane(0, 0, H, TILE, TILE, mat, flip_normals=True)
    add_box(0, -wall_cx, H / 2, TILE + WALL_T, WALL_T, H, mat)  # south wall
    uv_all()
    export("corridor_t")


def make_corridor_cross(mat):
    """Cross/4-way: floor + ceiling only; open all 4 sides."""
    clear()
    add_plane(0, 0, 0, TILE, TILE, mat)
    add_plane(0, 0, H, TILE, TILE, mat, flip_normals=True)
    uv_all()
    export("corridor_cross")


def make_door_cap(mat):
    """
    Sealed doorway cap — closes an unused room exit from outside the room wall.

    Dimensions match the standard opening exactly: DOOR_W × DOOR_H = 256×256.
    Placed flush against the room wall outer face, centred on the doorway.
    Rotate 90°/180°/270° for E/S/W walls.
    """
    clear()
    add_box(0, 0, DOOR_H / 2, DOOR_W, WALL_T, DOOR_H, mat)
    uv_all()
    export("doorway_cap")


# ─── Main ────────────────────────────────────────────────────────────────────

mat = make_material()
variant_a(mat)
make_corridor(mat)
make_corridor_corner(mat)
make_corridor_t(mat)
make_corridor_cross(mat)
make_door_cap(mat)
print("Done — 1 room variant + straight + corner + t-junction + cross + door cap.")
