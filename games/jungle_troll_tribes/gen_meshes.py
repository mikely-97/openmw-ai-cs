"""
Generate placeholder meshes for Jungle Troll Tribes.
All coordinates are in OpenMW game units (1 unit ≈ 1.4cm).
Player height ≈ 140 units for reference.

Run: blender --background --python gen_meshes.py
"""
import bpy
import os
import math

OUT = "/home/mike/Documents/grimoires/openmw-ai-cs/games/jungle_troll_tribes/meshes/jtt"
os.makedirs(OUT, exist_ok=True)


def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)


def mat(name, r, g, b):
    m = bpy.data.materials.new(name)
    m.use_nodes = False
    m.diffuse_color = (r, g, b, 1.0)
    return m


def apply_mat(obj, m):
    obj.data.materials.clear()
    obj.data.materials.append(m)


def export(name):
    path = os.path.join(OUT, name)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.wm.collada_export(
        filepath=path,
        selected=True,
        include_children=True,
    )
    count = len([o for o in bpy.context.scene.objects if o.type == 'MESH'])
    print(f"  ✓ {name}  ({count} meshes)")


# ─── ENVIRONMENT STATICS ──────────────────────────────────────────────────

def mk_totem_pole():
    clear()
    m = mat("totem", 0.50, 0.25, 0.05)
    m_face = mat("totem_face", 0.70, 0.45, 0.20)
    # Main pole
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=18, depth=260,
                                         location=(0, 0, 130))
    apply_mat(bpy.context.active_object, m)
    # Top head sphere
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=32, location=(0, 0, 292))
    apply_mat(bpy.context.active_object, m_face)
    # Decorative rings
    for z in [80, 160, 220]:
        bpy.ops.mesh.primitive_torus_add(major_radius=24, minor_radius=6,
                                          major_segments=12, minor_segments=6,
                                          location=(0, 0, z))
        apply_mat(bpy.context.active_object, m_face)
    export("totem_pole.dae")


def mk_troll_hut():
    clear()
    m_wall = mat("hut_wall", 0.60, 0.45, 0.25)
    m_roof = mat("hut_roof", 0.35, 0.18, 0.04)
    m_door = mat("hut_door", 0.12, 0.06, 0.01)
    # Walls (hexagonal prism)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=190, depth=120,
                                         location=(0, 0, 60))
    apply_mat(bpy.context.active_object, m_wall)
    # Roof cone
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=210, radius2=5,
                                     depth=110, location=(0, 0, 175))
    apply_mat(bpy.context.active_object, m_roof)
    # Door marker (dark box on front)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -192, 60))
    bpy.context.active_object.scale = (40, 5, 60)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_door)
    export("troll_hut.dae")


def mk_voodoo_shrine():
    clear()
    m_stone = mat("shrine_stone", 0.28, 0.14, 0.28)
    m_skull = mat("shrine_skull", 0.84, 0.80, 0.68)
    m_dark  = mat("shrine_dark",  0.05, 0.00, 0.08)
    # Four-sided pyramid base
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=100, radius2=0,
                                     depth=200, location=(0, 0, 100))
    apply_mat(bpy.context.active_object, m_stone)
    # Skull
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=28, location=(0, 0, 228))
    apply_mat(bpy.context.active_object, m_skull)
    # Eye sockets
    for x in [-10, 10]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4,
                                              radius=7, location=(x, -22, 232))
        apply_mat(bpy.context.active_object, m_dark)
    # Corner bone stakes
    for angle in [45, 135, 225, 315]:
        rad = math.radians(angle)
        x, y = math.cos(rad) * 120, math.sin(rad) * 120
        bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=6, depth=160,
                                             location=(x, y, 80),
                                             rotation=(0.25, 0, rad))
        apply_mat(bpy.context.active_object, m_skull)
    export("voodoo_shrine.dae")


def mk_wood_node():
    clear()
    m_bark = mat("wood_bark", 0.38, 0.20, 0.06)
    m_cut  = mat("wood_cut",  0.68, 0.45, 0.20)
    for (x, y, h) in [(-40, 0, 90), (40, -20, 70), (5, 50, 110)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=22, depth=h,
                                             location=(x, y, h / 2))
        apply_mat(bpy.context.active_object, m_bark)
        # Cut top disc
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=22, depth=4,
                                             location=(x, y, h + 2))
        apply_mat(bpy.context.active_object, m_cut)
    export("wood_node.dae")


def mk_stone_node():
    clear()
    m = mat("stone", 0.50, 0.50, 0.54)
    # Central main rock (flat icosphere)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=90,
                                           location=(0, 0, 36))
    bpy.context.active_object.scale = (1.2, 1.0, 0.45)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    for (x, y, r) in [(-95, 30, 45), (80, 40, 38), (20, -90, 55)]:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r,
                                               location=(x, y, r * 0.4))
        bpy.context.active_object.scale = (1.0, 0.9, 0.48)
        bpy.ops.object.transform_apply(scale=True)
        apply_mat(bpy.context.active_object, m)
    export("stone_node.dae")


def mk_herb_node():
    clear()
    m_green  = mat("herb_ground",  0.12, 0.50, 0.12)
    m_flower = mat("herb_flower",  0.72, 0.82, 0.18)
    # Ground patch
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=75, depth=8,
                                         location=(0, 0, 4))
    apply_mat(bpy.context.active_object, m_green)
    for (x, y) in [(-28, 5), (28, -15), (5, 38), (-15, -35), (22, 30)]:
        # Stem
        bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=4, depth=36,
                                             location=(x, y, 22))
        apply_mat(bpy.context.active_object, m_green)
        # Flower/leaf
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4,
                                              radius=10, location=(x, y, 44))
        apply_mat(bpy.context.active_object, m_flower)
    export("herb_node.dae")


