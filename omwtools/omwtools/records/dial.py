"""DIAL and INFO records — dialogue topics and responses.

DIAL:
  NAME  → topic string (C-string for old format)
  DATA  → dialogue type (1 byte int8)

INFO:
  INAM  → record_id (C-string, unique info ID)
  PNAM  → previous INFO id
  NNAM  → next INFO id
  DATA  → info conditions (12 bytes: int32 type + int32 disp + int32 rank +
                            int8 gender + int8 pcrank + int16 pad)
  ONAM  → actor RefId
  RNAM  → race RefId
  CNAM  → class RefId
  FNAM  → faction RefId
  ANAM  → cell name string
  DNAM  → PC faction RefId
  SNAM  → sound file path
  NAME  → response text
  SCVR  → condition variable (packed string, followed by INTV or FLTV)
  BNAM  → result script
  QSTN  → quest name flag (1 byte)
  QSTF  → quest finished flag (1 byte)
  QSTR  → quest restart flag (1 byte)
  DELE  → deleted flag
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from omwtools.io.codec import (
    decode_cstring, encode_cstring, decode_string,
    pack_subrec_header, pack_i32, pack_u8,
    unpack_i32, unpack_u8,
)
from omwtools.io.refid import (
    RefId, EmptyRefId,
    decode_refid_from_subrecord, encode_refid_to_subrecord, refid_to_db_text,
)
from omwtools.records.base import BaseRecord, RawRecord

# INFO DATA: int32 type + int32 disposition + int8 rank +
#            int8 gender + int8 pc_rank + int8 padding = 12 bytes
INFO_DATA_FMT = "<iibbbB"
INFO_DATA_SIZE = struct.calcsize(INFO_DATA_FMT)  # 12 (2×4 + 4×1)


@dataclass
class InfoCondition:
    """One SCVR condition entry."""
    index: str = "0"           # 1 char: '0'-'F' (which local variable index)
    func_class: str = "1"      # 1 char: function class
    func_type: str = "0"       # 1 char: variable type char
    comparison: str = "0"      # 1 char: comparison operator
    var_name: str = ""         # variable name (rest of SCVR string)
    value_int: Optional[int] = None
    value_float: Optional[float] = None


@dataclass
class Dialogue(BaseRecord):
    """DIAL record — dialogue topic."""

    REC_TYPE = b"DIAL"

    flags: int = 0
    unknown: int = 0
    topic: str = ""
    dial_type: int = 0   # 0=regular, 1=voice, 2=greeting, 3=persuasion, 4=journal

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "Dialogue":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.topic = decode_cstring(name_sub.data)

        data_sub = raw.get_subrecord(b"DATA")
        if data_sub and len(data_sub.data) >= 1:
            obj.dial_type = unpack_u8(data_sub.data)

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()
        n = encode_cstring(self.topic)
        out += pack_subrec_header(b"NAME", len(n)) + n
        out += pack_subrec_header(b"DATA", 1) + pack_u8(self.dial_type)
        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "DIAL",
            "topic": self.topic,
            "dial_type": self.dial_type,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Dialogue":
        obj = cls()
        obj.topic     = d.get("topic", "")
        obj.dial_type = d.get("dial_type", 0)
        obj.flags     = d.get("flags", 0)
        return obj


@dataclass
class DialogueInfo(BaseRecord):
    """INFO record — dialogue response."""

    REC_TYPE = b"INFO"

    flags: int = 0
    unknown: int = 0
    record_id: str = ""       # INAM (plain string, not RefId)
    prev_id: str = ""         # PNAM
    next_id: str = ""         # NNAM

    # DATA fields
    info_type: int = 0        # 0=topic, 1=voice, 2=greeting, 3=persuasion, 4=journal
    disp_index: int = 0
    rank: int = -1
    gender: int = -1          # -1=any, 0=male, 1=female
    pc_rank: int = -1

    # optional filter fields
    actor: RefId = field(default_factory=EmptyRefId)   # ONAM
    race: RefId = field(default_factory=EmptyRefId)    # RNAM
    class_id: RefId = field(default_factory=EmptyRefId)  # CNAM
    faction: RefId = field(default_factory=EmptyRefId) # FNAM
    cell: str = ""                                     # ANAM
    pc_faction: RefId = field(default_factory=EmptyRefId)  # DNAM
    sound: str = ""                                    # SNAM
    response: str = ""                                 # NAME (response text)
    conditions: list[InfoCondition] = field(default_factory=list)
    result_script: str = ""                            # BNAM
    quest_name: int = 0    # QSTN
    quest_finish: int = 0  # QSTF
    quest_restart: int = 0 # QSTR
    deleted: bool = False  # DELE

    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "DialogueInfo":
        obj = cls(flags=raw.flags, unknown=raw.unknown)

        def get_refid(tag: bytes) -> RefId:
            sub = raw.get_subrecord(tag)
            return decode_refid_from_subrecord(sub.data, format_version) if sub else EmptyRefId()

        inam = raw.get_subrecord(b"INAM")
        if inam:
            obj.record_id = decode_cstring(inam.data)
        pnam = raw.get_subrecord(b"PNAM")
        if pnam:
            obj.prev_id = decode_cstring(pnam.data)
        nnam = raw.get_subrecord(b"NNAM")
        if nnam:
            obj.next_id = decode_cstring(nnam.data)

        data_sub = raw.get_subrecord(b"DATA")
        if data_sub and len(data_sub.data) >= INFO_DATA_SIZE:
            vals = struct.unpack_from(INFO_DATA_FMT, data_sub.data)
            obj.info_type, obj.disp_index, obj.rank, obj.gender, obj.pc_rank, _ = vals

        obj.actor     = get_refid(b"ONAM")
        obj.race      = get_refid(b"RNAM")
        obj.class_id  = get_refid(b"CNAM")
        obj.faction   = get_refid(b"FNAM")

        anam = raw.get_subrecord(b"ANAM")
        if anam:
            obj.cell = decode_cstring(anam.data)

        obj.pc_faction = get_refid(b"DNAM")

        snam = raw.get_subrecord(b"SNAM")
        if snam:
            obj.sound = decode_cstring(snam.data)

        name_sub = raw.get_subrecord(b"NAME")
        if name_sub:
            obj.response = decode_string(name_sub.data)

        # SCVR/INTV/FLTV condition blocks (state machine)
        pending: InfoCondition | None = None
        for sub in raw.subrecords:
            if sub.sub_type == b"SCVR":
                if pending is not None:
                    obj.conditions.append(pending)
                raw_bytes = sub.data
                # Format: index(1) + func_class(1) + func_type(1) + comparison(1) + var_name
                if len(raw_bytes) >= 4:
                    pending = InfoCondition(
                        index=chr(raw_bytes[0]),
                        func_class=chr(raw_bytes[1]),
                        func_type=chr(raw_bytes[2]),
                        comparison=chr(raw_bytes[3]),
                        var_name=raw_bytes[4:].decode("cp1252", errors="replace"),
                    )
                else:
                    pending = InfoCondition()
            elif sub.sub_type == b"INTV" and pending is not None:
                if len(sub.data) >= 4:
                    pending.value_int = unpack_i32(sub.data)
            elif sub.sub_type == b"FLTV" and pending is not None:
                if len(sub.data) >= 4:
                    pending.value_float = struct.unpack_from("<f", sub.data)[0]
        if pending is not None:
            obj.conditions.append(pending)

        bnam = raw.get_subrecord(b"BNAM")
        if bnam:
            obj.result_script = decode_string(bnam.data)

        qstn = raw.get_subrecord(b"QSTN")
        if qstn and qstn.data:
            obj.quest_name = qstn.data[0]
        qstf = raw.get_subrecord(b"QSTF")
        if qstf and qstf.data:
            obj.quest_finish = qstf.data[0]
        qstr = raw.get_subrecord(b"QSTR")
        if qstr and qstr.data:
            obj.quest_restart = qstr.data[0]

        if raw.get_subrecord(b"DELE") is not None:
            obj.deleted = True

        return obj

    def encode_subrecords(self, format_version: int) -> bytes:
        out = bytearray()

        def add_cstr(tag: bytes, s: str) -> None:
            if s:
                d = encode_cstring(s)
                out.extend(pack_subrec_header(tag, len(d)) + d)

        def add_refid(tag: bytes, ref: RefId) -> None:
            data = encode_refid_to_subrecord(ref, format_version)
            out.extend(pack_subrec_header(tag, len(data)) + data)

        def add_cstr_always(tag: bytes, s: str) -> None:
            """Write subrecord even when s is empty (required for PNAM/NNAM)."""
            d = encode_cstring(s)
            out.extend(pack_subrec_header(tag, len(d)) + d)

        add_cstr(b"INAM", self.record_id)
        add_cstr_always(b"PNAM", self.prev_id)
        add_cstr_always(b"NNAM", self.next_id)

        out += pack_subrec_header(b"DATA", INFO_DATA_SIZE)
        out += struct.pack(INFO_DATA_FMT,
                           self.info_type, self.disp_index, self.rank,
                           self.gender, self.pc_rank, 0)

        add_refid(b"ONAM", self.actor)
        add_refid(b"RNAM", self.race)
        add_refid(b"CNAM", self.class_id)
        add_refid(b"FNAM", self.faction)
        add_cstr(b"ANAM", self.cell)
        add_refid(b"DNAM", self.pc_faction)
        add_cstr(b"SNAM", self.sound)

        if self.response:
            txt = self.response.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"NAME", len(txt)) + txt

        for cond in self.conditions:
            scvr = (
                cond.index.encode("cp1252")[:1] +
                cond.func_class.encode("cp1252")[:1] +
                cond.func_type.encode("cp1252")[:1] +
                cond.comparison.encode("cp1252")[:1] +
                cond.var_name.encode("cp1252", errors="replace")
            )
            out += pack_subrec_header(b"SCVR", len(scvr)) + scvr
            if cond.value_int is not None:
                out += pack_subrec_header(b"INTV", 4) + pack_i32(cond.value_int)
            elif cond.value_float is not None:
                out += pack_subrec_header(b"FLTV", 4) + struct.pack("<f", cond.value_float)

        if self.result_script:
            bs = self.result_script.encode("cp1252", errors="replace")
            out += pack_subrec_header(b"BNAM", len(bs)) + bs
        if self.quest_name:
            out += pack_subrec_header(b"QSTN", 1) + pack_u8(self.quest_name)
        if self.quest_finish:
            out += pack_subrec_header(b"QSTF", 1) + pack_u8(self.quest_finish)
        if self.quest_restart:
            out += pack_subrec_header(b"QSTR", 1) + pack_u8(self.quest_restart)
        if self.deleted:
            out += pack_subrec_header(b"DELE", 4) + b"\x00" * 4

        return bytes(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rec_type": "INFO",
            "record_id": self.record_id,
            "prev_id": self.prev_id,
            "next_id": self.next_id,
            "info_type": self.info_type,
            "disp_index": self.disp_index,
            "rank": self.rank,
            "gender": self.gender,
            "pc_rank": self.pc_rank,
            "actor": refid_to_db_text(self.actor),
            "race": refid_to_db_text(self.race),
            "class_id": refid_to_db_text(self.class_id),
            "faction": refid_to_db_text(self.faction),
            "cell": self.cell,
            "pc_faction": refid_to_db_text(self.pc_faction),
            "sound": self.sound,
            "response": self.response,
            "conditions": [
                {
                    "index": c.index,
                    "func_class": c.func_class,
                    "func_type": c.func_type,
                    "comparison": c.comparison,
                    "var_name": c.var_name,
                    "value_int": c.value_int,
                    "value_float": c.value_float,
                }
                for c in self.conditions
            ],
            "result_script": self.result_script,
            "quest_name": self.quest_name,
            "quest_finish": self.quest_finish,
            "quest_restart": self.quest_restart,
            "deleted": self.deleted,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DialogueInfo":
        from omwtools.io.refid import refid_from_db_text
        obj = cls()
        obj.record_id     = d.get("record_id", "")
        obj.prev_id       = d.get("prev_id", "")
        obj.next_id       = d.get("next_id", "")
        obj.info_type     = d.get("info_type", 0)
        obj.disp_index    = d.get("disp_index", 0)
        obj.rank          = d.get("rank", -1)
        obj.gender        = d.get("gender", -1)
        obj.pc_rank       = d.get("pc_rank", -1)
        obj.actor         = refid_from_db_text(d.get("actor", ""))
        obj.race          = refid_from_db_text(d.get("race", ""))
        obj.class_id      = refid_from_db_text(d.get("class_id", ""))
        obj.faction       = refid_from_db_text(d.get("faction", ""))
        obj.cell          = d.get("cell", "")
        obj.pc_faction    = refid_from_db_text(d.get("pc_faction", ""))
        obj.sound         = d.get("sound", "")
        obj.response      = d.get("response", "")
        obj.result_script = d.get("result_script", "")
        obj.quest_name    = d.get("quest_name", 0)
        obj.quest_finish  = d.get("quest_finish", 0)
        obj.quest_restart = d.get("quest_restart", 0)
        obj.deleted       = d.get("deleted", False)
        obj.flags         = d.get("flags", 0)
        obj.conditions = [
            InfoCondition(
                index=c.get("index", "0"),
                func_class=c.get("func_class", "1"),
                func_type=c.get("func_type", "0"),
                comparison=c.get("comparison", "0"),
                var_name=c.get("var_name", ""),
                value_int=c.get("value_int"),
                value_float=c.get("value_float"),
            )
            for c in d.get("conditions", [])
        ]
        return obj
