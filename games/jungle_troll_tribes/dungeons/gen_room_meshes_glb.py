#!/usr/bin/env python3
"""
gen_room_meshes_glb.py
Generate cave room GLB meshes (glTF 2.0) for OpenMW 0.47+.
Textures are embedded directly in the GLB — no VFS texture path lookup needed.
Run: python3 gen_room_meshes_glb.py
"""
import json
import struct
import math
from pathlib import Path

GAME_DIR = Path(__file__).parents[1]
OUT_DIR  = GAME_DIR / "meshes" / "omwdg"
TEX_FILE = GAME_DIR / "textures" / "omwdg" / "cave_stone.png"

# Room dimensions (must match cave_roomkit.py)
HALF   = 512.0    # room_size/2 = (4 tiles * 256) / 2
H      = 256.0    # room height
DW     = 128.0    # doorway half-width  (total 256)
DH     = 200.0    # doorway height

UV = lambda world: world / 256.0   # 1 texture tile per 256 units


# ---------------------------------------------------------------------------
# Geometry builder
# ---------------------------------------------------------------------------

class MeshBuilder:
    def __init__(self):
        self.pos: list[tuple] = []
        self.nor: list[tuple] = []
        self.uvs: list[tuple] = []
        self.idx: list[int]   = []

    def quad(self, v0, v1, v2, v3, n, u0, u1, u2, u3):
        """Add a CCW quad as 2 triangles with a fixed normal."""
        b = len(self.pos)
        for v, u in ((v0,u0),(v1,u1),(v2,u2),(v3,u3)):
            self.pos.append(v)
            self.nor.append(n)
            self.uvs.append(u)
        self.idx += [b, b+1, b+2, b, b+2, b+3]

    # ------------------------------------------------------------------
    # Axis-aligned surface helpers
    # ------------------------------------------------------------------

    def floor_rect(self, x0, y0, x1, y1, z):
        """Horizontal floor quad (normal +Z)."""
        n = (0,0,1)
        self.quad(
            (x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z), n,
            (UV(x0+HALF),UV(y0+HALF)), (UV(x1+HALF),UV(y0+HALF)),
            (UV(x1+HALF),UV(y1+HALF)), (UV(x0+HALF),UV(y1+HALF)),
        )

    def ceil_rect(self, x0, y0, x1, y1, z):
        """Horizontal ceiling quad (normal -Z)."""
        n = (0,0,-1)
        self.quad(
            (x0,y1,z),(x1,y1,z),(x1,y0,z),(x0,y0,z), n,
            (UV(x0+HALF),UV(y1+HALF)), (UV(x1+HALF),UV(y1+HALF)),
            (UV(x1+HALF),UV(y0+HALF)), (UV(x0+HALF),UV(y0+HALF)),
        )

    def north_wall_rect(self, x0, x1, z0, z1):
        """Wall on north face (Y=+HALF, normal -Y)."""
        y = HALF
        n = (0,-1,0)
        self.quad(
            (x0,y,z0),(x1,y,z0),(x1,y,z1),(x0,y,z1), n,
            (UV(x0+HALF),UV(z0)), (UV(x1+HALF),UV(z0)),
            (UV(x1+HALF),UV(z1)), (UV(x0+HALF),UV(z1)),
        )

    def south_wall_rect(self, x0, x1, z0, z1):
        """Wall on south face (Y=-HALF, normal +Y)."""
        y = -HALF
        n = (0,1,0)
        self.quad(
            (x1,y,z0),(x0,y,z0),(x0,y,z1),(x1,y,z1), n,
            (UV(x1+HALF),UV(z0)), (UV(x0+HALF),UV(z0)),
            (UV(x0+HALF),UV(z1)), (UV(x1+HALF),UV(z1)),
        )

    def east_wall_rect(self, y0, y1, z0, z1):
        """Wall on east face (X=+HALF, normal -X)."""
        x = HALF
        n = (-1,0,0)
        self.quad(
            (x,y1,z0),(x,y0,z0),(x,y0,z1),(x,y1,z1), n,
            (UV(y1+HALF),UV(z0)), (UV(y0+HALF),UV(z0)),
            (UV(y0+HALF),UV(z1)), (UV(y1+HALF),UV(z1)),
        )

    def west_wall_rect(self, y0, y1, z0, z1):
        """Wall on west face (X=-HALF, normal +X)."""
        x = -HALF
        n = (1,0,0)
        self.quad(
            (x,y0,z0),(x,y1,z0),(x,y1,z1),(x,y0,z1), n,
            (UV(y0+HALF),UV(z0)), (UV(y1+HALF),UV(z0)),
            (UV(y1+HALF),UV(z1)), (UV(y0+HALF),UV(z1)),
        )

    def pillar(self, cx, cy, size=64.0):
        """Square pillar from floor to ceiling at (cx, cy)."""
        h = size / 2
        # 4 faces
        self.north_wall_rect(cx-h, cx+h, 0, H)  # north face of pillar (y=cy+h)
        self.south_wall_rect(cx-h, cx+h, 0, H)
        self.east_wall_rect(cy-h, cy+h, 0, H)
        self.west_wall_rect(cy-h, cy+h, 0, H)

    # ------------------------------------------------------------------
    # Standard room shell
    # ------------------------------------------------------------------

    def add_room_shell(self):
        """Floor + ceiling + 4 walls each with a centred doorway."""
        # Floor & ceiling
        self.floor_rect(-HALF, -HALF, HALF, HALF, 0)
        self.ceil_rect(-HALF, -HALF, HALF, HALF, H)

        # Each wall: left panel, right panel, top-over-door panel
        for wall_fn_l, wall_fn_r, wall_fn_t in [
            (self.north_wall_rect, self.north_wall_rect, self.north_wall_rect),
            (self.south_wall_rect, self.south_wall_rect, self.south_wall_rect),
            (self.east_wall_rect,  self.east_wall_rect,  self.east_wall_rect),
            (self.west_wall_rect,  self.west_wall_rect,  self.west_wall_rect),
        ]:
            pass  # handled below

        for add_wall in (self._north_wall, self._south_wall,
                         self._east_wall,  self._west_wall):
            add_wall()

    def _north_wall(self):
        self.north_wall_rect(-HALF, -DW,  0,  H)   # left
        self.north_wall_rect( DW,  HALF,  0,  H)   # right
        self.north_wall_rect(-DW,   DW,  DH,  H)   # over doorway

    def _south_wall(self):
        self.south_wall_rect(-HALF, -DW,  0,  H)
        self.south_wall_rect( DW,  HALF,  0,  H)
        self.south_wall_rect(-DW,   DW,  DH,  H)

    def _east_wall(self):
        self.east_wall_rect(-HALF, -DW,  0,  H)
        self.east_wall_rect( DW,  HALF,  0,  H)
        self.east_wall_rect(-DW,   DW,  DH,  H)

    def _west_wall(self):
        self.west_wall_rect(-HALF, -DW,  0,  H)
        self.west_wall_rect( DW,  HALF,  0,  H)
        self.west_wall_rect(-DW,   DW,  DH,  H)