def mk_tribal_chest():
    clear()
    m_wood  = mat("chest_wood",  0.44, 0.24, 0.08)
    m_metal = mat("chest_metal", 0.70, 0.60, 0.20)
    # Body
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 22))
    bpy.context.active_object.scale = (80, 50, 24)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_wood)
    # Lid (slightly arched — use cylinder half)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 54))
    bpy.context.active_object.scale = (82, 52, 16)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_wood)
    # Metal corner clasps
    for (x, y) in [(75, 45), (-75, 45), (75, -45), (-75, -45)]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 30))
        bpy.context.active_object.scale = (8, 8, 38)
        bpy.ops.object.transform_apply(scale=True)
        apply_mat(bpy.context.active_object, m_metal)
    # Front latch
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -52, 36))
    bpy.context.active_object.scale = (16, 5, 14)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_metal)
    export("tribal_chest.dae")


def mk_herb_basket():
    clear()
    m_weave = mat("basket_weave", 0.70, 0.50, 0.20)
    m_herb  = mat("basket_herb",  0.20, 0.60, 0.14)
    # Basket body (wide-top truncated cone)
    bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=30, radius2=50,
                                     depth=65, location=(0, 0, 32))
    apply_mat(bpy.context.active_object, m_weave)
    # Herb bundle on top
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=36, location=(0, 0, 78))
    bpy.context.active_object.scale = (1.0, 1.0, 0.62)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_herb)
    export("herb_basket.dae")


def mk_resource_pile():
    clear()
    m = mat("resource_pile", 0.55, 0.40, 0.15)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8,
                                          radius=130, location=(0, 0, 45))
    bpy.context.active_object.scale = (1.0, 1.0, 0.38)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    export("resource_pile.dae")


def mk_fire_pit():
    clear()
    m_stone = mat("pit_stone",  0.50, 0.45, 0.40)
    m_fire  = mat("pit_fire",   0.96, 0.40, 0.04)
    m_ember = mat("pit_ember",  0.80, 0.20, 0.00)
    # Stone ring
    bpy.ops.mesh.primitive_torus_add(major_radius=62, minor_radius=18,
                                      major_segments=14, minor_segments=8,
                                      location=(0, 0, 16))
    apply_mat(bpy.context.active_object, m_stone)
    # Ember disc
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=50, depth=6,
                                         location=(0, 0, 6))
    apply_mat(bpy.context.active_object, m_ember)
    # Flame cone
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=40, radius2=4,
                                     depth=80, location=(0, 0, 68))
    apply_mat(bpy.context.active_object, m_fire)
    export("fire_pit.dae")


def mk_bone_torch():
    clear()
    m_bone = mat("torch_bone", 0.84, 0.80, 0.65)
    m_fire = mat("torch_fire", 0.96, 0.52, 0.04)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=5, depth=160,
                                         location=(0, 0, 80))
    apply_mat(bpy.context.active_object, m_bone)
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=14, radius2=2,
                                     depth=38, location=(0, 0, 178))
    apply_mat(bpy.context.active_object, m_fire)
    export("bone_torch.dae")


def mk_glow_mushroom():
    clear()
    m_stem  = mat("mush_stem",  0.70, 0.60, 0.50)
    m_cap   = mat("mush_cap",   0.08, 0.80, 0.52)
    m_glow  = mat("mush_glow",  0.00, 1.00, 0.62)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=9, depth=44,
                                         location=(0, 0, 22))
    apply_mat(bpy.context.active_object, m_stem)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8,
                                          radius=34, location=(0, 0, 60))
    bpy.context.active_object.scale = (1.0, 1.0, 0.68)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_cap)
    # Glow ring under cap
    bpy.ops.mesh.primitive_torus_add(major_radius=32, minor_radius=4,
                                      major_segments=12, minor_segments=6,
                                      location=(0, 0, 42))
    apply_mat(bpy.context.active_object, m_glow)
    export("glow_mushroom.dae")


def mk_troll_door():
    clear()
    m_wood  = mat("door_wood",  0.38, 0.20, 0.06)
    m_frame = mat("door_frame", 0.28, 0.13, 0.03)
    m_bone  = mat("door_bone",  0.80, 0.76, 0.62)
    # Door panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 86))
    bpy.context.active_object.scale = (76, 7, 86)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_wood)
    # Frame top
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 178))
    bpy.context.active_object.scale = (90, 8, 10)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_frame)
    # Frame sides
    for sx in [-85, 85]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sx, 0, 86))
        bpy.context.active_object.scale = (8, 8, 90)
        bpy.ops.object.transform_apply(scale=True)
        apply_mat(bpy.context.active_object, m_frame)
    # Bone handle
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=5, depth=30,
                                         location=(55, -10, 86),
                                         rotation=(math.pi / 2, 0, 0))
    apply_mat(bpy.context.active_object, m_bone)
    export("troll_door.dae")


# ─── WEAPONS ─────────────────────────────────────────────────────────────

def mk_bone_club():
    clear()
    m = mat("club", 0.82, 0.78, 0.65)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=6, depth=88,
                                         location=(0, 0, 44))
    apply_mat(bpy.context.active_object, m)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=20, location=(0, 0, 100))
    bpy.context.active_object.scale = (1.0, 1.0, 1.30)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    export("bone_club.dae")


def mk_stone_hatchet():
    clear()
    m_wood  = mat("hatchet_wood",  0.44, 0.25, 0.08)
    m_stone = mat("hatchet_stone", 0.50, 0.48, 0.54)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=5, depth=70,
                                         location=(0, 0, 35))
    apply_mat(bpy.context.active_object, m_wood)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(10, 0, 78))
    bpy.context.active_object.scale = (30, 6, 22)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_stone)
    export("stone_hatchet.dae")


