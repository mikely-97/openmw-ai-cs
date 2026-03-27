"""
Blender Python script — generates 6 cave tile placeholder meshes.
Run: blender --background --python gen_dungeon_meshes.py
Output: omwtools/omwtools/dungeons/tilesets/meshes/cave/
"""
import bpy
import math
from pathlib import Path

OUT_DIR = Path(__file__).parents[3] / "omwtools" / "omwtools" / "dungeons" / "tilesets" / "meshes" / "cave"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TILE = 4.0
H = 3.0


def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.object.select_all(action='DESELECT')


def export(name: str):
    bpy.ops.object.select_all(action='SELECT')
    path = str(OUT_DIR / f"omwdg_{name}.dae")
    bpy.ops.wm.collada_export(filepath=path, selected=True)
    print(f"Exported: {path}")


def make_floor():
    clear()
    bpy.ops.mesh.primitive_plane_add(size=TILE, location=(0, 0, 0))
    export("cave_floor")


def make_wall():
    clear()
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -TILE / 2, H / 2))
    ob = bpy.context.active_object
    ob.scale = (TILE, 1, H)
    bpy.ops.object.transform_apply(scale=True)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    export("cave_wall")


def make_corner():
    """L-shaped corner: two wall panels at 90 degrees."""
    clear()
    # South face
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -TILE / 2, H / 2))
    ob1 = bpy.context.active_object
    ob1.scale = (TILE, 1, H)
    bpy.ops.object.transform_apply(scale=True)
    ob1.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    # West face
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-TILE / 2, 0, H / 2))
    ob2 = bpy.context.active_object
    ob2.scale = (TILE, 1, H)
    bpy.ops.object.transform_apply(scale=True)
    ob2.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    bpy.ops.object.transform_apply(rotation=True)
    export("cave_corner")


def make_pillar():
    clear()
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H)
    bpy.ops.object.transform_apply(scale=True)
    export("cave_pillar")


def make_doorway():
    """Arch frame: two vertical posts and a lintel."""
    clear()
    # Left post
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(-0.85, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H / 0.3)
    bpy.ops.object.transform_apply(scale=True)
    # Right post
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(0.85, 0, H / 2))
    ob = bpy.context.active_object
    ob.scale = (1, 1, H / 0.3)
    bpy.ops.object.transform_apply(scale=True)
    # Lintel
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(0, 0, H - 0.15))
    ob = bpy.context.active_object
    ob.scale = (TILE / 0.3, 1, 1)
    bpy.ops.object.transform_apply(scale=True)
    export("cave_doorway")


def make_ceiling():
    clear()
    bpy.ops.mesh.primitive_plane_add(size=TILE, location=(0, 0, H))
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.editmode_toggle()
    export("cave_ceiling")


make_floor()
make_wall()
make_corner()
make_pillar()
make_doorway()
make_ceiling()
print("Done — 6 cave tile meshes generated.")