# ---------------------------------------------------------------------------
# GLB serialisation
# ---------------------------------------------------------------------------

def _pad4(data: bytes) -> bytes:
    rem = len(data) % 4
    return data if rem == 0 else data + bytes(4 - rem)


def build_glb(mb: MeshBuilder, texture_bytes: bytes) -> bytes:
    # Pack vertex data
    pos_data = _pad4(b''.join(struct.pack('<fff', *p) for p in mb.pos))
    nor_data = _pad4(b''.join(struct.pack('<fff', *n) for n in mb.nor))
    uv_data  = _pad4(b''.join(struct.pack('<ff',  *u) for u in mb.uvs))

    use_u32 = len(mb.pos) > 65535
    idx_fmt  = '<I' if use_u32 else '<H'
    idx_ct   = 5125 if use_u32 else 5123
    idx_data = _pad4(b''.join(struct.pack(idx_fmt, i) for i in mb.idx))
    tex_data = _pad4(texture_bytes)

    # Buffer layout
    off_pos = 0
    off_nor = off_pos + len(pos_data)
    off_uv  = off_nor + len(nor_data)
    off_idx = off_uv  + len(uv_data)
    off_tex = off_idx + len(idx_data)
    total   = off_tex + len(tex_data)

    binary  = pos_data + nor_data + uv_data + idx_data + tex_data

    xs = [p[0] for p in mb.pos]; ys = [p[1] for p in mb.pos]; zs = [p[2] for p in mb.pos]
    nv = len(mb.pos); ni = len(mb.idx)

    gltf = {
        "asset": {"version": "2.0", "generator": "gen_room_meshes_glb.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{
            "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
            "indices": 3,
            "material": 0
        }]}],
        "materials": [{"name": "cave_rock", "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0, "texCoord": 0},
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0
            }
        }],
        "textures": [{"sampler": 0, "source": 0}],
        "images":   [{"bufferView": 4, "mimeType": "image/png"}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987,
                      "wrapS": 10497, "wrapT": 10497}],
        "accessors": [
            {"bufferView":0,"byteOffset":0,"componentType":5126,"count":nv,
             "type":"VEC3","min":[min(xs),min(ys),min(zs)],"max":[max(xs),max(ys),max(zs)]},
            {"bufferView":1,"byteOffset":0,"componentType":5126,"count":nv,"type":"VEC3"},
            {"bufferView":2,"byteOffset":0,"componentType":5126,"count":nv,"type":"VEC2"},
            {"bufferView":3,"byteOffset":0,"componentType":idx_ct,"count":ni,"type":"SCALAR"},
        ],
        "bufferViews": [
            {"buffer":0,"byteOffset":off_pos,"byteLength":len(pos_data),"target":34962},
            {"buffer":0,"byteOffset":off_nor,"byteLength":len(nor_data),"target":34962},
            {"buffer":0,"byteOffset":off_uv, "byteLength":len(uv_data), "target":34962},
            {"buffer":0,"byteOffset":off_idx,"byteLength":len(idx_data),"target":34963},
            {"buffer":0,"byteOffset":off_tex,"byteLength":len(texture_bytes)},
        ],
        "buffers": [{"byteLength": total}],
    }

    json_bytes  = _pad4(json.dumps(gltf, separators=(',',':')).encode() + b' ')
    json_chunk  = struct.pack('<II', len(json_bytes), 0x4E4F534A) + json_bytes
    bin_chunk   = struct.pack('<II', len(binary),     0x004E4942) + binary
    total_size  = 12 + len(json_chunk) + len(bin_chunk)
    header      = struct.pack('<III', 0x46546C67, 2, total_size)
    return header + json_chunk + bin_chunk