def mk_obsidian_spear():
    clear()
    m_shaft = mat("spear_shaft", 0.34, 0.18, 0.05)
    m_tip   = mat("spear_tip",   0.10, 0.05, 0.14)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=4, depth=180,
                                         location=(0, 0, 90))
    apply_mat(bpy.context.active_object, m_shaft)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=8, radius2=0,
                                     depth=38, location=(0, 0, 199))
    apply_mat(bpy.context.active_object, m_tip)
    export("obsidian_spear.dae")


def mk_flint_dagger():
    clear()
    m_blade = mat("dagger_blade", 0.46, 0.44, 0.52)
    m_grip  = mat("dagger_grip",  0.40, 0.20, 0.06)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=7, radius2=1,
                                     depth=50, location=(0, 0, 40))
    apply_mat(bpy.context.active_object, m_blade)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=6, depth=25,
                                         location=(0, 0, 10))
    apply_mat(bpy.context.active_object, m_grip)
    export("flint_dagger.dae")


def mk_vine_whip():
    clear()
    m = mat("whip", 0.14, 0.50, 0.10)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=3, depth=120,
                                         location=(0, 0, 60))
    bpy.context.active_object.rotation_euler = (0.22, 0.12, 0)
    apply_mat(bpy.context.active_object, m)
    export("vine_whip.dae")


def mk_war_maul():
    clear()
    m_handle = mat("maul_handle", 0.34, 0.18, 0.05)
    m_head   = mat("maul_head",   0.54, 0.50, 0.55)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=7, depth=140,
                                         location=(0, 0, 70))
    apply_mat(bpy.context.active_object, m_handle)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=22, depth=45,
                                         location=(0, 0, 155),
                                         rotation=(math.pi / 2, 0, 0))
    apply_mat(bpy.context.active_object, m_head)
    export("war_maul.dae")


def mk_wooden_bow():
    clear()
    m_wood   = mat("bow_wood",   0.50, 0.30, 0.08)
    m_string = mat("bow_string", 0.84, 0.80, 0.65)
    bpy.ops.mesh.primitive_torus_add(major_radius=70, minor_radius=4,
                                      major_segments=16, minor_segments=6,
                                      location=(0, 0, 0))
    bpy.context.active_object.scale = (1.0, 0.28, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_wood)
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=2, depth=138,
                                         location=(0, -18, 0))
    apply_mat(bpy.context.active_object, m_string)
    export("wooden_bow.dae")


def mk_stone_arrow():
    clear()
    m_shaft = mat("arrow_shaft", 0.44, 0.27, 0.08)
    m_tip   = mat("arrow_tip",   0.50, 0.48, 0.56)
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=2, depth=80,
                                         location=(0, 0, 40))
    apply_mat(bpy.context.active_object, m_shaft)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=4, radius2=0,
                                     depth=16, location=(0, 0, 88))
    apply_mat(bpy.context.active_object, m_tip)
    export("stone_arrow.dae")


# ─── ARMOR ────────────────────────────────────────────────────────────────

def mk_bone_shield():
    clear()
    m      = mat("shield_bone", 0.82, 0.78, 0.64)
    m_rim  = mat("shield_rim",  0.60, 0.50, 0.30)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=65, depth=8,
                                         location=(0, 0, 0))
    apply_mat(bpy.context.active_object, m)
    bpy.ops.mesh.primitive_torus_add(major_radius=65, minor_radius=6,
                                      major_segments=14, minor_segments=6,
                                      location=(0, 0, 0))
    apply_mat(bpy.context.active_object, m_rim)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=15, location=(0, 0, 12))
    apply_mat(bpy.context.active_object, m)
    export("bone_shield.dae")


def mk_hide_cuirass():
    clear()
    m = mat("cuirass", 0.50, 0.30, 0.12)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 44))
    bpy.context.active_object.scale = (55, 28, 55)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    export("hide_cuirass.dae")


def mk_bone_helm():
    clear()
    m = mat("helm", 0.80, 0.76, 0.62)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8,
                                          radius=32, location=(0, 0, 22))
    bpy.context.active_object.scale = (1.0, 1.0, 0.72)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=5, radius2=1,
                                     depth=28, location=(0, 0, 60))
    apply_mat(bpy.context.active_object, m)
    export("bone_helm.dae")


def mk_bark_pauldron():
    clear()
    m = mat("pauldron", 0.35, 0.22, 0.06)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=36, location=(0, 0, 18))
    bpy.context.active_object.scale = (1.0, 0.50, 0.60)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    export("bark_pauldron.dae")


# ─── MISC ITEMS ───────────────────────────────────────────────────────────

def mk_tribal_drum():
    clear()
    m_wood = mat("drum_wood", 0.44, 0.24, 0.08)
    m_skin = mat("drum_skin", 0.76, 0.60, 0.40)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=40, depth=50,
                                         location=(0, 0, 25))
    apply_mat(bpy.context.active_object, m_wood)
    for z in [51, -1]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=42, depth=3,
                                             location=(0, 0, z))
        apply_mat(bpy.context.active_object, m_skin)
    export("tribal_drum.dae")


def mk_voodoo_doll():
    clear()
    m      = mat("doll_body", 0.60, 0.40, 0.30)
    m_pin  = mat("doll_pin",  0.80, 0.10, 0.10)
    m_eyes = mat("doll_eyes", 0.05, 0.00, 0.00)
    # Body
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=10, depth=38,
                                         location=(0, 0, 30))
    apply_mat(bpy.context.active_object, m)
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=13, location=(0, 0, 63))
    apply_mat(bpy.context.active_object, m)
    for xe in [-5, 5]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=4, ring_count=3,
                                              radius=3, location=(xe, -11, 65))
        apply_mat(bpy.context.active_object, m_eyes)
    # Arms
    for xa in [-20, 20]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=4, depth=35,
                                             location=(xa, 0, 38),
                                             rotation=(0, math.pi / 2, 0))
        apply_mat(bpy.context.active_object, m)
    # Pin
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=2, depth=48,
                                         location=(5, -8, 30),
                                         rotation=(0.4, 0.1, 0))
    apply_mat(bpy.context.active_object, m_pin)
    export("voodoo_doll.dae")


