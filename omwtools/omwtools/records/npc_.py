"""NPC_ record — Non-Player Character.

This is the flagship record implementation, covering all subrecord fields.

Key subrecords (from components/esm3/loadnpc.hpp):
  NAME  → record_id (RefId)
  MODL  → mesh path
  FNAM  → display name
  RNAM  → race RefId
  CNAM  → class RefId
  ANAM  → faction RefId
  BNAM  → head mesh RefId
  KNAM  → hair mesh RefId
  SCRI  → script RefId
  NPDT  → NPC data (52 bytes = full, 12 bytes = autocalc)
  FLAG  → NPC flags (uint32)
  NPCO  → inventory item (int32 count + RefId)
  NPCS  → spell RefId (32-byte fixed string)
  AIDT  → AI data (12 bytes)
  AI_W  → wander AI package
  AI_T  → travel AI package
  AI_F  → follow AI package
  AI_E  → escort AI package
  AI_A  → activate AI package
  DODT  → destination position (24 bytes)
  DNAM  → destination cell name
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from omwtools.io.codec import (
    decode_cstring, decode_fixed_string, decode_string,
    encode_cstring, encode_fixed_string,
    unpack_i16, unpack_i32, unpack_u8, unpack_u16, unpack_u32,
    pack_i32, pack_u8, pack_u16, pack_u32,
    pack_subrec_header,
)
from omwtools.io.refid import (
    RefId, EmptyRefId, StringRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord,
    refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord

# NPDT sizes
NPDT_FULL_SIZE    = 52
NPDT_AUTOCALC_SIZE = 12

# NPC flags
NPC_FLAG_FEMALE   = 0x0001
NPC_FLAG_ESSENTIAL = 0x0002
NPC_FLAG_RESPAWN  = 0x0004
NPC_FLAG_AUTOCALC = 0x0010
NPC_FLAG_SKELETON_BLOOD = 0x0400
NPC_FLAG_METAL_BLOOD    = 0x0800


@dataclass
class NPDTFull:
    """52-byte NPC data block for manually-set stats."""
    level: int = 0
    attributes: list[int] = field(default_factory=lambda: [0] * 8)  # Strength..Luck
    skills: list[int] = field(default_factory=lambda: [0] * 27)
    health: int = 0
    mana: int = 0
    fatigue: int = 0
    disposition: int = 0
    reputation: int = 0
    rank: int = 0
    gold: int = 0


@dataclass
class NPDTAutocalc:
    """12-byte NPC data block for autocalculated stats."""
    level: int = 0
    disposition: int = 0
    reputation: int = 0
    rank: int = 0
    gold: int = 0


@dataclass
class ContItem:
    """One inventory slot: count + item RefId."""
    count: int = 0
    item_id: RefId = field(default_factory=EmptyRefId)


@dataclass
class AIData:
    """12-byte AI configuration."""
    hello: int = 0
    fight: int = 0
    flee: int = 0
    alarm: int = 0
    services: int = 0  # bitfield


@dataclass
class AIPackage:
    """Raw AI package blob (AI_W / AI_T / AI_F / AI_E / AI_A)."""
    package_type: bytes = b"AI_W"
    raw_data: bytes = b""


@dataclass
class TransportDest:
    """DODT + optional DNAM — a travel/transport destination."""
    pos_x: float = 0.0
    pos_y: float = 0.0
    pos_z: float = 0.0
    rot_x: float = 0.0
    rot_y: float = 0.0
    rot_z: float = 0.0
    cell_name: str = ""


@dataclass
class NPC(BaseRecord):
    """NPC_ record — fully decoded NPC."""

    REC_TYPE = b"NPC_"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    name: str = ""
    race: RefId = field(default_factory=EmptyRefId)
    class_id: RefId = field(default_factory=EmptyRefId)
    faction: RefId = field(default_factory=EmptyRefId)
    head: RefId = field(default_factory=EmptyRefId)
    hair: RefId = field(default_factory=EmptyRefId)
    script: RefId = field(default_factory=EmptyRefId)
    npc_flags: int = 0
    npdt_full: Optional[NPDTFull] = None
    npdt_autocalc: Optional[NPDTAutocalc] = None
    inventory: list[ContItem] = field(default_factory=list)
    spells: list[RefId] = field(default_factory=list)
    ai_data: Optional[AIData] = None
    ai_packages: list[AIPackage] = field(default_factory=list)
    transport: list[TransportDest] = field(default_factory=list)

    # ------------------------------------------------------------------ #

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "NPC":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        def get_refid(sub_type: bytes) -> RefId:
            sub = raw.get_subrecord(sub_type)
            if sub is None:
                return EmptyRefId()
            return decode_refid_from_subrecord(sub.data, format_version)

        obj.record_id = get_refid(b"NAME")

        modl = raw.get_subrecord(b"MODL")
        if modl:
            obj.mesh = decode_cstring(modl.data)

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        obj.race    = get_refid(b"RNAM")
        obj.class_id = get_refid(b"CNAM")
        obj.faction  = get_refid(b"ANAM")
        obj.head     = get_refid(b"BNAM")
        obj.hair     = get_refid(b"KNAM")
        obj.script   = get_refid(b"SCRI")

        # NPDT
        npdt = raw.get_subrecord(b"NPDT")
        if npdt:
            if len(npdt.data) == NPDT_FULL_SIZE:
                d = npdt.data
                full = NPDTFull()
                full.level = unpack_i16(d, 0)
                full.attributes = list(d[2:10])
                full.skills = list(d[10:37])
                # byte 37 unused (reputation? same as npdt12)
                full.health   = unpack_i16(d, 38)
                full.mana     = unpack_i16(d, 40)
                full.fatigue  = unpack_i16(d, 42)
                full.disposition = d[44]
                full.reputation  = unpack_i16(d, 45) if len(d) > 45 else 0
                full.rank        = d[47] if len(d) > 47 else 0
                full.gold        = unpack_i32(d, 48) if len(d) >= 52 else 0
                obj.npdt_full = full
            elif len(npdt.data) >= NPDT_AUTOCALC_SIZE:
                d = npdt.data
                ac = NPDTAutocalc()
                ac.level       = unpack_i16(d, 0)
                ac.disposition = d[2]
                ac.reputation  = d[3]
                ac.rank        = d[4]
                # bytes 5-7 padding
                ac.gold        = unpack_i32(d, 8)
                obj.npdt_autocalc = ac

        # FLAG
        flag_sub = raw.get_subrecord(b"FLAG")
        if flag_sub and len(flag_sub.data) >= 4:
            obj.npc_flags = unpack_u32(flag_sub.data)

        # NPCO — inventory
        for sub in raw.get_subrecords(b"NPCO"):
            if len(sub.data) >= 4:
                count = unpack_i32(sub.data)
                item_id = decode_refid_from_subrecord(sub.data[4:], format_version)
                obj.inventory.append(ContItem(count, item_id))

        # NPCS — spells (32-byte fixed string)
        for sub in raw.get_subrecords(b"NPCS"):
            spell_id = decode_refid_from_subrecord(sub.data, format_version)
            obj.spells.append(spell_id)

        # AIDT
        aidt = raw.get_subrecord(b"AIDT")
        if aidt and len(aidt.data) >= 12:
            d = aidt.data
            obj.ai_data = AIData(
                hello    = unpack_u16(d, 0),
                fight    = d[2],
                flee     = d[3],
                alarm    = d[4],
                services = unpack_i32(d, 8),
            )

        # AI packages (raw blobs)
        for sub in raw.subrecords:
            if sub.sub_type in (b"AI_W", b"AI_T", b"AI_F", b"AI_E", b"AI_A"):
                obj.ai_packages.append(AIPackage(sub.sub_type, sub.data))

        # DODT/DNAM — transport destinations
        i = 0
        subs = raw.subrecords
        while i < len(subs):
            if subs[i].sub_type == b"DODT" and len(subs[i].data) >= 24:
                d = subs[i].data
                dest = TransportDest(
                    pos_x=struct.unpack_from("<f", d, 0)[0],
                    pos_y=struct.unpack_from("<f", d, 4)[0],
                    pos_z=struct.unpack_from("<f", d, 8)[0],
                    rot_x=struct.unpack_from("<f", d, 12)[0],
                    rot_y=struct.unpack_from("<f", d, 16)[0],
                    rot_z=struct.unpack_from("<f", d, 20)[0],
                )
                if i + 1 < len(subs) and subs[i + 1].sub_type == b"DNAM":
                    dest.cell_name = decode_cstring(subs[i + 1].data)
                    i += 1
                obj.transport.append(dest)
            i += 1

        return obj

    # ------------------------------------------------------------------ #

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_refid(sub_type: bytes, refid: RefId) -> None:
            data = encode_refid_to_subrecord(refid, format_version)
            out.extend(pack_subrec_header(sub_type, len(data)))
            out.extend(data)

        def add_cstr(sub_type: bytes, s: str) -> None:
            data = encode_cstring(s)
            out.extend(pack_subrec_header(sub_type, len(data)))
            out.extend(data)

        add_refid(b"NAME", self.record_id)
        if self.mesh:
            add_cstr(b"MODL", self.mesh)
        if self.name:
            add_cstr(b"FNAM", self.name)
        add_refid(b"RNAM", self.race)
        add_refid(b"CNAM", self.class_id)
        if not isinstance(self.faction, EmptyRefId):
            add_refid(b"ANAM", self.faction)
        if not isinstance(self.head, EmptyRefId):
            add_refid(b"BNAM", self.head)
        if not isinstance(self.hair, EmptyRefId):
            add_refid(b"KNAM", self.hair)
        if not isinstance(self.script, EmptyRefId):
            add_refid(b"SCRI", self.script)

        # NPDT
        if self.npdt_full is not None:
            f = self.npdt_full
            buf = bytearray(NPDT_FULL_SIZE)
            struct.pack_into("<h", buf, 0, f.level)
            attrs = (f.attributes + [0] * 8)[:8]
            buf[2:10] = bytes(attrs)
            skills = (f.skills + [0] * 27)[:27]
            buf[10:37] = bytes(skills)
            # byte 37 = 0 (padding/unknown)
            struct.pack_into("<h", buf, 38, f.health)
            struct.pack_into("<h", buf, 40, f.mana)
            struct.pack_into("<h", buf, 42, f.fatigue)
            buf[44] = f.disposition & 0xFF
            buf[45] = f.reputation & 0xFF
            buf[46] = 0  # pad
            buf[47] = f.rank & 0xFF
            struct.pack_into("<i", buf, 48, f.gold)
            out.extend(pack_subrec_header(b"NPDT", NPDT_FULL_SIZE))
            out.extend(buf)
        elif self.npdt_autocalc is not None:
            ac = self.npdt_autocalc
            buf = bytearray(NPDT_AUTOCALC_SIZE)
            struct.pack_into("<h", buf, 0, ac.level)
            buf[2] = ac.disposition & 0xFF
            buf[3] = ac.reputation & 0xFF
            buf[4] = ac.rank & 0xFF
            # bytes 5-7: padding
            struct.pack_into("<i", buf, 8, ac.gold)
            out.extend(pack_subrec_header(b"NPDT", NPDT_AUTOCALC_SIZE))
            out.extend(buf)

        # FLAG
        out.extend(pack_subrec_header(b"FLAG", 4))
        out.extend(pack_u32(self.npc_flags))

        # NPCO — 32-byte fixed string in old format, variable RefId in new format
        for item in self.inventory:
            if format_version <= 23:
                id_name = item.item_id.value if isinstance(item.item_id, StringRefId) else ""
                id_data = encode_fixed_string(id_name, 32)
            else:
                id_data = encode_refid_to_subrecord(item.item_id, format_version)
            item_data = pack_i32(item.count) + id_data
            out.extend(pack_subrec_header(b"NPCO", len(item_data)))
            out.extend(item_data)

        # NPCS — 32-byte fixed string in old format, variable RefId in new format
        for spell in self.spells:
            if format_version <= 23:
                spell_name = spell.value if isinstance(spell, StringRefId) else ""
                spell_data = encode_fixed_string(spell_name, 32)
            else:
                spell_data = encode_refid_to_subrecord(spell, format_version)
            out.extend(pack_subrec_header(b"NPCS", len(spell_data)))
            out.extend(spell_data)

        # AIDT
        if self.ai_data is not None:
            ai = self.ai_data
            buf = bytearray(12)
            struct.pack_into("<H", buf, 0, ai.hello)
            buf[2] = ai.fight & 0xFF
            buf[3] = ai.flee & 0xFF
            buf[4] = ai.alarm & 0xFF
            # bytes 5-7: padding
            struct.pack_into("<i", buf, 8, ai.services)
            out.extend(pack_subrec_header(b"AIDT", 12))
            out.extend(buf)

        # AI packages
        for pkg in self.ai_packages:
            out.extend(pack_subrec_header(pkg.package_type, len(pkg.raw_data)))
            out.extend(pkg.raw_data)

        # DODT/DNAM
        for dest in self.transport:
            dodt = bytearray(24)
            struct.pack_into("<f", dodt, 0, dest.pos_x)
            struct.pack_into("<f", dodt, 4, dest.pos_y)
            struct.pack_into("<f", dodt, 8, dest.pos_z)
            struct.pack_into("<f", dodt, 12, dest.rot_x)
            struct.pack_into("<f", dodt, 16, dest.rot_y)
            struct.pack_into("<f", dodt, 20, dest.rot_z)
            out.extend(pack_subrec_header(b"DODT", 24))
            out.extend(dodt)
            if dest.cell_name:
                cell_data = encode_cstring(dest.cell_name)
                out.extend(pack_subrec_header(b"DNAM", len(cell_data)))
                out.extend(cell_data)

        return bytes(out)

    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        from omwtools.io.refid import refid_to_db_text

        def rid(r: RefId) -> str:
            return refid_to_db_text(r)

        d: dict[str, Any] = {
            "rec_type": "NPC_",
            "record_id": rid(self.record_id),
            "mesh": self.mesh,
            "name": self.name,
            "race": rid(self.race),
            "class_id": rid(self.class_id),
            "faction": rid(self.faction),
            "head": rid(self.head),
            "hair": rid(self.hair),
            "script": rid(self.script),
            "npc_flags": self.npc_flags,
            "flags": self.flags,
        }
        if self.npdt_full:
            f = self.npdt_full
            d["npdt_full"] = {
                "level": f.level,
                "attributes": f.attributes,
                "skills": f.skills,
                "health": f.health,
                "mana": f.mana,
                "fatigue": f.fatigue,
                "disposition": f.disposition,
                "reputation": f.reputation,
                "rank": f.rank,
                "gold": f.gold,
            }
        if self.npdt_autocalc:
            ac = self.npdt_autocalc
            d["npdt_autocalc"] = {
                "level": ac.level,
                "disposition": ac.disposition,
                "reputation": ac.reputation,
                "rank": ac.rank,
                "gold": ac.gold,
            }
        d["inventory"] = [
            {"count": it.count, "item_id": rid(it.item_id)}
            for it in self.inventory
        ]
        d["spells"] = [rid(s) for s in self.spells]
        if self.ai_data:
            ai = self.ai_data
            d["ai_data"] = {
                "hello": ai.hello,
                "fight": ai.fight,
                "flee": ai.flee,
                "alarm": ai.alarm,
                "services": ai.services,
            }
        d["ai_packages"] = [
            {"type": p.package_type.decode("ascii", errors="replace"),
             "raw_hex": p.raw_data.hex()}
            for p in self.ai_packages
        ]
        d["transport"] = [
            {"pos_x": t.pos_x, "pos_y": t.pos_y, "pos_z": t.pos_z,
             "rot_x": t.rot_x, "rot_y": t.rot_y, "rot_z": t.rot_z,
             "cell_name": t.cell_name}
            for t in self.transport
        ]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "NPC":
        from omwtools.io.refid import refid_from_db_text

        obj = cls()
        obj.record_id = refid_from_db_text(d.get("record_id", ""))
        obj.mesh = d.get("mesh", "")
        obj.name = d.get("name", "")
        obj.race     = refid_from_db_text(d.get("race", ""))
        obj.class_id = refid_from_db_text(d.get("class_id", ""))
        obj.faction  = refid_from_db_text(d.get("faction", ""))
        obj.head     = refid_from_db_text(d.get("head", ""))
        obj.hair     = refid_from_db_text(d.get("hair", ""))
        obj.script   = refid_from_db_text(d.get("script", ""))
        obj.npc_flags = d.get("npc_flags", 0)
        obj.flags     = d.get("flags", 0)

        if "npdt_full" in d:
            f = d["npdt_full"]
            obj.npdt_full = NPDTFull(
                level=f["level"],
                attributes=f["attributes"],
                skills=f["skills"],
                health=f["health"],
                mana=f["mana"],
                fatigue=f["fatigue"],
                disposition=f["disposition"],
                reputation=f["reputation"],
                rank=f["rank"],
                gold=f["gold"],
            )
        elif "npdt_autocalc" in d:
            ac = d["npdt_autocalc"]
            obj.npdt_autocalc = NPDTAutocalc(
                level=ac["level"],
                disposition=ac["disposition"],
                reputation=ac["reputation"],
                rank=ac["rank"],
                gold=ac["gold"],
            )

        obj.inventory = [
            ContItem(it["count"], refid_from_db_text(it["item_id"]))
            for it in d.get("inventory", [])
        ]
        obj.spells = [refid_from_db_text(s) for s in d.get("spells", [])]

        if "ai_data" in d:
            ai = d["ai_data"]
            obj.ai_data = AIData(
                hello=ai["hello"],
                fight=ai["fight"],
                flee=ai["flee"],
                alarm=ai["alarm"],
                services=ai["services"],
            )
        obj.ai_packages = [
            AIPackage(p["type"].encode("ascii")[:4], bytes.fromhex(p["raw_hex"]))
            for p in d.get("ai_packages", [])
        ]
        obj.transport = [
            TransportDest(**t)
            for t in d.get("transport", [])
        ]
        return obj