# ---------------------------------------------------------------------------
# Room variant builders
# ---------------------------------------------------------------------------

def make_room(variant: str) -> MeshBuilder:
    mb = MeshBuilder()
    mb.add_room_shell()

    if variant == 'b':   # central pillar
        mb.pillar(0, 0)
    elif variant == 'c': # two pillars
        mb.pillar(-200, 0); mb.pillar(200, 0)
    elif variant == 'd': # ledge along south wall
        # Low platform (128 wide, 64 tall) along south wall
        bx0, bx1, by0, by1, bz = -256.0, 256.0, -HALF+64, -HALF+192, 80.0
        mb.floor_rect(bx0, by0, bx1, by1, bz)
        mb.south_wall_rect(bx0, bx1, 0, bz)  # front face of ledge
        mb.east_wall_rect(by0, by1, 0, bz)
        mb.west_wall_rect(by0, by1, 0, bz)
    elif variant == 'e': # two pillars offset
        mb.pillar(-300, -200); mb.pillar(300, 200)
    elif variant == 'f': # altar / raised platform in centre
        s = 160.0
        mb.floor_rect(-s/2, -s/2, s/2, s/2, 48.0)
        mb.north_wall_rect(-s/2, s/2, 0, 48.0)
        mb.south_wall_rect(-s/2, s/2, 0, 48.0)
        mb.east_wall_rect(-s/2, s/2, 0, 48.0)
        mb.west_wall_rect(-s/2, s/2, 0, 48.0)
    elif variant == 'g': # corner pillars
        for cx, cy in ((-300,-300),(300,-300),(-300,300),(300,300)):
            mb.pillar(cx, cy, 80.0)
    elif variant == 'h': # cross formation (4 pillars in cross)
        for cx, cy in ((0,-280),(0,280),(-280,0),(280,0)):
            mb.pillar(cx, cy)
    elif variant == 'i': # boulder (octagonal low platform)
        r = 128.0
        mb.floor_rect(-r, -r, r, r, 64.0)
        mb.north_wall_rect(-r, r, 0, 64.0)
        mb.south_wall_rect(-r, r, 0, 64.0)
        mb.east_wall_rect(-r, r, 0, 64.0)
        mb.west_wall_rect(-r, r, 0, 64.0)
    elif variant == 'j': # three pillars triangle
        for cx, cy in ((0, 250),(-200,-180),(200,-180)):
            mb.pillar(cx, cy)
    # variant 'a': bare room — nothing extra

    return mb


def make_corridor() -> MeshBuilder:
    """256×256×256 corridor: open north/south, walls east/west + floor + ceiling."""
    mb = MeshBuilder()
    # Narrow corridor: 256 wide (X), 256 deep (Y), 256 tall (Z)
    # Open at Y = ±128 (no walls N/S), walls at X = ±128
    CSIZE = 128.0
    mb.floor_rect(-CSIZE, -CSIZE, CSIZE, CSIZE, 0)
    mb.ceil_rect(-CSIZE, -CSIZE, CSIZE, CSIZE, H)
    mb.east_wall_rect(-CSIZE, CSIZE, 0, H)
    mb.west_wall_rect(-CSIZE, CSIZE, 0, H)
    return mb


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tex_bytes = TEX_FILE.read_bytes()
    print(f"Texture: {TEX_FILE} ({len(tex_bytes)} bytes)")

    for letter in 'abcdefghij':
        mb = make_room(letter)
        glb = build_glb(mb, tex_bytes)
        out = OUT_DIR / f"cave_room_{letter}.glb"
        out.write_bytes(glb)
        print(f"  {out.name}  {len(glb)//1024}KB  verts={len(mb.pos)} tris={len(mb.idx)//3}")

    mb_c = make_corridor()
    glb_c = build_glb(mb_c, tex_bytes)
    out_c = OUT_DIR / "cave_corridor.glb"
    out_c.write_bytes(glb_c)
    print(f"  {out_c.name}  {len(glb_c)//1024}KB  verts={len(mb_c.pos)} tris={len(mb_c.idx)//3}")

    print("Done.")


if __name__ == "__main__":
    main()