def mk_troll_idol():
    clear()
    m       = mat("idol_stone", 0.44, 0.42, 0.48)
    m_tusk  = mat("idol_tusk",  0.82, 0.78, 0.65)
    # Base plinth
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 10))
    bpy.context.active_object.scale = (30, 24, 10)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    # Body
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=12, depth=40,
                                         location=(0, 0, 40))
    apply_mat(bpy.context.active_object, m)
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=17, location=(0, 0, 73))
    bpy.context.active_object.scale = (0.9, 0.9, 1.1)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    for xt in [-8, 8]:
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=3, radius2=1,
                                         depth=16, location=(xt, -14, 64),
                                         rotation=(-0.4, 0, 0))
        apply_mat(bpy.context.active_object, m_tusk)
    export("troll_idol.dae")


def mk_shell_token():
    clear()
    m = mat("token", 0.84, 0.74, 0.54)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=10, depth=2,
                                         location=(0, 0, 1))
    apply_mat(bpy.context.active_object, m)
    export("shell_token.dae")


# ─── CREATURES ────────────────────────────────────────────────────────────

def mk_panther():
    clear()
    m_body = mat("panther_fur",  0.08, 0.08, 0.10)
    m_eye  = mat("panther_eye",  0.90, 0.82, 0.00)
    # Main body (elongated sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8,
                                          radius=50, location=(0, 0, 52))
    bpy.context.active_object.scale = (1.6, 0.72, 0.80)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_body)
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8,
                                          radius=28, location=(88, 0, 62))
    apply_mat(bpy.context.active_object, m_body)
    # Eyes
    for ey in [-12, 12]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4,
                                              radius=6, location=(112, ey, 68))
        apply_mat(bpy.context.active_object, m_eye)
    # Tail
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=7, depth=82,
                                         location=(-112, 0, 60),
                                         rotation=(0, math.pi / 3, 0))
    apply_mat(bpy.context.active_object, m_body)
    # Legs (4)
    for (lx, ly) in [(40, 32), (40, -32), (-28, 32), (-28, -32)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=9, depth=54,
                                             location=(lx, ly, 24))
        apply_mat(bpy.context.active_object, m_body)
    export("panther.dae")


def mk_croc():
    clear()
    m_top = mat("croc_top", 0.14, 0.34, 0.14)
    # Body
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8,
                                          radius=50, location=(0, 0, 30))
    bpy.context.active_object.scale = (2.6, 0.50, 0.40)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_top)
    # Snout box
    bpy.ops.mesh.primitive_cube_add(size=1, location=(158, 0, 28))
    bpy.context.active_object.scale = (66, 24, 18)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_top)
    # Tail
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=18, radius2=2,
                                     depth=120,
                                     location=(-136, 0, 28),
                                     rotation=(0, -math.pi / 2, 0))
    apply_mat(bpy.context.active_object, m_top)
    # Legs (short)
    for (lx, ly) in [(60, 36), (60, -36), (-38, 36), (-38, -36)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=10, depth=35,
                                             location=(lx, ly, 12))
        apply_mat(bpy.context.active_object, m_top)
    export("croc.dae")


def mk_spider():
    clear()
    m_body = mat("spider_body", 0.14, 0.10, 0.14)
    m_eye  = mat("spider_eye",  0.80, 0.00, 0.00)
    # Abdomen
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8,
                                          radius=36, location=(-32, 0, 40))
    apply_mat(bpy.context.active_object, m_body)
    # Thorax/head
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=22, location=(24, 0, 40))
    apply_mat(bpy.context.active_object, m_body)
    # Eyes
    for ey in [-9, 9]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=4, ring_count=3,
                                              radius=5, location=(44, ey, 48))
        apply_mat(bpy.context.active_object, m_eye)
    # 8 legs (spread radially)
    for i in range(8):
        side  = 1 if i < 4 else -1
        pair  = i % 4
        angle = (pair - 1.5) * 30
        rad   = math.radians(angle)
        lx    = 10 + math.cos(rad) * 14
        ly    = side * (30 + pair * 12)
        bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=4, depth=80,
                                             location=(lx, ly * 0.82, 36),
                                             rotation=(0.32, 0,
                                                       math.pi / 2 + math.radians(angle) * 0.4))
        apply_mat(bpy.context.active_object, m_body)
    export("spider.dae")


def mk_boar():
    clear()
    m_body = mat("boar_body", 0.44, 0.30, 0.20)
    m_tusk = mat("boar_tusk", 0.84, 0.80, 0.65)
    # Body
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8,
                                          radius=46, location=(0, 0, 50))
    bpy.context.active_object.scale = (1.32, 0.72, 0.90)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_body)
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=26, location=(66, 0, 54))
    bpy.context.active_object.scale = (1.20, 0.86, 0.86)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_body)
    # Snout
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=10, depth=16,
                                         location=(95, 0, 50),
                                         rotation=(0, math.pi / 2, 0))
    apply_mat(bpy.context.active_object, m_body)
    # Tusks
    for ty in [-8, 8]:
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=4, radius2=1,
                                         depth=26, location=(102, ty, 44),
                                         rotation=(math.pi * 0.3, 0, 0))
        apply_mat(bpy.context.active_object, m_tusk)
    # Legs
    for (lx, ly) in [(24, 30), (24, -30), (-26, 30), (-26, -30)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=10, depth=50,
                                             location=(lx, ly, 22))
        apply_mat(bpy.context.active_object, m_body)
    # Tail
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=4, depth=24,
                                         location=(-60, 0, 65),
                                         rotation=(math.pi / 3, 0, 0))
    apply_mat(bpy.context.active_object, m_body)
    export("boar.dae")


