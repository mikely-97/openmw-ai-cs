"""LUAL record — LuaScriptsCfg binary record.

Found in omwgame/omwaddon files; stores Lua script configuration in binary form.
This is the ESM-embedded counterpart to .omwscripts text files.

Subrecords per script entry (from components/esm/luascripts.cpp):
  LUAS  : VFS path to .lua file (NUL-terminated string)
  LUAF  : uint32 flags + repeated uint32 ESM::RecNameInts (attached types)
  LUAD  : (optional) binary initialization data (Lua table)
  LUAR  : (repeating) per-record attach — byte attach + RefId + optional LUAD
  LUAI  : (repeating) per-ref attach — byte attach + uint32 refnum_index +
                                        int32 refnum_content_file + optional LUAD

Flag bits (ESM::LuaScriptCfg):
  sGlobal = 1   sCustom = 2   sPlayer = 4   sMerge = 8   sMenu = 16
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import (
    decode_cstring, encode_cstring,
    unpack_u32, unpack_i32, unpack_u8,
    pack_u32, pack_i32, pack_u8,
    pack_subrec_header,
)
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord,
)
from omwtools.records.base import BaseRecord, RawRecord

# LuaScriptCfg flag bits
LUAF_GLOBAL = 1
LUAF_CUSTOM = 2
LUAF_PLAYER = 4
LUAF_MERGE  = 8
LUAF_MENU   = 16


@dataclass
class LuaPerRecordCfg:
    attach: bool = True
    record_id: RefId = field(default_factory=EmptyRefId)
    init_data: bytes = b""


@dataclass
class LuaPerRefCfg:
    attach: bool = True
    refnum_index: int = 0
    refnum_content_file: int = 0
    init_data: bytes = b""


@dataclass
class LuaScriptEntry:
    script_path: str = ""
    flags: int = 0
    types: list[int] = field(default_factory=list)  # ESM::RecNameInts values
    init_data: bytes = b""
    per_record: list[LuaPerRecordCfg] = field(default_factory=list)
    per_ref: list[LuaPerRefCfg] = field(default_factory=list)


@dataclass
class LUALRecord(BaseRecord):
    """LUAL record — binary Lua scripts configuration."""

    REC_TYPE = b"LUAL"

    flags: int = 0
    unknown: int = 0
    scripts: list[LuaScriptEntry] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "LUALRecord":
        obj = cls(flags=raw.flags, unknown=raw.unknown)
        subs = raw.subrecords

        current: LuaScriptEntry | None = None
        i = 0

        while i < len(subs):
            sub = subs[i]

            if sub.sub_type == b"LUAS":
                current = LuaScriptEntry(script_path=decode_cstring(sub.data))
                obj.scripts.append(current)

            elif sub.sub_type == b"LUAF" and current is not None:
                if len(sub.data) >= 4:
                    current.flags = unpack_u32(sub.data, 0)
                    n_types = (len(sub.data) - 4) // 4
                    for k in range(n_types):
                        current.types.append(unpack_u32(sub.data, 4 + k * 4))

            elif sub.sub_type == b"LUAD" and current is not None:
                # Initialization data follows the most recent LUAS, LUAR or LUAI
                # We attach it to the last per_ref or per_record if one is pending
                if current.per_ref:
                    current.per_ref[-1].init_data = sub.data
                elif current.per_record:
                    current.per_record[-1].init_data = sub.data
                else:
                    current.init_data = sub.data

            elif sub.sub_type == b"LUAR" and current is not None:
                if len(sub.data) >= 1:
                    attach = bool(sub.data[0])
                    rid = decode_refid_from_subrecord(sub.data[1:], format_version)
                    current.per_record.append(
                        LuaPerRecordCfg(attach=attach, record_id=rid)
                    )

            elif sub.sub_type == b"LUAI" and current is not None:
                if len(sub.data) >= 9:
                    attach = bool(sub.data[0])
                    rnum_idx  = unpack_u32(sub.data, 1)
                    rnum_cf   = unpack_i32(sub.data, 5)
                    current.per_ref.append(
                        LuaPerRefCfg(attach=attach,
                                     refnum_index=rnum_idx,
                                     refnum_content_file=rnum_cf)
                    )

            i += 1

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        for script in self.scripts:
            luas_data = encode_cstring(script.script_path)
            out.extend(pack_subrec_header(b"LUAS", len(luas_data)))
            out.extend(luas_data)

            # LUAF: flags (uint32) + types (uint32 each)
            luaf_data = pack_u32(script.flags)
            for t in script.types:
                luaf_data += pack_u32(t)
            out.extend(pack_subrec_header(b"LUAF", len(luaf_data)))
            out.extend(luaf_data)

            # Initialization data
            if script.init_data:
                out.extend(pack_subrec_header(b"LUAD", len(script.init_data)))
                out.extend(script.init_data)

            # Per-record configurations
            for rec_cfg in script.per_record:
                rid_data = encode_refid_to_subrecord(rec_cfg.record_id, format_version)
                luar_data = bytes([1 if rec_cfg.attach else 0]) + rid_data
                out.extend(pack_subrec_header(b"LUAR", len(luar_data)))
                out.extend(luar_data)
                if rec_cfg.init_data:
                    out.extend(pack_subrec_header(b"LUAD", len(rec_cfg.init_data)))
                    out.extend(rec_cfg.init_data)

            # Per-ref configurations
            for ref_cfg in script.per_ref:
                luai_data = (
                    bytes([1 if ref_cfg.attach else 0])
                    + pack_u32(ref_cfg.refnum_index)
                    + pack_i32(ref_cfg.refnum_content_file)
                )
                out.extend(pack_subrec_header(b"LUAI", len(luai_data)))
                out.extend(luai_data)
                if ref_cfg.init_data:
                    out.extend(pack_subrec_header(b"LUAD", len(ref_cfg.init_data)))
                    out.extend(ref_cfg.init_data)

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        from omwtools.io.refid import refid_to_db_text

        return {
            "rec_type": "LUAL",
            "flags": self.flags,
            "scripts": [
                {
                    "script_path": s.script_path,
                    "flags": s.flags,
                    "types": s.types,
                    "init_data_hex": s.init_data.hex(),
                    "per_record": [
                        {
                            "attach": r.attach,
                            "record_id": refid_to_db_text(r.record_id),
                            "init_data_hex": r.init_data.hex(),
                        }
                        for r in s.per_record
                    ],
                    "per_ref": [
                        {
                            "attach": r.attach,
                            "refnum_index": r.refnum_index,
                            "refnum_content_file": r.refnum_content_file,
                            "init_data_hex": r.init_data.hex(),
                        }
                        for r in s.per_ref
                    ],
                }
                for s in self.scripts
            ],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LUALRecord":
        from omwtools.io.refid import refid_from_db_text

        obj = cls(flags=d.get("flags", 0))
        for s in d.get("scripts", []):
            entry = LuaScriptEntry(
                script_path=s.get("script_path", ""),
                flags=s.get("flags", 0),
                types=s.get("types", []),
                init_data=bytes.fromhex(s.get("init_data_hex", "")),
            )
            for r in s.get("per_record", []):
                entry.per_record.append(LuaPerRecordCfg(
                    attach=r.get("attach", True),
                    record_id=refid_from_db_text(r.get("record_id", "")),
                    init_data=bytes.fromhex(r.get("init_data_hex", "")),
                ))
            for r in s.get("per_ref", []):
                entry.per_ref.append(LuaPerRefCfg(
                    attach=r.get("attach", True),
                    refnum_index=r.get("refnum_index", 0),
                    refnum_content_file=r.get("refnum_content_file", 0),
                    init_data=bytes.fromhex(r.get("init_data_hex", "")),
                ))
            obj.scripts.append(entry)
        return obj
