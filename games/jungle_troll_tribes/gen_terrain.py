#!/usr/bin/env python3
"""Generate LAND records for Jungle Troll Tribes (cross pattern: 5 cells)."""

import json
import struct
import os

def make_vnml_flat():
    """Flat terrain normals: (0, 0, 127) per vertex."""
    return bytes([0, 0, 127] * 4225)

def make_vtex_empty():
    """Empty texture indices: 256 uint16 zeros."""
    return bytes(512)

def make_wnam(val):
    """9x9 world map heights, all same value."""
    return bytes([val] * 81)

def make_vclr(r, g, b):
    """Uniform vertex colors."""
    return bytes([r, g, b] * 4225)

def make_vclr_beach():
    """Eastern Beach: green on west half, sandy on east half."""
    data = bytearray()
    for y in range(65):
        for x in range(65):
            if x < 32:
                data += bytes([60, 110, 40])
            else:
                data += bytes([180, 160, 100])
    return bytes(data)

def make_vhgt(base_height, offset_func):
    """Build VHGT: float32 base + 65*65 signed int8 offsets + 3 padding.

    offset_func(x, y) returns the ABSOLUTE height offset for vertex (x, y).
    We must encode as row-major delta encoding:
    - First entry of each row is relative to first entry of previous row
    - Subsequent entries in a row are relative to the previous entry in that row
    - First entry of first row is relative to 0
    """
    # Get absolute offsets
    abs_offsets = [[offset_func(x, y) for x in range(65)] for y in range(65)]

    data = struct.pack('<f', base_height)

    prev_row_first = 0
    for y in range(65):
        for x in range(65):
            val = abs_offsets[y][x]
            if x == 0:
                # First column: relative to previous row's first column
                delta = val - prev_row_first
                prev_row_first = val
            else:
                # Other columns: relative to previous column in same row
                delta = val - abs_offsets[y][x - 1]
            # Clamp to int8 range
            delta = max(-128, min(127, delta))
            data += struct.pack('b', delta)

    data += bytes(3)  # padding
    return data

def cell_flat(x, y):
    """All cells flat — zero offset everywhere."""
    return 0

CELLS = [
    {
        "grid_x": 0, "grid_y": 0,
        "base_height": 200.0,
        "offset_func": cell_flat,
        "vclr": make_vclr(50, 130, 50),
        "wnam_val": 0x30,
    },
]

def main():
    records = []
    for cell in CELLS:
        gx, gy = cell["grid_x"], cell["grid_y"]
        vhgt = make_vhgt(cell["base_height"], cell["offset_func"])
        vnml = make_vnml_flat()
        wnam = make_wnam(cell["wnam_val"])
        vclr = cell["vclr"]
        vtex = make_vtex_empty()

        rec = {
            "rec_type": "LAND",
            "record_id": f"Esm3ExteriorCell:{gx}:{gy}",
            "grid_x": gx,
            "grid_y": gy,
            "data_flags": 31,
            "vnml_hex": vnml.hex().upper(),
            "vhgt_hex": vhgt.hex().upper(),
            "wnam_hex": wnam.hex().upper(),
            "vclr_hex": vclr.hex().upper(),
            "vtex_hex": vtex.hex().upper(),
        }
        records.append(rec)

    out_path = os.path.join(os.path.dirname(__file__), "records", "18_land.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)

    # Verify sizes
    expected = {
        "vhgt_hex": 8464,
        "vnml_hex": 25350,
        "wnam_hex": 162,
        "vclr_hex": 25350,
        "vtex_hex": 1024,
    }
    print(f"Wrote {len(records)} LAND records to {out_path}")
    for rec in records:
        rid = rec["record_id"]
        for key, exp_len in expected.items():
            actual = len(rec[key])
            status = "OK" if actual == exp_len else f"FAIL (got {actual})"
            print(f"  {rid} {key}: {status}")

if __name__ == "__main__":
    main()