# ─── TROLL BODY PARTS (for NPC rendering) ────────────────────────────────

def mk_troll_head():
    """Troll head with tusks and pronounced brow — used as BODY part 0."""
    clear()
    m_skin = mat("troll_skin",  0.28, 0.44, 0.30)
    m_tusk = mat("troll_tusk",  0.84, 0.80, 0.65)
    m_eye  = mat("troll_eye",   0.88, 0.72, 0.10)
    m_hair = mat("troll_hair",  0.08, 0.30, 0.10)
    # Head sphere (slightly elongated)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8,
                                          radius=18, location=(0, 0, 0))
    bpy.context.active_object.scale = (0.95, 0.90, 1.05)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_skin)
    # Pronounced brow ridge
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -17, 6))
    bpy.context.active_object.scale = (32, 5, 5)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_skin)
    # Eyes
    for ex in [-8, 8]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4,
                                              radius=4, location=(ex, -16, 4))
        apply_mat(bpy.context.active_object, m_eye)
    # Lower jaw / chin protrusion
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -14, -10))
    bpy.context.active_object.scale = (22, 7, 10)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_skin)
    # Tusks (lower jaw)
    for tx in [-7, 7]:
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=3, radius2=0.5,
                                         depth=16, location=(tx, -18, -14),
                                         rotation=(-0.35, 0, 0))
        apply_mat(bpy.context.active_object, m_tusk)
    # Wild hair (cluster of cylinders)
    for (hx, hy, ha) in [(0, 5, 0), (-8, 4, -0.3), (8, 4, 0.3),
                          (-5, 6, -0.5), (5, 6, 0.5), (0, 7, 0.2)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=3, depth=22,
                                             location=(hx, hy, 26),
                                             rotation=(ha, 0, 0))
        apply_mat(bpy.context.active_object, m_hair)
    export("troll_head.dae")


def mk_troll_hair():
    """Troll wild dreadlocks — used as BODY part hair (1)."""
    clear()
    m_hair = mat("troll_hair_h", 0.08, 0.30, 0.10)
    # Wild dreadlocks cluster
    for (hx, hy, ha) in [(0, 5, 0), (-8, 4, -0.3), (8, 4, 0.3),
                          (-5, 6, -0.5), (5, 6, 0.5), (0, 7, 0.2),
                          (-10, 2, -0.4), (10, 2, 0.4)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=3, depth=22,
                                             location=(hx, hy, 14),
                                             rotation=(ha, 0, 0))
        apply_mat(bpy.context.active_object, m_hair)
    export("troll_hair.dae")


def mk_troll_body():
    """Troll torso + arms — used as BODY part chest (3)."""
    clear()
    m_skin = mat("troll_skin_b", 0.28, 0.44, 0.30)
    m_hide = mat("troll_hide",   0.42, 0.28, 0.12)
    # Torso (barrel-chested)
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=26, depth=58,
                                         location=(0, 0, 0))
    apply_mat(bpy.context.active_object, m_skin)
    # Shoulders
    for sx in [-30, 30]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                              radius=14, location=(sx, 0, 22))
        apply_mat(bpy.context.active_object, m_skin)
    # Upper arms
    for sx in [-44, 44]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=10, depth=40,
                                             location=(sx, 0, 8),
                                             rotation=(0, math.pi / 2, 0))
        apply_mat(bpy.context.active_object, m_skin)
    # Forearms
    for sx in [-76, 76]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=8, depth=38,
                                             location=(sx, 0, 2),
                                             rotation=(0, math.pi / 2, 0))
        apply_mat(bpy.context.active_object, m_skin)
    # Hide loincloth/belt
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=28, depth=14,
                                         location=(0, 0, -30))
    apply_mat(bpy.context.active_object, m_hide)
    export("troll_body.dae")


def mk_troll_legs():
    """Troll lower body + legs — used as BODY part groin (4)."""
    clear()
    m_skin = mat("troll_skin_l", 0.28, 0.44, 0.30)
    m_hide = mat("troll_leg_hide", 0.38, 0.24, 0.10)
    for lx in [-14, 14]:
        # Thigh
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=13, depth=44,
                                             location=(lx, 0, -22))
        apply_mat(bpy.context.active_object, m_skin)
        # Knee
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=5,
                                              radius=12, location=(lx, 0, -46))
        apply_mat(bpy.context.active_object, m_skin)
        # Lower leg
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=10, depth=42,
                                             location=(lx, 0, -68))
        apply_mat(bpy.context.active_object, m_skin)
        # Foot
        bpy.ops.mesh.primitive_cube_add(size=1, location=(lx, -8, -92))
        bpy.context.active_object.scale = (14, 20, 8)
        bpy.ops.object.transform_apply(scale=True)
        apply_mat(bpy.context.active_object, m_skin)
    # Loincloth strip
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -6, -2))
    bpy.context.active_object.scale = (24, 5, 16)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_hide)
    export("troll_legs.dae")


def mk_troll_hands():
    """Troll hands — used as BODY part right hand (6) and left hand (7)."""
    clear()
    m = mat("troll_hand", 0.28, 0.44, 0.30)
    # Palm
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    bpy.context.active_object.scale = (14, 8, 18)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    # Stubby fingers
    for fx in [-8, -3, 3, 8]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=3, depth=14,
                                             location=(fx, -2, 16))
        apply_mat(bpy.context.active_object, m)
    # Thumb
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=3, depth=12,
                                         location=(10, 0, 5),
                                         rotation=(0, 0.8, 0))
    apply_mat(bpy.context.active_object, m)
    export("troll_hands.dae")


