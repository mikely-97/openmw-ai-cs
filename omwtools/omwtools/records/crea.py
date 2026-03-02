"""CREA — Creature record.

Subrecords:
  NAME  → record_id (RefId)
  MODL  → mesh path
  CNAM  → sound template RefId (creature whose sounds to use)
  FNAM  → display name
  SCRI  → script RefId
  NPDT  → creature stats (96 bytes, see NPDTstruct below)
  FLAG  → creature flags (int32)
  XSCL  → scale (float, optional)
  NPCO  → inventory item: int32 count + RefId (repeating)
  NPCS  → spell: 32-byte fixed string (repeating)
  AIDT  → AI data (12 bytes: uint16 hello + uint8×3 fight/flee/alarm + 1 pad + int32 services)
  AI_W  → wander AI package (blob)
  AI_T  → travel AI package (blob)
  AI_F  → follow AI package (blob)
  AI_E  → escort AI package (blob)
  AI_A  → activate AI package (blob)
  DODT  → transport destination position (24 bytes: float×6)
  DNAM  → transport destination cell (C-string)

NPDTstruct (96 bytes, little-endian):
  int32 type     (0=Creature,1=Daedra,2=Undead,3=Humanoid)
  int32 level
  int32 str/int/wil/agi/spd/end/per/luc  (8 attributes)
  int32 health + int32 mana + int32 fatigue
  int32 soul
  int32 combat + int32 magic + int32 stealth
  int32 attack[6]   (3 min/max pairs)
  int32 gold
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import (
    decode_cstring, encode_cstring, encode_fixed_string, decode_string,
    pack_subrec_header, pack_i32, pack_u16, pack_u8,
    unpack_i32, unpack_u16,
)
from omwtools.io.refid import (
    RefId, EmptyRefId, StringRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord

# NPDT layout — 24 int32 values = 96 bytes
NPDT_FMT = "<" + "i" * 24
NPDT_SIZE = struct.calcsize(NPDT_FMT)  # 96

# AIDT: uint16 hello + uint8 fight + uint8 flee + uint8 alarm + 3 pad + int32 services
AIDT_FMT = "<HBBBxxxI"
AIDT_SIZE = struct.calcsize(AIDT_FMT)  # 12

# NPCS: 32-byte fixed string per spell
NPCS_SIZE = 32

# DODT: 6 floats (pos xyz + rot xyz)
DODT_FMT = "<ffffff"
DODT_SIZE = struct.calcsize(DODT_FMT)  # 24

# Creature FLAG bits
CREA_BIPED        = 0x0001
CREA_RESPAWN      = 0x0002
CREA_WEAPON_SHIELD = 0x0004
CREA_NONE         = 0x0008
CREA_SWIMS        = 0x0010
CREA_FLIES        = 0x0020
CREA_WALKS        = 0x0040
CREA_ESSENTIAL    = 0x0080
CREA_SKELETON_BLOOD = 0x0400
CREA_METAL_BLOOD  = 0x0800


@dataclass
class TransportDest:
    pos_x: float = 0.0
    pos_y: float = 0.0
    pos_z: float = 0.0
    rot_x: float = 0.0
    rot_y: float = 0.0
    rot_z: float = 0.0
    cell_name: str = ""


@dataclass
class ContItem:
    count: int = 0
    item: RefId = field(default_factory=EmptyRefId)


@dataclass
class AIPackage:
    package_type: str = ""
    raw_data: bytes = b""


@dataclass
class Creature(BaseRecord):
    """CREA record — creature."""

    REC_TYPE = b"CREA"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    mesh: str = ""
    sound_template: RefId = field(default_factory=EmptyRefId)
    name: str = ""
    script: RefId = field(default_factory=EmptyRefId)
    # NPDT fields
    crea_type: int = 0
    level: int = 1
    strength: int = 0
    intelligence: int = 0
    willpower: int = 0
    agility: int = 0
    speed: int = 0
    endurance: int = 0
    personality: int = 0
    luck: int = 0
    health: int = 0
    mana: int = 0
    fatigue: int = 0
    soul: int = 0
    combat: int = 0
    magic: int = 0
    stealth: int = 0
    attack1_min: int = 0
    attack1_max: int = 0
    attack2_min: int = 0
    attack2_max: int = 0
    attack3_min: int = 0
    attack3_max: int = 0
    gold: int = 0
    # Other subrecords
    crea_flags: int = 0
    scale: float = 1.0
    inventory: list[ContItem] = field(default_factory=list)
    spells: list[RefId] = field(default_factory=list)
    # AI
    ai_hello: int = 0
    ai_fight: int = 0
    ai_flee: int = 0
    ai_alarm: int = 0
    ai_services: int = 0
    ai_packages: list[AIPackage] = field(default_factory=list)
    transport: list[TransportDest] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Creature":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        def get_refid(tag: bytes) -> RefId:
            sub = raw.get_subrecord(tag)
            return decode_refid_from_subrecord(sub.data, format_version) if sub else EmptyRefId()

        obj.record_id = get_refid(b"NAME")

        modl = raw.get_subrecord(b"MODL")
        if modl:
            obj.mesh = decode_cstring(modl.data)

        obj.sound_template = get_refid(b"CNAM")

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        obj.script = get_refid(b"SCRI")

        npdt = raw.get_subrecord(b"NPDT")
        if npdt and len(npdt.data) >= NPDT_SIZE:
            v = struct.unpack_from(NPDT_FMT, npdt.data)
            (obj.crea_type, obj.level,
             obj.strength, obj.intelligence, obj.willpower, obj.agility,
             obj.speed, obj.endurance, obj.personality, obj.luck,
             obj.health, obj.mana, obj.fatigue,
             obj.soul,
             obj.combat, obj.magic, obj.stealth,
             obj.attack1_min, obj.attack1_max,
             obj.attack2_min, obj.attack2_max,
             obj.attack3_min, obj.attack3_max,
             obj.gold) = v

        flag_sub = raw.get_subrecord(b"FLAG")
        if flag_sub and len(flag_sub.data) >= 4:
            obj.crea_flags = unpack_i32(flag_sub.data)

        xscl = raw.get_subrecord(b"XSCL")
        if xscl and len(xscl.data) >= 4:
            obj.scale = struct.unpack_from("<f", xscl.data)[0]

        # Inventory: NPCO = int32 count + RefId
        for sub in raw.get_subrecords(b"NPCO"):
            if len(sub.data) >= 4:
                count = unpack_i32(sub.data)
                item = decode_refid_from_subrecord(sub.data[4:], format_version)
                obj.inventory.append(ContItem(count, item))

        # Spells: NPCS = 32-byte fixed string
        for sub in raw.get_subrecords(b"NPCS"):
            spell = decode_refid_from_subrecord(sub.data[:NPCS_SIZE], format_version)
            obj.spells.append(spell)

        # AI data
        aidt = raw.get_subrecord(b"AIDT")
        if aidt and len(aidt.data) >= AIDT_SIZE:
            v = struct.unpack_from(AIDT_FMT, aidt.data)
            obj.ai_hello, obj.ai_fight, obj.ai_flee, obj.ai_alarm, obj.ai_services = v

        # AI packages
        _AI_TAGS = {b"AI_W", b"AI_T", b"AI_F", b"AI_E", b"AI_A"}
        for sub in raw.subrecords:
            if sub.sub_type in _AI_TAGS:
                obj.ai_packages.append(
                    AIPackage(sub.sub_type.decode("ascii"), sub.data)
                )

        # Transport destinations
        pending_dodt: list[tuple] | None = None
        for sub in raw.subrecords:
            if sub.sub_type == b"DODT" and len(sub.data) >= DODT_SIZE:
                pending_dodt = list(struct.unpack_from(DODT_FMT, sub.data))
            elif sub.sub_type == b"DNAM" and pending_dodt is not None:
                cell_name = decode_cstring(sub.data)
                obj.transport.append(TransportDest(*pending_dodt, cell_name))
                pending_dodt = None

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_refid(tag: bytes, ref: RefId) -> None:
            data = encode_refid_to_subrecord(ref, format_version)
            out.extend(pack_subrec_header(tag, len(data)) + data)

        def add_cstr(tag: bytes, s: str) -> None:
            d = encode_cstring(s)
            out.extend(pack_subrec_header(tag, len(d)) + d)

        add_refid(b"NAME", self.record_id)
        if self.mesh:
            add_cstr(b"MODL", self.mesh)
        if not isinstance(self.sound_template, EmptyRefId):
            add_refid(b"CNAM", self.sound_template)
        if self.name:
            add_cstr(b"FNAM", self.name)
        if not isinstance(self.script, EmptyRefId):
            add_refid(b"SCRI", self.script)

        out += pack_subrec_header(b"NPDT", NPDT_SIZE)
        out += struct.pack(NPDT_FMT,
                           self.crea_type, self.level,
                           self.strength, self.intelligence, self.willpower, self.agility,
                           self.speed, self.endurance, self.personality, self.luck,
                           self.health, self.mana, self.fatigue,
                           self.soul,
                           self.combat, self.magic, self.stealth,
                           self.attack1_min, self.attack1_max,
                           self.attack2_min, self.attack2_max,
                           self.attack3_min, self.attack3_max,
                           self.gold)

        out += pack_subrec_header(b"FLAG", 4) + pack_i32(self.crea_flags)

        if self.scale != 1.0:
            out += pack_subrec_header(b"XSCL", 4) + struct.pack("<f", self.scale)

        for item in self.inventory:
            if format_version <= 23:
                item_name = item.item.value if isinstance(item.item, StringRefId) else ""
                item_data = encode_fixed_string(item_name, 32)
            else:
                item_data = encode_refid_to_subrecord(item.item, format_version)
            payload = pack_i32(item.count) + item_data
            out += pack_subrec_header(b"NPCO", len(payload)) + payload

        for spell in self.spells:
            if format_version <= 23:
                spell_name = spell.value if isinstance(spell, StringRefId) else ""
                spell_data = encode_fixed_string(spell_name, 32)
            else:
                spell_data = encode_refid_to_subrecord(spell, format_version)
            out += pack_subrec_header(b"NPCS", NPCS_SIZE) + spell_data

        out += pack_subrec_header(b"AIDT", AIDT_SIZE)
        out += struct.pack(AIDT_FMT,
                           self.ai_hello, self.ai_fight, self.ai_flee,
                           self.ai_alarm, self.ai_services)

        for pkg in self.ai_packages:
            tag = pkg.package_type.encode("ascii")[:4]
            out += pack_subrec_header(tag, len(pkg.raw_data)) + pkg.raw_data

        for dest in self.transport:
            out += pack_subrec_header(b"DODT", DODT_SIZE)
            out += struct.pack(DODT_FMT,
                               dest.pos_x, dest.pos_y, dest.pos_z,
                               dest.rot_x, dest.rot_y, dest.rot_z)
            d = encode_cstring(dest.cell_name)
            out += pack_subrec_header(b"DNAM", len(d)) + d

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "CREA",
            "record_id": refid_to_db_text(self.record_id),
            "mesh": self.mesh,
            "sound_template": refid_to_db_text(self.sound_template),
            "name": self.name,
            "script": refid_to_db_text(self.script),
            "crea_type": self.crea_type,
            "level": self.level,
            "strength": self.strength,
            "intelligence": self.intelligence,
            "willpower": self.willpower,
            "agility": self.agility,
            "speed": self.speed,
            "endurance": self.endurance,
            "personality": self.personality,
            "luck": self.luck,
            "health": self.health,
            "mana": self.mana,
            "fatigue": self.fatigue,
            "soul": self.soul,
            "combat": self.combat,
            "magic": self.magic,
            "stealth": self.stealth,
            "attack1_min": self.attack1_min,
            "attack1_max": self.attack1_max,
            "attack2_min": self.attack2_min,
            "attack2_max": self.attack2_max,
            "attack3_min": self.attack3_min,
            "attack3_max": self.attack3_max,
            "gold": self.gold,
            "crea_flags": self.crea_flags,
            "scale": self.scale,
            "inventory": [{"count": i.count, "item": refid_to_db_text(i.item)}
                          for i in self.inventory],
            "spells": [refid_to_db_text(s) for s in self.spells],
            "ai_hello": self.ai_hello,
            "ai_fight": self.ai_fight,
            "ai_flee": self.ai_flee,
            "ai_alarm": self.ai_alarm,
            "ai_services": self.ai_services,
            "ai_packages": [{"type": p.package_type, "raw_hex": p.raw_data.hex()}
                            for p in self.ai_packages],
            "transport": [{"pos_x": t.pos_x, "pos_y": t.pos_y, "pos_z": t.pos_z,
                           "rot_x": t.rot_x, "rot_y": t.rot_y, "rot_z": t.rot_z,
                           "cell_name": t.cell_name}
                          for t in self.transport],
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Creature":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id     = refid_from_db_text(d.get("record_id", ""))
        obj.mesh          = d.get("mesh", "")
        obj.sound_template = refid_from_db_text(d.get("sound_template", ""))
        obj.name          = d.get("name", "")
        obj.script        = refid_from_db_text(d.get("script", ""))
        obj.crea_type     = d.get("crea_type", 0)
        obj.level         = d.get("level", 1)
        obj.strength      = d.get("strength", 0)
        obj.intelligence  = d.get("intelligence", 0)
        obj.willpower     = d.get("willpower", 0)
        obj.agility       = d.get("agility", 0)
        obj.speed         = d.get("speed", 0)
        obj.endurance     = d.get("endurance", 0)
        obj.personality   = d.get("personality", 0)
        obj.luck          = d.get("luck", 0)
        obj.health        = d.get("health", 0)
        obj.mana          = d.get("mana", 0)
        obj.fatigue       = d.get("fatigue", 0)
        obj.soul          = d.get("soul", 0)
        obj.combat        = d.get("combat", 0)
        obj.magic         = d.get("magic", 0)
        obj.stealth       = d.get("stealth", 0)
        obj.attack1_min   = d.get("attack1_min", 0)
        obj.attack1_max   = d.get("attack1_max", 0)
        obj.attack2_min   = d.get("attack2_min", 0)
        obj.attack2_max   = d.get("attack2_max", 0)
        obj.attack3_min   = d.get("attack3_min", 0)
        obj.attack3_max   = d.get("attack3_max", 0)
        obj.gold          = d.get("gold", 0)
        obj.crea_flags    = d.get("crea_flags", 0)
        obj.scale         = d.get("scale", 1.0)
        obj.inventory     = [ContItem(i["count"], refid_from_db_text(i["item"]))
                             for i in d.get("inventory", [])]
        obj.spells        = [refid_from_db_text(s) for s in d.get("spells", [])]
        obj.ai_hello      = d.get("ai_hello", 0)
        obj.ai_fight      = d.get("ai_fight", 0)
        obj.ai_flee       = d.get("ai_flee", 0)
        obj.ai_alarm      = d.get("ai_alarm", 0)
        obj.ai_services   = d.get("ai_services", 0)
        obj.ai_packages   = [AIPackage(p["type"], bytes.fromhex(p["raw_hex"]))
                             for p in d.get("ai_packages", [])]
        obj.transport     = [TransportDest(**t) for t in d.get("transport", [])]
        obj.flags         = d.get("flags", 0)
        return obj
