"""Record registry and parse_record() dispatcher."""

from __future__ import annotations

from omwtools.records.base import BaseRecord, RawRecord
from omwtools.records.unknown import UnknownRecord
from omwtools.records.tes3 import TES3Header
from omwtools.records.npc_ import NPC
from omwtools.records.cell import Cell
from omwtools.records.scpt import Script
from omwtools.records.lual import LUALRecord

# Phase 2 records
from omwtools.records.spel import Spell
from omwtools.records.ench import Enchantment
from omwtools.records.alch import Potion
from omwtools.records.ingr import Ingredient
from omwtools.records.weap import Weapon
from omwtools.records.armo import Armour
from omwtools.records.clot import Clothing
from omwtools.records.book import Book
from omwtools.records.misc_ import MiscItem, Lockpick, Probe, RepairItem, Apparatus
from omwtools.records.ligh import Light
from omwtools.records.door import Door, Activator, Static
from omwtools.records.body import BodyPart
from omwtools.records.cont import Container
from omwtools.records.dial import Dialogue, DialogueInfo
from omwtools.records.race import Race, Birthsign
from omwtools.records.fact import Faction, Class
from omwtools.records.glob import GlobalVariable, GameSetting
from omwtools.records.skil import Skill, MagicEffect
from omwtools.records.levc import LevelledCreature, LevelledItem
from omwtools.records.regn import Region
from omwtools.records.soun import Sound, SoundGenerator, LandTexture
from omwtools.records.crea import Creature
from omwtools.records.land import Land
from omwtools.records.pgrd import Pathgrid
from omwtools.records.sscr import StartupScript

# ---------------------------------------------------------------------------
# Registry: maps 4-byte record type → BaseRecord subclass
# ---------------------------------------------------------------------------

RECORD_REGISTRY: dict[bytes, type[BaseRecord]] = {
    b"TES3": TES3Header,
    b"NPC_": NPC,
    b"CELL": Cell,
    b"SCPT": Script,
    b"LUAL": LUALRecord,
    # Phase 2
    b"SPEL": Spell,
    b"ENCH": Enchantment,
    b"ALCH": Potion,
    b"INGR": Ingredient,
    b"WEAP": Weapon,
    b"ARMO": Armour,
    b"CLOT": Clothing,
    b"BOOK": Book,
    b"MISC": MiscItem,
    b"LOCK": Lockpick,
    b"PROB": Probe,
    b"REPA": RepairItem,
    b"APPA": Apparatus,
    b"LIGH": Light,
    b"BODY": BodyPart,
    b"DOOR": Door,
    b"ACTI": Activator,
    b"STAT": Static,
    b"CONT": Container,
    b"DIAL": Dialogue,
    b"INFO": DialogueInfo,
    b"RACE": Race,
    b"BSGN": Birthsign,
    b"FACT": Faction,
    b"CLAS": Class,
    b"GLOB": GlobalVariable,
    b"GMST": GameSetting,
    b"SKIL": Skill,
    b"MGEF": MagicEffect,
    b"LEVC": LevelledCreature,
    b"LEVI": LevelledItem,
    b"REGN": Region,
    b"SOUN": Sound,
    b"SNDG": SoundGenerator,
    b"LTEX": LandTexture,
    b"CREA": Creature,
    b"LAND": Land,
    b"PGRD": Pathgrid,
    b"SSCR": StartupScript,
}


def parse_record(raw: RawRecord, format_version: int) -> BaseRecord:
    """Parse a RawRecord into a typed BaseRecord using the registry."""
    cls = RECORD_REGISTRY.get(raw.rec_type, UnknownRecord)
    return cls.from_raw(raw, format_version)


def register(rec_type: bytes, cls: type[BaseRecord]) -> None:
    """Register a new record type handler."""
    RECORD_REGISTRY[rec_type] = cls


__all__ = [
    "RECORD_REGISTRY",
    "parse_record",
    "register",
    "BaseRecord",
    "RawRecord",
    "UnknownRecord",
    "TES3Header",
    "NPC",
    "Cell",
    "Script",
    "LUALRecord",
    "Spell",
    "Enchantment",
    "Potion",
    "Ingredient",
    "Weapon",
    "Armour",
    "Clothing",
    "Book",
    "MiscItem",
    "Lockpick",
    "Probe",
    "RepairItem",
    "Apparatus",
    "Light",
    "BodyPart",
    "Door",
    "Activator",
    "Static",
    "Container",
    "Dialogue",
    "DialogueInfo",
    "Race",
    "Birthsign",
    "Faction",
    "Class",
    "GlobalVariable",
    "GameSetting",
    "Skill",
    "MagicEffect",
    "LevelledCreature",
    "LevelledItem",
    "Region",
    "Sound",
    "SoundGenerator",
    "LandTexture",
    "Creature",
    "Land",
    "Pathgrid",
    "StartupScript",
]