# ─── SURVIVAL OBJECTS ─────────────────────────────────────────────────────

def mk_workbench():
    """Crafting table: flat rectangular top on 4 legs."""
    clear()
    m = mat("workbench", 0.45, 0.30, 0.15)
    # Table top
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 50))
    bpy.context.active_object.scale = (50, 30, 4)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    # 4 legs at corners
    for (lx, ly) in [(42, 22), (-42, 22), (42, -22), (-42, -22)]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(lx, ly, 23))
        bpy.context.active_object.scale = (4, 4, 25)
        bpy.ops.object.transform_apply(scale=True)
        apply_mat(bpy.context.active_object, m)
    export("workbench.dae")


def mk_tannery():
    """Hide-drying A-frame rack: two angled poles meeting at top, crossbar, hide plane."""
    clear()
    m_wood = mat("tannery_wood", 0.50, 0.28, 0.08)
    m_hide = mat("tannery_hide", 0.65, 0.45, 0.25)
    m_rope = mat("tannery_rope", 0.40, 0.35, 0.20)
    # Left A-frame leg (angled inward)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=5, depth=140,
                                         location=(-40, 0, 55),
                                         rotation=(0, 0.35, 0))
    apply_mat(bpy.context.active_object, m_wood)
    # Right A-frame leg (angled inward opposite)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=5, depth=140,
                                         location=(40, 0, 55),
                                         rotation=(0, -0.35, 0))
    apply_mat(bpy.context.active_object, m_wood)
    # Top crossbar connecting the two legs
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=4, depth=100,
                                         location=(0, 0, 118),
                                         rotation=(0, math.pi / 2, 0))
    apply_mat(bpy.context.active_object, m_wood)
    # Lower crossbar for stability
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=3, depth=90,
                                         location=(0, 0, 40),
                                         rotation=(0, math.pi / 2, 0))
    apply_mat(bpy.context.active_object, m_wood)
    # Hide draped over top bar (flat plane, slightly angled)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 105))
    bpy.context.active_object.scale = (35, 50, 1)
    bpy.ops.object.transform_apply(scale=True)
    bpy.context.active_object.rotation_euler = (0.4, 0, 0)
    apply_mat(bpy.context.active_object, m_hide)
    # Rope lashings at top
    for x in [-20, 20]:
        bpy.ops.mesh.primitive_torus_add(major_radius=7, minor_radius=2,
                                          major_segments=8, minor_segments=4,
                                          location=(x, 0, 118))
        apply_mat(bpy.context.active_object, m_rope)
    export("tannery.dae")


def mk_armory():
    """Weapon rack: two vertical poles with horizontal bars and crossed sticks."""
    clear()
    m_wood = mat("armory_wood", 0.38, 0.22, 0.06)
    m_bar  = mat("armory_bar",  0.55, 0.35, 0.12)
    m_bone = mat("armory_bone", 0.78, 0.74, 0.60)
    # Two vertical side poles
    for x in [-50, 50]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=6, depth=160,
                                             location=(x, 0, 80))
        apply_mat(bpy.context.active_object, m_wood)
    # Three horizontal bars for hanging weapons
    for z in [40, 80, 120]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=4, depth=110,
                                             location=(0, 0, z),
                                             rotation=(0, math.pi / 2, 0))
        apply_mat(bpy.context.active_object, m_bar)
    # Decorative crossed sticks on front
    for rot_z in [0.5, -0.5]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=3, depth=80,
                                             location=(0, -8, 80),
                                             rotation=(0, 0, rot_z))
        apply_mat(bpy.context.active_object, m_bone)
    # Bone ornament on top
    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4,
                                          radius=10, location=(0, 0, 168))
    apply_mat(bpy.context.active_object, m_bone)
    export("armory.dae")


def mk_forge():
    """Stone furnace: large stone block base with glowing orange top surface."""
    clear()
    m_stone = mat("forge_stone", 0.35, 0.32, 0.30)
    m_glow  = mat("forge_glow",  0.95, 0.45, 0.05)
    m_dark  = mat("forge_dark",  0.20, 0.18, 0.16)
    # Main stone block base
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 40))
    bpy.context.active_object.scale = (55, 45, 40)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_stone)
    # Chimney / raised back wall
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 30, 80))
    bpy.context.active_object.scale = (50, 10, 35)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_dark)
    # Glowing hot top surface (recessed)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 81))
    bpy.context.active_object.scale = (42, 32, 3)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_glow)
    # Side stone supports
    for x in [-52, 52]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 25))
        bpy.context.active_object.scale = (8, 35, 25)
        bpy.ops.object.transform_apply(scale=True)
        apply_mat(bpy.context.active_object, m_stone)
    # Small bellows hint (cylinder on side)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=12, depth=20,
                                         location=(-68, 0, 40),
                                         rotation=(0, math.pi / 2, 0))
    apply_mat(bpy.context.active_object, m_dark)
    export("forge.dae")


