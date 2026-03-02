"""Shared magic effect list codec.

ENAM subrecord — old format (format_version ≤ 35, all content files):
  24 bytes: int16 effect_id + int8 skill + int8 attribute +
            int32 range + int32 area + int32 duration + int32 mmin + int32 mmax
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

ENAM_FMT = "<hbbiiiii"
ENAM_SIZE = struct.calcsize(ENAM_FMT)  # 24


@dataclass
class EffectEntry:
    """One magic effect entry from an ENAM subrecord."""
    effect_id: int = 0
    skill: int = -1       # -1 = not applicable
    attribute: int = -1   # -1 = not applicable
    range: int = 0        # 0=self, 1=touch, 2=target
    area: int = 0
    duration: int = 0
    mmin: int = 0
    mmax: int = 0


def decode_effects(raw_subs: list) -> list[EffectEntry]:
    """Decode all ENAM subrecords from a list of RawSubrecords."""
    result: list[EffectEntry] = []
    for sub in raw_subs:
        if sub.sub_type != b"ENAM":
            continue
        if len(sub.data) < ENAM_SIZE:
            continue
        vals = struct.unpack_from(ENAM_FMT, sub.data)
        result.append(EffectEntry(
            effect_id=vals[0],
            skill=vals[1],
            attribute=vals[2],
            range=vals[3],
            area=vals[4],
            duration=vals[5],
            mmin=vals[6],
            mmax=vals[7],
        ))
    return result


def encode_effects(effects: list[EffectEntry]) -> bytes:
    """Encode a list of EffectEntry to raw ENAM payload bytes (no headers)."""
    out = bytearray()
    for e in effects:
        out += struct.pack(ENAM_FMT,
                           e.effect_id, e.skill, e.attribute,
                           e.range, e.area, e.duration, e.mmin, e.mmax)
    return bytes(out)


def effects_to_dicts(effects: list[EffectEntry]) -> list[dict[str, Any]]:
    return [
        {
            "effect_id": e.effect_id,
            "skill": e.skill,
            "attribute": e.attribute,
            "range": e.range,
            "area": e.area,
            "duration": e.duration,
            "mmin": e.mmin,
            "mmax": e.mmax,
        }
        for e in effects
    ]


def effects_from_dicts(lst: list[dict[str, Any]]) -> list[EffectEntry]:
    return [
        EffectEntry(
            effect_id=d.get("effect_id", 0),
            skill=d.get("skill", -1),
            attribute=d.get("attribute", -1),
            range=d.get("range", 0),
            area=d.get("area", 0),
            duration=d.get("duration", 0),
            mmin=d.get("mmin", 0),
            mmax=d.get("mmax", 0),
        )
        for d in lst
    ]
