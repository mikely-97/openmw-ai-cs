"""REGN — Region record.

Subrecords:
  NAME  → record_id (RefId)
  FNAM  → display name
  WEAT  → weather chances (10 bytes: uint8 × 10 for each weather type)
  BNAM  → sleep creature RefId
  CNAM  → map color (uint32 RGBA)
  SNAM  → sound entry (32-byte fixed RefId + 1 byte chance) — repeating
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from omwtools.io.codec import decode_cstring, encode_cstring, pack_subrec_header, pack_u32, unpack_u32
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord

WEAT_SIZE = 10
# SNAM: 32-byte fixed-string RefId + 1 byte chance = 33 bytes
SNAM_SIZE = 33


@dataclass
class WeatherChances:
    clear: int = 0
    cloudy: int = 0
    foggy: int = 0
    overcast: int = 0
    rain: int = 0
    thunder: int = 0
    ash: int = 0
    blight: int = 0
    snow: int = 0
    blizzard: int = 0


@dataclass
class SoundEntry:
    sound: RefId = field(default_factory=EmptyRefId)
    chance: int = 0


@dataclass
class Region(BaseRecord):
    """REGN record — geographic region."""

    REC_TYPE = b"REGN"

    flags: int = 0
    unknown: int = 0
    record_id: RefId = field(default_factory=EmptyRefId)
    name: str = ""
    weather: WeatherChances = field(default_factory=WeatherChances)
    sleep_creature: RefId = field(default_factory=EmptyRefId)
    map_color: int = 0
    sounds: list[SoundEntry] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Region":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        def get_refid(tag: bytes) -> RefId:
            sub = raw.get_subrecord(tag)
            return decode_refid_from_subrecord(sub.data, format_version) if sub else EmptyRefId()

        obj.record_id = get_refid(b"NAME")

        fnam = raw.get_subrecord(b"FNAM")
        if fnam:
            obj.name = decode_cstring(fnam.data)

        weat = raw.get_subrecord(b"WEAT")
        if weat and len(weat.data) >= WEAT_SIZE:
            d = weat.data
            obj.weather = WeatherChances(
                clear=d[0], cloudy=d[1], foggy=d[2], overcast=d[3],
                rain=d[4], thunder=d[5], ash=d[6], blight=d[7],
                snow=d[8] if len(d) > 8 else 0,
                blizzard=d[9] if len(d) > 9 else 0,
            )

        obj.sleep_creature = get_refid(b"BNAM")

        cnam = raw.get_subrecord(b"CNAM")
        if cnam and len(cnam.data) >= 4:
            obj.map_color = unpack_u32(cnam.data)

        for sub in raw.get_subrecords(b"SNAM"):
            if len(sub.data) >= SNAM_SIZE:
                sound = decode_refid_from_subrecord(sub.data[:32], format_version)
                chance = sub.data[32]
                obj.sounds.append(SoundEntry(sound, chance))

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
        if self.name:
            add_cstr(b"FNAM", self.name)

        w = self.weather
        weat = bytes([w.clear, w.cloudy, w.foggy, w.overcast, w.rain,
                      w.thunder, w.ash, w.blight, w.snow, w.blizzard])
        out += pack_subrec_header(b"WEAT", WEAT_SIZE) + weat

        if not isinstance(self.sleep_creature, EmptyRefId):
            add_refid(b"BNAM", self.sleep_creature)
        out += pack_subrec_header(b"CNAM", 4) + pack_u32(self.map_color)

        for se in self.sounds:
            # 32-byte fixed-string + 1 byte chance
            sound_data = encode_refid_to_subrecord(se.sound, format_version)
            # Pad or truncate to 32 bytes
            fixed = (sound_data + b"\x00" * 32)[:32]
            out += pack_subrec_header(b"SNAM", 33) + fixed + bytes([se.chance])

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        w = self.weather
        return {
            "rec_type": "REGN",
            "record_id": refid_to_db_text(self.record_id),
            "name": self.name,
            "weather": {
                "clear": w.clear, "cloudy": w.cloudy, "foggy": w.foggy,
                "overcast": w.overcast, "rain": w.rain, "thunder": w.thunder,
                "ash": w.ash, "blight": w.blight, "snow": w.snow, "blizzard": w.blizzard,
            },
            "sleep_creature": refid_to_db_text(self.sleep_creature),
            "map_color": self.map_color,
            "sounds": [{"sound": refid_to_db_text(s.sound), "chance": s.chance}
                       for s in self.sounds],
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Region":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id      = refid_from_db_text(d.get("record_id", ""))
        obj.name           = d.get("name", "")
        w = d.get("weather", {})
        obj.weather        = WeatherChances(**w) if w else WeatherChances()
        obj.sleep_creature = refid_from_db_text(d.get("sleep_creature", ""))
        obj.map_color      = d.get("map_color", 0)
        obj.sounds         = [SoundEntry(refid_from_db_text(s["sound"]), s["chance"])
                               for s in d.get("sounds", [])]
        obj.flags          = d.get("flags", 0)
        return obj