def mk_cauldron():
    """Large round pot (half-sphere) on three legs with greenish brew inside."""
    clear()
    m_iron = mat("cauldron_iron", 0.18, 0.18, 0.20)
    m_brew = mat("cauldron_brew", 0.15, 0.55, 0.20)
    m_rim  = mat("cauldron_rim",  0.25, 0.22, 0.22)
    # Pot body (top half of sphere — full sphere scaled to cut bottom)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=10,
                                          radius=55, location=(0, 0, 55))
    bpy.context.active_object.scale = (1.0, 1.0, 0.6)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_iron)
    # Brew surface inside (flat disc near top)
    bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=48, depth=3,
                                         location=(0, 0, 72))
    apply_mat(bpy.context.active_object, m_brew)
    # Rim ring
    bpy.ops.mesh.primitive_torus_add(major_radius=55, minor_radius=4,
                                      major_segments=14, minor_segments=6,
                                      location=(0, 0, 78))
    apply_mat(bpy.context.active_object, m_rim)
    # Three legs (120 degrees apart)
    for angle in [0, 120, 240]:
        rad = math.radians(angle)
        lx = math.cos(rad) * 40
        ly = math.sin(rad) * 40
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=5, depth=50,
                                             location=(lx, ly, 12),
                                             rotation=(0, 0, 0))
        apply_mat(bpy.context.active_object, m_iron)
    # Handle arch over top
    bpy.ops.mesh.primitive_torus_add(major_radius=42, minor_radius=3,
                                      major_segments=12, minor_segments=4,
                                      location=(0, 0, 88),
                                      rotation=(math.pi / 2, 0, 0))
    bpy.context.active_object.scale = (0.3, 1.0, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_iron)
    export("cauldron.dae")


def mk_build_site():
    """Small pile of crossed sticks as a build-site marker."""
    clear()
    m = mat("build_site", 0.60, 0.50, 0.30)
    # 3 crossed thin cylinders at different angles
    angles = [(0.5, 0.0, 0.0), (-0.3, 0.0, 0.8), (0.2, 0.6, -0.4)]
    for rot in angles:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=3, depth=40,
                                             location=(0, 0, 10),
                                             rotation=rot)
        apply_mat(bpy.context.active_object, m)
    export("build_site.dae")


def mk_raw_meat():
    """Small slab of raw meat — flattened UV sphere."""
    clear()
    m = mat("raw_meat", 0.70, 0.15, 0.10)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8,
                                          radius=15, location=(0, 0, 5))
    bpy.context.active_object.scale = (1.2, 0.8, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    export("raw_meat.dae")


def mk_spider_silk():
    """Small wispy ball of spider silk."""
    clear()
    m = mat("spider_silk", 0.85, 0.85, 0.80)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=8, location=(0, 0, 8))
    apply_mat(bpy.context.active_object, m)
    export("spider_silk.dae")


# ─── GROUND PICKABLES ────────────────────────────────────────────────

def mk_stick():
    """A small stick lying on the ground."""
    clear()
    m = mat("stick", 0.50, 0.32, 0.10)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=2, depth=40,
                                         location=(0, 0, 2),
                                         rotation=(0, math.pi / 2, 0.3))
    apply_mat(bpy.context.active_object, m)
    # Small branch
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=1.5, depth=14,
                                         location=(12, 4, 5),
                                         rotation=(0.4, 0.3, 0.6))
    apply_mat(bpy.context.active_object, m)
    export("stick.dae")


def mk_stone_item():
    """A small rock on the ground."""
    clear()
    m = mat("stone_item", 0.55, 0.52, 0.50)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=10,
                                           location=(0, 0, 6))
    bpy.context.active_object.scale = (1.2, 0.9, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    export("stone_item.dae")


def mk_flint():
    """A sharp flint shard."""
    clear()
    m = mat("flint", 0.30, 0.28, 0.32)
    bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=8, radius2=1,
                                     depth=14, location=(0, 0, 5),
                                     rotation=(0.2, 0, 0))
    apply_mat(bpy.context.active_object, m)
    export("flint.dae")


def mk_tinder():
    """A small clump of dry grass/tinder."""
    clear()
    m = mat("tinder", 0.72, 0.65, 0.35)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=8, location=(0, 0, 5))
    bpy.context.active_object.scale = (1.4, 1.0, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m)
    export("tinder.dae")


def mk_jungle_berry():
    """Small cluster of berries on the ground."""
    clear()
    m_leaf = mat("berry_leaf", 0.15, 0.50, 0.10)
    m_berry = mat("berry_red", 0.75, 0.10, 0.15)
    # Leaf base
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=12, depth=4,
                                         location=(0, 0, 2))
    apply_mat(bpy.context.active_object, m_leaf)
    # Berries
    for (bx, by) in [(-4, -3), (4, -2), (0, 5), (-6, 4), (5, 4)]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4,
                                              radius=4, location=(bx, by, 7))
        apply_mat(bpy.context.active_object, m_berry)
    export("jungle_berry.dae")


def mk_jungle_root():
    """A gnarled root on the ground."""
    clear()
    m = mat("root", 0.40, 0.25, 0.08)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=4, depth=30,
                                         location=(0, 0, 3),
                                         rotation=(0, math.pi / 2, 0.5))
    apply_mat(bpy.context.active_object, m)
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=3, depth=18,
                                         location=(10, 6, 4),
                                         rotation=(0.3, 0.6, 0.2))
    apply_mat(bpy.context.active_object, m)
    export("jungle_root.dae")


def mk_jungle_mushroom():
    """A small glowing mushroom ingredient."""
    clear()
    m_stem = mat("ingr_mush_stem", 0.65, 0.55, 0.45)
    m_cap  = mat("ingr_mush_cap",  0.10, 0.70, 0.45)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=4, depth=14,
                                         location=(0, 0, 7))
    apply_mat(bpy.context.active_object, m_stem)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                          radius=10, location=(0, 0, 18))
    bpy.context.active_object.scale = (1.0, 1.0, 0.6)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_cap)
    export("jungle_mushroom.dae")


def mk_hut_floor():
    """Large flat wooden floor slab for the Troll Hut interior."""
    clear()
    m_wood = mat("hut_floor", 0.42, 0.28, 0.14)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    bpy.context.active_object.scale = (1000, 1000, 100)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_wood)
    export("hut_floor.dae")


