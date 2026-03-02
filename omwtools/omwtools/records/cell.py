"""CELL record — interior or exterior cell with all cell references.

Subrecords (from components/esm3/loadcell.hpp):
  NAME  → cell name (string for interior; empty for exterior)
  DATA  → 12 bytes: uint32 flags + int32 grid_x + int32 grid_y
  RGNN  → region RefId
  NAM0  → int32 ref_num_counter
  WHGT  → float water_height
  AMBI  → 16 bytes: uint32 ambient + uint32 sunlight + uint32 fog + float fog_density
  NAM5  → int32 map_color (rgba)

  Per-reference:
  FRMR  → uint32 ref_num  [starts a new CellRef]
  NAME  → object RefId
  XSCL  → float scale
  DATA  → 24 bytes: float[3] pos + float[3] rot
  TNAM  → trap/lock flags (optional)
  UNAM  → blocked (1 byte)
  XSOL  → soul RefId
  XCHG  → float enchantment charge
  INTV  → int32 health/charge count
  NAM9  → int32 unknown
  DODT  → destination pos (24 bytes)
  DNAM  → destination cell name
  FLTV  → float lock level
  KNAM  → key RefId
  XOWN  → owner RefId
  XRNK  → int32 owner rank
  XGLB  → global variable RefId (owner global)
  DELE  → 4-byte deletion marker

  MVRF  → moved ref num (uint32)
  CNDT  → moved ref cell coordinates (2×int32)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from omwtools.io.codec import (
    decode_cstring, encode_cstring,
    unpack_f32, unpack_i32, unpack_u32,
    pack_f32, pack_i32, pack_u32,
    pack_subrec_header,
)
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord,
)
from omwtools.records.base import BaseRecord, RawRecord

# Cell DATA flags
CELL_INTERIOR  = 0x01
CELL_HAS_WATER = 0x02
CELL_NO_SLEEP  = 0x04
CELL_QUASI_EXT = 0x80


@dataclass
class CellAmbient:
    ambient: int = 0
    sunlight: int = 0
    fog: int = 0
    fog_density: float = 0.0


@dataclass
class CellRef:
    """One object placed in a cell."""
    ref_num: int = 0
    object_id: RefId = field(default_factory=EmptyRefId)
    scale: float = 1.0
    pos_x: float = 0.0
    pos_y: float = 0.0
    pos_z: float = 0.0
    rot_x: float = 0.0
    rot_y: float = 0.0
    rot_z: float = 0.0
    soul: RefId = field(default_factory=EmptyRefId)
    owner: RefId = field(default_factory=EmptyRefId)
    owner_rank: int = -1
    owner_global: RefId = field(default_factory=EmptyRefId)
    key_id: RefId = field(default_factory=EmptyRefId)
    enchant_charge: float = -1.0
    charge_int: int = -1
    lock_level: float = 0.0
    # destination teleport
    dest_pos: Optional[tuple[float, float, float]] = None
    dest_rot: Optional[tuple[float, float, float]] = None
    dest_cell: str = ""
    trap_id: RefId = field(default_factory=EmptyRefId)
    is_deleted: bool = False
    is_blocked: bool = False


@dataclass
class MovedRef:
    ref_num: int = 0
    cell_x: int = 0
    cell_y: int = 0


@dataclass
class Cell(BaseRecord):
    """CELL record."""

    REC_TYPE = b"CELL"

    flags: int = 0
    unknown: int = 0
    cell_name: str = ""
    cell_flags: int = 0
    grid_x: int = 0
    grid_y: int = 0
    region: RefId = field(default_factory=EmptyRefId)
    ref_num_counter: int = 0
    water_height: Optional[float] = None
    ambient: Optional[CellAmbient] = None
    map_color: Optional[int] = None
    refs: list[CellRef] = field(default_factory=list)
    moved_refs: list[MovedRef] = field(default_factory=list)

    @property
    def is_interior(self) -> bool:
        return bool(self.cell_flags & CELL_INTERIOR)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Cell":
        obj = cls(flags=raw.flags, unknown=raw.unknown)
        subs = raw.subrecords

        def refid_from(sub_type: bytes) -> RefId:
            sub = raw.get_subrecord(sub_type)
            if sub is None:
                return EmptyRefId()
            return decode_refid_from_subrecord(sub.data, format_version)

        # We need to process subrecords in order, maintaining state
        current_ref: Optional[CellRef] = None
        seen_frmr = False  # tracks whether we're inside a ref block

        # First pass: cell-level subrecords appear before any FRMR
        i = 0
        while i < len(subs):
            sub = subs[i]

            if sub.sub_type == b"FRMR":
                # Flush previous ref
                if current_ref is not None:
                    obj.refs.append(current_ref)
                current_ref = CellRef()
                if len(sub.data) >= 4:
                    current_ref.ref_num = unpack_u32(sub.data)
                seen_frmr = True

            elif not seen_frmr:
                # Cell-level subrecords
                if sub.sub_type == b"NAME":
                    obj.cell_name = decode_cstring(sub.data)
                elif sub.sub_type == b"DATA" and len(sub.data) >= 12:
                    obj.cell_flags = unpack_u32(sub.data, 0)
                    obj.grid_x     = unpack_i32(sub.data, 4)
                    obj.grid_y     = unpack_i32(sub.data, 8)
                elif sub.sub_type == b"RGNN":
                    obj.region = decode_refid_from_subrecord(sub.data, format_version)
                elif sub.sub_type == b"NAM0" and len(sub.data) >= 4:
                    obj.ref_num_counter = unpack_i32(sub.data)
                elif sub.sub_type == b"WHGT" and len(sub.data) >= 4:
                    obj.water_height = unpack_f32(sub.data)
                elif sub.sub_type == b"AMBI" and len(sub.data) >= 16:
                    obj.ambient = CellAmbient(
                        ambient     = unpack_u32(sub.data, 0),
                        sunlight    = unpack_u32(sub.data, 4),
                        fog         = unpack_u32(sub.data, 8),
                        fog_density = unpack_f32(sub.data, 12),
                    )
                elif sub.sub_type == b"NAM5" and len(sub.data) >= 4:
                    obj.map_color = unpack_i32(sub.data)
            else:
                # Reference-level subrecords
                if sub.sub_type == b"NAM0" and len(sub.data) >= 4:
                    obj.ref_num_counter = unpack_i32(sub.data)
                elif current_ref is not None:
                    if sub.sub_type == b"NAME":
                        current_ref.object_id = decode_refid_from_subrecord(
                            sub.data, format_version)
                    elif sub.sub_type == b"XSCL" and len(sub.data) >= 4:
                        current_ref.scale = unpack_f32(sub.data)
                    elif sub.sub_type == b"DATA" and len(sub.data) >= 24:
                        current_ref.pos_x = struct.unpack_from("<f", sub.data, 0)[0]
                        current_ref.pos_y = struct.unpack_from("<f", sub.data, 4)[0]
                        current_ref.pos_z = struct.unpack_from("<f", sub.data, 8)[0]
                        current_ref.rot_x = struct.unpack_from("<f", sub.data, 12)[0]
                        current_ref.rot_y = struct.unpack_from("<f", sub.data, 16)[0]
                        current_ref.rot_z = struct.unpack_from("<f", sub.data, 20)[0]
                    elif sub.sub_type == b"XSOL":
                        current_ref.soul = decode_refid_from_subrecord(
                            sub.data, format_version)
                    elif sub.sub_type == b"XOWN":
                        current_ref.owner = decode_refid_from_subrecord(
                            sub.data, format_version)
                    elif sub.sub_type == b"XRNK" and len(sub.data) >= 4:
                        current_ref.owner_rank = unpack_i32(sub.data)
                    elif sub.sub_type == b"XGLB":
                        current_ref.owner_global = decode_refid_from_subrecord(
                            sub.data, format_version)
                    elif sub.sub_type == b"KNAM":
                        current_ref.key_id = decode_refid_from_subrecord(
                            sub.data, format_version)
                    elif sub.sub_type == b"TNAM":
                        current_ref.trap_id = decode_refid_from_subrecord(
                            sub.data, format_version)
                    elif sub.sub_type == b"XCHG" and len(sub.data) >= 4:
                        current_ref.enchant_charge = unpack_f32(sub.data)
                    elif sub.sub_type == b"INTV" and len(sub.data) >= 4:
                        current_ref.charge_int = unpack_i32(sub.data)
                    elif sub.sub_type == b"FLTV" and len(sub.data) >= 4:
                        current_ref.lock_level = unpack_f32(sub.data)
                    elif sub.sub_type == b"DODT" and len(sub.data) >= 24:
                        current_ref.dest_pos = (
                            struct.unpack_from("<f", sub.data, 0)[0],
                            struct.unpack_from("<f", sub.data, 4)[0],
                            struct.unpack_from("<f", sub.data, 8)[0],
                        )
                        current_ref.dest_rot = (
                            struct.unpack_from("<f", sub.data, 12)[0],
                            struct.unpack_from("<f", sub.data, 16)[0],
                            struct.unpack_from("<f", sub.data, 20)[0],
                        )
                    elif sub.sub_type == b"DNAM":
                        current_ref.dest_cell = decode_cstring(sub.data)
                    elif sub.sub_type == b"DELE":
                        current_ref.is_deleted = True
                    elif sub.sub_type == b"UNAM" and len(sub.data) >= 1:
                        current_ref.is_blocked = bool(sub.data[0])

            # Moved refs (appear after all regular refs or interspersed)
            if sub.sub_type == b"MVRF":
                mvr = MovedRef()
                if len(sub.data) >= 4:
                    mvr.ref_num = unpack_u32(sub.data)
                if i + 1 < len(subs) and subs[i + 1].sub_type == b"CNDT":
                    cndt = subs[i + 1].data
                    if len(cndt) >= 8:
                        mvr.cell_x = unpack_i32(cndt, 0)
                        mvr.cell_y = unpack_i32(cndt, 4)
                    i += 1
                obj.moved_refs.append(mvr)

            i += 1

        # Flush last ref
        if current_ref is not None:
            obj.refs.append(current_ref)

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_refid(sub_type: bytes, refid: RefId) -> None:
            data = encode_refid_to_subrecord(refid, format_version)
            out.extend(pack_subrec_header(sub_type, len(data)))
            out.extend(data)

        # Cell header
        name_data = encode_cstring(self.cell_name)
        out.extend(pack_subrec_header(b"NAME", len(name_data)))
        out.extend(name_data)

        data_block = (pack_u32(self.cell_flags)
                      + pack_i32(self.grid_x)
                      + pack_i32(self.grid_y))
        out.extend(pack_subrec_header(b"DATA", 12))
        out.extend(data_block)

        if not isinstance(self.region, EmptyRefId):
            add_refid(b"RGNN", self.region)

        if self.ref_num_counter:
            out.extend(pack_subrec_header(b"NAM0", 4))
            out.extend(pack_i32(self.ref_num_counter))

        if self.water_height is not None:
            out.extend(pack_subrec_header(b"WHGT", 4))
            out.extend(pack_f32(self.water_height))

        if self.ambient is not None:
            ambi = bytearray(16)
            struct.pack_into("<I", ambi, 0, self.ambient.ambient)
            struct.pack_into("<I", ambi, 4, self.ambient.sunlight)
            struct.pack_into("<I", ambi, 8, self.ambient.fog)
            struct.pack_into("<f", ambi, 12, self.ambient.fog_density)
            out.extend(pack_subrec_header(b"AMBI", 16))
            out.extend(ambi)

        if self.map_color is not None:
            out.extend(pack_subrec_header(b"NAM5", 4))
            out.extend(pack_i32(self.map_color))

        # References
        for ref in self.refs:
            out.extend(pack_subrec_header(b"FRMR", 4))
            out.extend(pack_u32(ref.ref_num))

            add_refid(b"NAME", ref.object_id)

            if ref.scale != 1.0:
                out.extend(pack_subrec_header(b"XSCL", 4))
                out.extend(pack_f32(ref.scale))

            if not ref.is_deleted:
                pos_data = bytearray(24)
                struct.pack_into("<f", pos_data, 0, ref.pos_x)
                struct.pack_into("<f", pos_data, 4, ref.pos_y)
                struct.pack_into("<f", pos_data, 8, ref.pos_z)
                struct.pack_into("<f", pos_data, 12, ref.rot_x)
                struct.pack_into("<f", pos_data, 16, ref.rot_y)
                struct.pack_into("<f", pos_data, 20, ref.rot_z)
                out.extend(pack_subrec_header(b"DATA", 24))
                out.extend(pos_data)

            if not isinstance(ref.soul, EmptyRefId):
                add_refid(b"XSOL", ref.soul)
            if not isinstance(ref.owner, EmptyRefId):
                add_refid(b"XOWN", ref.owner)
            if ref.owner_rank >= 0:
                out.extend(pack_subrec_header(b"XRNK", 4))
                out.extend(pack_i32(ref.owner_rank))
            if not isinstance(ref.owner_global, EmptyRefId):
                add_refid(b"XGLB", ref.owner_global)
            if not isinstance(ref.key_id, EmptyRefId):
                add_refid(b"KNAM", ref.key_id)
            if not isinstance(ref.trap_id, EmptyRefId):
                add_refid(b"TNAM", ref.trap_id)
            if ref.enchant_charge >= 0:
                out.extend(pack_subrec_header(b"XCHG", 4))
                out.extend(pack_f32(ref.enchant_charge))
            if ref.charge_int >= 0:
                out.extend(pack_subrec_header(b"INTV", 4))
                out.extend(pack_i32(ref.charge_int))
            if ref.lock_level:
                out.extend(pack_subrec_header(b"FLTV", 4))
                out.extend(pack_f32(ref.lock_level))
            if ref.dest_pos is not None:
                dodt = bytearray(24)
                for k, v in enumerate((*ref.dest_pos, *(ref.dest_rot or (0., 0., 0.)))):
                    struct.pack_into("<f", dodt, k * 4, v)
                out.extend(pack_subrec_header(b"DODT", 24))
                out.extend(dodt)
                if ref.dest_cell:
                    dc = encode_cstring(ref.dest_cell)
                    out.extend(pack_subrec_header(b"DNAM", len(dc)))
                    out.extend(dc)
            if ref.is_deleted:
                out.extend(pack_subrec_header(b"DELE", 4))
                out.extend(b"\x00\x00\x00\x00")
            if ref.is_blocked:
                out.extend(pack_subrec_header(b"UNAM", 1))
                out.extend(b"\x01")

        # Moved refs
        for mvr in self.moved_refs:
            out.extend(pack_subrec_header(b"MVRF", 4))
            out.extend(pack_u32(mvr.ref_num))
            out.extend(pack_subrec_header(b"CNDT", 8))
            out.extend(pack_i32(mvr.cell_x))
            out.extend(pack_i32(mvr.cell_y))

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        from omwtools.io.refid import refid_to_db_text

        def rid(r: RefId) -> str:
            return refid_to_db_text(r)

        result: dict[str, Any] = {
            "rec_type": "CELL",
            "cell_name": self.cell_name,
            "cell_flags": self.cell_flags,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "region": rid(self.region),
            "ref_num_counter": self.ref_num_counter,
            "water_height": self.water_height,
            "flags": self.flags,
        }
        if self.ambient:
            result["ambient"] = {
                "ambient": self.ambient.ambient,
                "sunlight": self.ambient.sunlight,
                "fog": self.ambient.fog,
                "fog_density": self.ambient.fog_density,
            }
        if self.map_color is not None:
            result["map_color"] = self.map_color
        result["refs"] = [
            {
                "ref_num": r.ref_num,
                "object_id": rid(r.object_id),
                "scale": r.scale,
                "pos": [r.pos_x, r.pos_y, r.pos_z],
                "rot": [r.rot_x, r.rot_y, r.rot_z],
                "is_deleted": r.is_deleted,
                "is_blocked": r.is_blocked,
                "soul": rid(r.soul),
                "owner": rid(r.owner),
                "owner_rank": r.owner_rank,
                "owner_global": rid(r.owner_global),
                "key_id": rid(r.key_id),
                "trap_id": rid(r.trap_id),
                "enchant_charge": r.enchant_charge,
                "charge_int": r.charge_int,
                "lock_level": r.lock_level,
                "dest_pos": list(r.dest_pos) if r.dest_pos is not None else None,
                "dest_rot": list(r.dest_rot) if r.dest_rot is not None else None,
                "dest_cell": r.dest_cell,
            }
            for r in self.refs
        ]
        return result

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Cell":
        from omwtools.io.refid import refid_from_db_text

        obj = cls()
        obj.cell_name = d.get("cell_name", "")
        obj.cell_flags = d.get("cell_flags", 0)
        obj.grid_x = d.get("grid_x", 0)
        obj.grid_y = d.get("grid_y", 0)
        obj.region = refid_from_db_text(d.get("region", ""))
        obj.ref_num_counter = d.get("ref_num_counter", 0)
        obj.water_height = d.get("water_height")
        obj.flags = d.get("flags", 0)

        ambi = d.get("ambient")
        if ambi:
            obj.ambient = CellAmbient(**ambi)

        obj.map_color = d.get("map_color")
        obj.refs = []
        for r in d.get("refs", []):
            ref = CellRef()
            ref.ref_num   = r.get("ref_num", 0)
            ref.object_id = refid_from_db_text(r.get("object_id", ""))
            ref.scale     = r.get("scale", 1.0)
            pos = r.get("pos", [0, 0, 0])
            rot = r.get("rot", [0, 0, 0])
            ref.pos_x, ref.pos_y, ref.pos_z = pos
            ref.rot_x, ref.rot_y, ref.rot_z = rot
            ref.is_deleted    = r.get("is_deleted", False)
            ref.is_blocked    = r.get("is_blocked", False)
            ref.soul          = refid_from_db_text(r.get("soul", ""))
            ref.owner         = refid_from_db_text(r.get("owner", ""))
            ref.owner_rank    = r.get("owner_rank", -1)
            ref.owner_global  = refid_from_db_text(r.get("owner_global", ""))
            ref.key_id        = refid_from_db_text(r.get("key_id", ""))
            ref.trap_id       = refid_from_db_text(r.get("trap_id", ""))
            ref.enchant_charge = r.get("enchant_charge", -1.0)
            ref.charge_int    = r.get("charge_int", -1)
            ref.lock_level    = r.get("lock_level", 0.0)
            dp = r.get("dest_pos")
            dr = r.get("dest_rot")
            if dp is not None:
                ref.dest_pos = tuple(dp)
            if dr is not None:
                ref.dest_rot = tuple(dr)
            ref.dest_cell = r.get("dest_cell", "")
            obj.refs.append(ref)

        return obj
