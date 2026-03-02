"""
ESM record type definitions for OpenMW.

Maps each record type to its required asset categories and type-specific metadata
that the orchestrator needs to produce correct generation prompts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ESMType(str, Enum):
    # Equippable items
    WEAP = "WEAP"
    ARMO = "ARMO"
    CLOT = "CLOT"
    # Actors
    NPC_ = "NPC_"
    CREA = "CREA"
    # World objects
    STAT = "STAT"
    ACTI = "ACTI"
    CONT = "CONT"
    DOOR = "DOOR"
    LIGH = "LIGH"
    # Inventory items
    MISC = "MISC"
    BOOK = "BOOK"
    ALCH = "ALCH"
    INGR = "INGR"
    # Tools
    LOCK = "LOCK"
    PROB = "PROB"
    APPA = "APPA"
    REPA = "REPA"
    # Character parts
    BODY = "BODY"
    # Terrain
    LTEX = "LTEX"


class WeaponSubtype(str, Enum):
    SHORT_BLADE = "ShortBlade"
    LONG_BLADE = "LongBlade"
    BLUNT_1H = "Blunt1H"
    BLUNT_2H = "Blunt2H"
    BLUNT_2W = "Blunt2W"   # two-wide (staves)
    SPEAR = "Spear"
    AXE_1H = "Axe1H"
    AXE_2H = "Axe2H"
    BOW = "Bow"
    CROSSBOW = "Crossbow"
    THROWN = "Thrown"
    ARROW = "Arrow"
    BOLT = "Bolt"


class ArmorSubtype(str, Enum):
    HELMET = "Helmet"
    CUIRASS = "Cuirass"
    LEFT_PAULDRON = "LPauldron"
    RIGHT_PAULDRON = "RPauldron"
    GREAVES = "Greaves"
    BOOTS = "Boots"
    LEFT_GAUNTLET = "LGauntlet"
    RIGHT_GAUNTLET = "RGauntlet"
    SHIELD = "Shield"
    LEFT_BRACER = "LBracer"
    RIGHT_BRACER = "RBracer"


class ClothingSubtype(str, Enum):
    PANTS = "Pants"
    SHOES = "Shoes"
    SHIRT = "Shirt"
    BELT = "Belt"
    ROBE = "Robe"
    LEFT_GLOVE = "LGlove"
    RIGHT_GLOVE = "RGlove"
    SKIRT = "Skirt"
    RING = "Ring"
    AMULET = "Amulet"


class ApparatusSubtype(str, Enum):
    MORTAR_PESTLE = "MortarPestle"
    ALEMBIC = "Alembic"
    CALCINATOR = "Calcinator"
    RETORT = "Retort"


class BodyPartType(str, Enum):
    HEAD = "Head"
    HAIR = "Hair"
    NECK = "Neck"
    CHEST = "Chest"
    GROIN = "Groin"
    HAND = "Hand"
    WRIST = "Wrist"
    FOREARM = "Forearm"
    UPPERARM = "Upperarm"
    FOOT = "Foot"
    ANKLE = "Ankle"
    KNEE = "Knee"
    UPPERLEG = "Upperleg"
    CLAVICLE = "Clavicle"
    TAIL = "Tail"


class CreatureType(str, Enum):
    CREATURE = "Creature"
    DAEDRA = "Daedra"
    UNDEAD = "Undead"
    HUMANOID = "Humanoid"


@dataclass(frozen=True)
class AssetRequirements:
    """Declares which asset categories a record type needs."""
    needs_3d_model: bool = False
    needs_icon: bool = False          # inventory icon (ITEX)
    needs_texture: bool = False       # diffuse/PBR texture for the mesh
    needs_open_sound: bool = False    # DOOR open sound
    needs_close_sound: bool = False   # DOOR close sound
    needs_ambient_sound: bool = False # LIGH ambient sound
    needs_body_parts: bool = False    # ARMO/CLOT wearable parts (flag: needs rigging later)
    needs_rigging: bool = False       # NPC_/CREA/BODY — skinned mesh
    is_terrain_texture: bool = False  # LTEX — no mesh, only tiling texture

    # Human-readable note for the orchestrator system prompt
    notes: str = ""


# Canonical requirements for each ESM type.
ASSET_REQUIREMENTS: dict[ESMType, AssetRequirements] = {
    ESMType.STAT: AssetRequirements(
        needs_3d_model=True, needs_texture=True,
        notes="Static world decoration. No icon. Only a mesh and its diffuse/PBR texture.",
    ),
    ESMType.ACTI: AssetRequirements(
        needs_3d_model=True, needs_texture=True,
        notes="Activatable world object (lever, button, shrine). Like STAT but scriptable.",
    ),
    ESMType.CONT: AssetRequirements(
        needs_3d_model=True, needs_texture=True,
        notes="Container (chest, barrel, sack). Should have an openable form if possible, "
              "but a static closed mesh is sufficient.",
    ),
    ESMType.DOOR: AssetRequirements(
        needs_3d_model=True, needs_texture=True,
        needs_open_sound=True, needs_close_sound=True,
        notes="Door mesh + two sounds (open, close). Keep mesh orientation so it rotates "
              "naturally on the vertical axis.",
    ),
    ESMType.LIGH: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        needs_ambient_sound=True,
        notes="Light source. If carryable, needs an inventory icon. "
              "Ambient sound is optional but recommended (e.g. torch crackle).",
    ),
    ESMType.MISC: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Miscellaneous inventory item (key, trinket, gem). Small object.",
    ),
    ESMType.BOOK: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Book or scroll world model + inventory icon.",
    ),
    ESMType.ALCH: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Potion bottle. Typically small vial or bottle shape.",
    ),
    ESMType.INGR: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Alchemy ingredient. Small organic or mineral object.",
    ),
    ESMType.LOCK: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Lockpick tool. Thin, elongated metal tool.",
    ),
    ESMType.PROB: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Probe tool for traps. Similar in shape to lockpick but distinct.",
    ),
    ESMType.APPA: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Alchemy apparatus: MortarPestle, Alembic, Calcinator, or Retort. "
              "Subtype determines the shape.",
    ),
    ESMType.REPA: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Repair hammer/tool for maintaining weapons and armor.",
    ),
    ESMType.WEAP: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        notes="Weapon. Subtype (ShortBlade, LongBlade, Blunt1H, Spear, Bow, Arrow, etc.) "
              "strongly determines shape. Generate a weapon appropriate for the subtype.",
    ),
    ESMType.ARMO: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        needs_body_parts=True,
        notes="Armor piece. Ground/held mesh + inventory icon are fully generated. "
              "Body part (wearable) meshes require skeleton alignment — flag in plan "
              "as needing manual rigging pass.",
    ),
    ESMType.CLOT: AssetRequirements(
        needs_3d_model=True, needs_icon=True, needs_texture=True,
        needs_body_parts=True,
        notes="Clothing piece. Same caveats as ARMO re: body part alignment.",
    ),
    ESMType.BODY: AssetRequirements(
        needs_3d_model=True, needs_texture=True,
        needs_rigging=True,
        notes="Body part mesh (head, hair, hand, etc.). Must be skinned and matched to "
              "race skeleton. Requires manual rigging — pipeline generates reference mesh only.",
    ),
    ESMType.NPC_: AssetRequirements(
        needs_3d_model=True, needs_texture=True,
        needs_rigging=True,
        notes="NPC composed of BODY part records. Pipeline generates head/hair meshes and "
              "skin textures only. Full rigging requires manual work or separate tools.",
    ),
    ESMType.CREA: AssetRequirements(
        needs_3d_model=True, needs_texture=True,
        needs_rigging=True,
        notes="Creature with full body mesh. Hunyuan3D generates the static mesh; "
              "rigging and animations require manual work.",
    ),
    ESMType.LTEX: AssetRequirements(
        is_terrain_texture=True, needs_texture=True,
        notes="Land texture. No mesh. Generate a seamless tileable terrain texture only.",
    ),
}


def get_requirements(esm_type: ESMType) -> AssetRequirements:
    return ASSET_REQUIREMENTS[esm_type]