def mk_tome():
    """Generic book / tome mesh used by BOOK records."""
    clear()
    m_cover = mat("tome_cover", 0.40, 0.20, 0.06)
    m_pages = mat("tome_pages", 0.90, 0.85, 0.70)
    # Cover
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 6))
    bpy.context.active_object.scale = (20, 28, 4)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_cover)
    # Pages
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 6))
    bpy.context.active_object.scale = (18, 26, 3)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_pages)
    export("tome_tribal.dae")
    clear()
    m_cover2 = mat("recipe_cover", 0.15, 0.35, 0.12)
    m_pages2 = mat("recipe_pages", 0.90, 0.85, 0.70)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 6))
    bpy.context.active_object.scale = (20, 28, 4)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_cover2)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 6))
    bpy.context.active_object.scale = (18, 26, 3)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_pages2)
    export("tome_recipes.dae")


# ─── RUN ALL ──────────────────────────────────────────────────────────────

print("\n=== Generating JTT placeholder meshes ===\n")
print("Environment:")
mk_totem_pole()
mk_troll_hut()
mk_voodoo_shrine()
mk_wood_node()
mk_stone_node()
mk_herb_node()
mk_tribal_chest()
mk_herb_basket()
mk_resource_pile()
mk_fire_pit()
mk_bone_torch()
mk_glow_mushroom()
mk_troll_door()
mk_hut_floor()

def mk_spider_web():
    """A large flat web stretched between anchor points."""
    clear()
    m_web = mat("web_silk", 0.90, 0.90, 0.85)
    # Central disc
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=40, depth=2,
                                         location=(0, 0, 60))
    apply_mat(bpy.context.active_object, m_web)
    # Radial strands
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=2, depth=80,
                                             location=(math.cos(rad)*40,
                                                       math.sin(rad)*40, 60),
                                             rotation=(0, 0, rad))
        apply_mat(bpy.context.active_object, m_web)
    export("spider_web.dae")


def mk_bear_den():
    """A rocky cave entrance mound."""
    clear()
    m_rock = mat("den_rock", 0.35, 0.30, 0.25)
    m_dark = mat("den_shadow", 0.12, 0.10, 0.08)
    # Main mound
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8,
                                          radius=55, location=(0, 0, 30))
    bpy.context.active_object.scale = (1.0, 0.8, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    apply_mat(bpy.context.active_object, m_rock)
    # Dark cave opening
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=22, depth=20,
                                         location=(0, 45, 20))
    apply_mat(bpy.context.active_object, m_dark)
    export("bear_den.dae")


def mk_tidal_pool():
    """A shallow rocky tidal pool."""
    clear()
    m_rock = mat("pool_rock", 0.45, 0.40, 0.35)
    m_water = mat("pool_water", 0.15, 0.50, 0.60)
    # Rocky rim
    bpy.ops.mesh.primitive_torus_add(major_radius=50, minor_radius=12,
                                      major_segments=16, minor_segments=8,
                                      location=(0, 0, 6))
    apply_mat(bpy.context.active_object, m_rock)
    # Water surface
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=38, depth=4,
                                         location=(0, 0, 2))
    apply_mat(bpy.context.active_object, m_water)
    export("tidal_pool.dae")


def mk_mushroom_patch():
    """A cluster of large glowing mushrooms."""
    clear()
    m_stem = mat("patch_stem", 0.60, 0.52, 0.42)
    m_cap1 = mat("patch_cap1", 0.08, 0.75, 0.45)
    m_cap2 = mat("patch_cap2", 0.50, 0.20, 0.70)
    offsets = [(0, 0, 20), (25, 15, 15), (-20, 20, 12), (15, -25, 18)]
    caps = [m_cap1, m_cap2, m_cap1, m_cap2]
    for (ox, oy, h), cap in zip(offsets, caps):
        r = h * 0.35
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=max(3, r*0.4),
                                             depth=h, location=(ox, oy, h/2))
        apply_mat(bpy.context.active_object, m_stem)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6,
                                              radius=r, location=(ox, oy, h))
        bpy.context.active_object.scale = (1.0, 1.0, 0.55)
        bpy.ops.object.transform_apply(scale=True)
        apply_mat(bpy.context.active_object, cap)
    export("mushroom_patch.dae")


print("Weapons:")
mk_bone_club()
mk_stone_hatchet()
mk_obsidian_spear()
mk_flint_dagger()
mk_vine_whip()
mk_war_maul()
mk_wooden_bow()
mk_stone_arrow()

print("Armor:")
mk_bone_shield()
mk_hide_cuirass()
mk_bone_helm()
mk_bark_pauldron()

print("Misc items:")
mk_tribal_drum()
mk_voodoo_doll()
mk_troll_idol()
mk_shell_token()

print("Creatures:")
mk_panther()
mk_croc()
mk_spider()
mk_boar()

print("Troll body parts (for NPC rendering):")
mk_troll_head()
mk_troll_hair()
mk_troll_body()
mk_troll_legs()
mk_troll_hands()

# --- survival objects ---
print("Survival objects:")
mk_workbench()
mk_build_site()
mk_raw_meat()
mk_spider_silk()

print("Crafting stations:")
mk_tannery()
mk_armory()
mk_forge()
mk_cauldron()

print("Ground pickables:")
mk_stick()
mk_stone_item()
mk_flint()
mk_tinder()
mk_jungle_berry()
mk_jungle_root()
mk_jungle_mushroom()
mk_tome()

print("Biome harvest nodes:")
mk_spider_web()
mk_bear_den()
mk_tidal_pool()
mk_mushroom_patch()

print(f"\n=== Done! Meshes written to: {OUT} ===\n")
