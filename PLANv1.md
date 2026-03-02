# Plan: `omwtools` — Python Library + CLI for OpenMW Extended ESM Format

## Context

OpenMW's game data lives in binary `.esm`/`.esp` files (the TES3/Morrowind format, extended by OpenMW with variant RefId encoding). The existing OpenMW-CS editor is a large Qt6/C++ GUI app — not scriptable, not AI-agent-friendly, and not able to export human-readable data. This project creates a standalone Python library and CLI that reads/writes the same format, using **SQLite as primary storage** and **JSON for export/import**, enabling programmatic editing and AI agent workflows.

## Target: new standalone Python repo (not inside OpenMW)

---

## OpenMW Native Formats (Corrections from source analysis)

### `.omwgame` and `.omwaddon`
These use the **exact same binary ESM3 format** as `.esm` and `.esp`:
- `.omwgame` ≡ `.esm` (game master file — `HEDR.file_type = 0`, no parent masters)
- `.omwaddon` ≡ `.esp` (addon plugin — `HEDR.file_type = 1`, may reference master files)
- The extension is the only difference. The reader/writer accepts all four extensions.
- New omwgame/omwaddon files should set `FORM` format_version = `CurrentContentFormatVersion = 1`.

### `.omwscripts` (note: plural 's')
**Completely different format** — plain text, not binary ESM.
Each non-comment, non-empty line:
```
FLAG1, FLAG2, TYPE1 : path/to/script.lua
```
- **Script-level flags**: `GLOBAL`, `CUSTOM`, `PLAYER`, `MENU`
- **Object-type attachment tags**: `ACTIVATOR`, `ARMOR`, `BOOK`, `CLOTHING`,
  `CONTAINER`, `CREATURE`, `DOOR`, `INGREDIENT`, `LIGHT`, `MISC_ITEM`, `NPC`,
  `POTION`, `WEAPON`, `APPARATUS`, `LOCKPICK`, `PROBE`, `REPAIR`
- Comment lines start with `#`; empty lines ignored; tags are case-insensitive
- Script path must end with `.lua`
- Example: `GLOBAL: scripts/mymod/main.lua`
- The `MERGE` flag (bit 3) is not a text tag; it only appears in binary `LUAL` records.
- Source: `components/lua/configuration.cpp:parseOMWScripts()`

### `LUAL` record (binary)
`omwgame`/`omwaddon` files may contain `LUAL` (`REC_LUAL`) records — the **binary ESM** encoding of `LuaScriptsCfg`. Subrecords per script entry:
- `LUAS` → VFS path to `.lua` file (string)
- `LUAF` → `uint32 flags` + repeated `uint32 type` (ESM::RecNameInts)
- `LUAD` → initialization data (binary Lua table, optional)
- `LUAR` (repeating) → per-record attach: `byte attach` + RefId + optional `LUAD`
- `LUAI` (repeating) → per-ref attach: `byte attach` + `uint32 refnum_index` + `int32 refnum_content_file` + optional `LUAD`

---

## Project Layout

```
omwtools/
├── pyproject.toml
├── README.md
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   └── fixtures/          # minimal hand-crafted .esm files
└── omwtools/
    ├── __init__.py
    ├── py.typed
    ├── io/
    │   ├── codec.py       # struct helpers, FourCC, fixed-string encode/decode
    │   ├── refid.py       # RefId variant type + binary codec
    │   ├── reader.py      # ESMReader — yields RawRecord objects
    │   └── writer.py      # ESMWriter — writes BaseRecord objects to binary
    ├── omwscripts/
    │   ├── __init__.py
    │   ├── parser.py      # parse .omwscripts text → list[ScriptEntry]
    │   └── writer.py      # list[ScriptEntry] → .omwscripts text
    ├── records/
    │   ├── __init__.py    # RECORD_REGISTRY: dict[bytes, type[BaseRecord]]
    │   ├── base.py        # RawRecord, RawSubrecord, RecordFlags, BaseRecord, UnknownRecord
    │   ├── tes3.py        # TES3 file header
    │   ├── npc_.py        # NPC_
    │   ├── crea.py        # CREA
    │   ├── cell.py        # CELL + CellRef (most complex)
    │   ├── dial.py        # DIAL
    │   ├── info.py        # INFO
    │   ├── scpt.py        # SCPT
    │   ├── lual.py        # LUAL (LuaScriptsCfg binary record)
    │   ├── spel.py        # SPEL
    │   ├── ench.py        # ENCH
    │   ├── alch.py        # ALCH
    │   ├── weap.py        # WEAP
    │   ├── armo.py        # ARMO
    │   ├── clot.py        # CLOT
    │   ├── misc_.py       # MISC / LOCK / PROB / REPA / APPA
    │   ├── book.py        # BOOK
    │   ├── cont.py        # CONT
    │   ├── door.py        # DOOR
    │   ├── ligh.py        # LIGH
    │   ├── acti.py        # ACTI / STAT
    │   ├── glob.py        # GLOB
    │   ├── gmst.py        # GMST
    │   ├── race.py        # RACE
    │   ├── fact.py        # FACT
    │   ├── clas.py        # CLAS
    │   ├── bsgn.py        # BSGN
    │   ├── regn.py        # REGN
    │   ├── soun.py        # SOUN / SNDG
    │   ├── skil.py        # SKIL
    │   ├── mgef.py        # MGEF
    │   ├── ingr.py        # INGR
    │   ├── levc.py        # LEVC
    │   ├── levi.py        # LEVI
    │   ├── land.py        # LAND (blob-heavy)
    │   ├── pgrd.py        # PGRD
    │   └── unknown.py     # UnknownRecord (pass-through blob)
    ├── db/
    │   ├── connection.py  # make_db(), RAII connection helper
    │   ├── schema.py      # Full SQL DDL (CREATE TABLE statements)
    │   ├── store.py       # ModStore — main API class
    │   ├── migrate.py     # schema version migrations
    │   └── queries.py     # named parameterized query helpers
    ├── json_io/
    │   ├── export_.py     # record_to_dict(), export_plugin_to_json()
    │   ├── import_.py     # dict_to_record(), import_plugin_from_json()
    │   └── schema_gen.py  # emit JSON Schema documents per record type
    └── cli/
        ├── main.py        # argparse root + dispatch
        ├── cmd_load.py
        ├── cmd_dump.py
        ├── cmd_export.py
        ├── cmd_import.py
        ├── cmd_query.py
        ├── cmd_write.py
        └── cmd_validate.py
```

---

## Binary Format — Key Facts (from OpenMW source)

**Sources to reference during implementation:**
- `components/esm3/formatversion.hpp` — all version threshold constants
  - `CurrentContentFormatVersion = 1` (use for new omwgame/omwaddon output)
  - `MaxStringRefIdFormatVersion = 23` (≤23: string RefIds; >23: typed RefIds)
- `components/esm/refid.hpp` — RefId variant enum + types
- `components/esm3/loadnpc.hpp` — NPDTstruct52, NPDTstruct12, NPC flags
- `components/esm3/loadcell.hpp` — DATAstruct, AMBIstruct, CellRef layout
- `components/esm3/loadinfo.hpp` — DialInfo DATAstruct, mPrev/mNext, conditions
- `components/esm3/esmreader.hpp` / `esmwriter.hpp` — reference I/O patterns
- `components/esm/luascripts.hpp` / `.cpp` — LUAL subrecord layout
- `components/lua/configuration.cpp` — `.omwscripts` text parser

### Accepted file extensions:
- **Reader**: `.esm`, `.esp`, `.omwgame`, `.omwaddon` (binary ESM3)
- **Reader**: `.omwscripts` (text format — separate code path)
- **Writer**: all above extensions

### HEDR file_type values:
- `0` = ESM/omwgame (game master)
- `1` = ESP/omwaddon (plugin/addon)
- `32` = ESS (saved game — out of scope for initial implementation)

### Record header (16 bytes, little-endian):
```
bytes 0-3:   4-char record type ("NPC_", "CELL", ...)
bytes 4-7:   uint32 total size of all following subrecords
bytes 8-11:  uint32 unknown (always 0; preserve for roundtrip)
bytes 12-15: uint32 flags (0x20=deleted, 0x400=persistent, 0x1000=ignored, 0x2000=blocked)
```

### Subrecord header (8 bytes, little-endian):
```
bytes 0-3:  4-char subrecord type ("NAME", "NPDT", "DATA", ...)
bytes 4-7:  uint32 size of data immediately following
```

### RefId encoding (critical — controlled by format version):
- **format_version ≤ 23** (`MaxStringRefIdFormatVersion`): null-terminated string in subrecord
- **format_version > 23**: first byte is type discriminant (0–6):

| Byte | Type            | Total bytes | Layout                              |
|------|-----------------|-------------|-------------------------------------|
| 0    | Empty           | 1           | —                                   |
| 1    | SizedString     | 5 + n       | 4-byte length + n bytes             |
| 2    | UnsizedString   | 1 + n       | remaining subrecord bytes after type |
| 3    | FormId          | 9           | uint32 index + int32 content_file   |
| 4    | Generated       | 9           | uint64 counter                      |
| 5    | Index           | 9           | 4-byte FourCC + uint32 index        |
| 6    | ESM3ExteriorCell| 9           | int32 X + int32 Y                   |

### TES3 file header subrecords (in order):
1. **FORM** (optional): uint32 format_version — if absent, version = 0
2. **HEDR** (required): float32 esm_version + int32 file_type + char[32] author + char[256] desc + int32 record_count
3. **MAST** / **DATA** pairs (repeating): master filename + uint64 file size

---

## Core Implementation Details

### `omwtools/io/refid.py`
Seven frozen dataclasses: `EmptyRefId`, `StringRefId`, `FormIdRefId`, `GeneratedRefId`, `IndexRefId`, `ESM3ExteriorCellRefId` (+ type alias `RefId = Union[...]`).

Key functions:
```python
decode_refid_from_subrecord(data: bytes, format_version: int) -> RefId
encode_refid_to_subrecord(refid: RefId, format_version: int) -> bytes
refid_to_db_text(refid: RefId) -> str       # canonical text form for SQLite storage
refid_from_db_text(text: str) -> RefId       # reconstruct from text
```
Canonical text forms: `""` (empty), `"caius cosades"` (string), `"FormId:0x1234"`, `"Generated:0xabcdef"`, `"Index:SKIL:3"`, `"Esm3ExteriorCell:2:-4"`.

### `omwtools/io/reader.py` — `ESMReader`
- Context manager, opens file in `"rb"` mode
- **Accepts `.esm`, `.esp`, `.omwgame`, `.omwaddon`** (binary ESM3 format)
- `read_header() -> TES3Header` — must be called first; sets `self.format_version`
- `iter_records() -> Iterator[RawRecord]` — yields one `RawRecord` per record
- `_read_next_raw_record()` — reads 16-byte header, reads `data_size` bytes, calls `_parse_subrecords()`
- `_parse_subrecords(data: bytes) -> list[RawSubrecord]` — state machine over subrecord 8-byte headers
- `lenient=True` mode: logs warnings and skips malformed records instead of raising

### `omwtools/records/base.py`
```python
@dataclass
class RawSubrecord:
    sub_type: bytes; data: bytes; truncated: bool = False

@dataclass
class RawRecord:
    rec_type: bytes; flags: RecordFlags; unknown: int
    raw_data: bytes; subrecords: list[RawSubrecord]
    def get_subrecord(self, sub_type: bytes) -> Optional[RawSubrecord]: ...
    def get_subrecords(self, sub_type: bytes) -> list[RawSubrecord]: ...

class BaseRecord:
    REC_TYPE: ClassVar[bytes]
    flags: RecordFlags
    @classmethod
    def from_raw(cls, raw: RawRecord, format_version: int) -> "BaseRecord": ...
    def encode_subrecords(self, writer: ESMWriter) -> bytes: ...
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> "BaseRecord": ...

class UnknownRecord(BaseRecord):
    # Stores raw_data blob intact — any record type not in RECORD_REGISTRY
    # encode_subrecords returns self._raw_data unchanged
```

### `omwtools/records/__init__.py`
```python
RECORD_REGISTRY: dict[bytes, type[BaseRecord]] = {
    b"TES3": TES3Header,
    b"NPC_": NPC,
    b"CELL": Cell,
    b"LUAL": LUALRecord,
    ...
}

def parse_record(raw: RawRecord, format_version: int) -> BaseRecord:
    cls = RECORD_REGISTRY.get(raw.rec_type, UnknownRecord)
    return cls.from_raw(raw, format_version)

def register(rec_type: bytes, cls: type[BaseRecord]) -> None:
    RECORD_REGISTRY[rec_type] = cls
```

### `omwtools/records/npc_.py` — NPC record (flagship implementation)
Key subrecords:
- `NAME` → `record_id: RefId`
- `FNAM` → `name: str`
- `RNAM/CNAM/ANAM/BNAM/KNAM/SCRI/MODL` → RefIds / strings
- `NPDT` 52 bytes → `NPDTFull` (level, 8 attrs, 27 skills, hp, mana, fatigue, disp, rep, rank, gold); 12 bytes → `NPDTAutocalc`
- `FLAG` → `npc_flags: int` (female, essential, respawn, autocalc + blood type in bits 8-13)
- `NPCO` (repeating) → `inventory: list[ContItem]` — int32 count + RefId
- `NPCS` (repeating) → `spells: list[RefId]`
- `AIDT` 12 bytes → `AIData` (hello uint16, fight/flee/alarm bytes, [3 pad], services int32)
- `AI_W/AI_T/AI_F/AI_E/AI_A` → `ai_packages: list[AIPackage]` (raw_data blob for now)
- `DODT/DNAM` pairs → `transport: list[TransportDest]`

### `omwtools/records/cell.py` — CELL record (most complex)
- `NAME` → cell name/RefId
- `DATA` 12 bytes → `cell_flags: int`, `grid_x: int`, `grid_y: int`
- `RGNN` → region RefId
- `AMBI` 16 bytes → 3× uint32 color + float fog_density
- `WHGT` 4 bytes → float water_height
- `NAM0` → int32 ref_num_counter
- **FRMR state machine**: when `FRMR` seen, start new `CellRef`; accumulate `NAME`, `XSCL`, `DATA`, `TNAM`, `UNAM`, `XSOL`, `XCHG`, `XTEL`, `LOCK`, `LSCR`, `XOWN`, `XRNK`, `DODT`, `DNAM`, `DELE` etc. until next `FRMR` or end
- `MVRF/CNDT` pairs → moved cell references

### `omwtools/records/info.py` — INFO record
- `INAM` → info ID
- `PNAM/NNAM` → prev/next RefIds (rebuilt from sort_order on write)
- `DATA` 12 bytes → `DialInfo.DATAstruct`: type int32, disposition/journal_index int32, npc_rank/gender/pc_rank bytes
- `ONAM/RNAM/CNAM/FNAM/ANAM/DNAM/SNAM` → actor/race/class/faction/pcfaction/cell/sound RefIds
- `NAME` → response text
- `SCVR/INTV/FLTV` → condition groups (function code, comparison operator, variable, value)
- `BNAM` → result script text
- `QSTN/QSTF/QSTR` → quest flags

### `omwtools/omwscripts/parser.py` — `.omwscripts` text format

```python
@dataclass
class ScriptEntry:
    script_path: str          # VFS path to .lua file
    flags: int                # bitmask: GLOBAL=1, CUSTOM=2, PLAYER=4, MERGE=8, MENU=16
    types: list[str]          # object type tags: "NPC", "CREATURE", etc.

SCRIPT_FLAGS = {"GLOBAL": 1, "CUSTOM": 2, "PLAYER": 4, "MENU": 16}
SCRIPT_TYPES = {
    "ACTIVATOR", "ARMOR", "BOOK", "CLOTHING", "CONTAINER", "CREATURE",
    "DOOR", "INGREDIENT", "LIGHT", "MISC_ITEM", "NPC", "POTION",
    "WEAPON", "APPARATUS", "LOCKPICK", "PROBE", "REPAIR",
}

def parse_omwscripts(text: str) -> list[ScriptEntry]: ...
def render_omwscripts(entries: list[ScriptEntry]) -> str: ...
```

---

## SQLite Schema (summary — full DDL in `db/schema.py`)

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Universal record index
CREATE TABLE records (
    id INTEGER PRIMARY KEY,
    mod_id INTEGER NOT NULL REFERENCES mods(id),
    rec_type TEXT NOT NULL,
    record_id_text TEXT NOT NULL,   -- canonical RefId text
    flags INTEGER NOT NULL DEFAULT 0,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    raw_blob BLOB,                  -- set for UnknownRecord; NULL for known types
    UNIQUE(mod_id, rec_type, record_id_text)
);

-- Satellite tables (one per record type, FK to records.id):
-- npcs, npc_spells, npc_inventory, npc_ai_packages, npc_transport
-- creatures, creature_spells, creature_inventory
-- cells, cell_refs
-- weapons, armors, armor_parts, clothings
-- spells, enchantments, potions, magic_effects (shared effect list)
-- dialogues, dialogue_infos, info_conditions
-- scripts
-- lua_script_cfgs (for LUAL records)
-- races, race_powers, factions, faction_reactions
-- game_settings, globals, skills, mgef_records
-- regions, region_sounds
-- levelled_lists, levelled_list_items
-- land_records (terrain blobs)
-- pathgrids
-- mods, master_files, schema_migrations
```

Key design decisions:
- `records.raw_blob` stores unknown record bytes for pass-through fidelity
- `records.sort_order` preserves file order (critical for DIAL→INFO write order)
- RefIds stored as canonical text strings (queryable, human-readable)
- Attribute/skill arrays stored as JSON text within satellite tables (e.g. `attributes_json`, `skills_json`) — avoids 35 extra columns
- `magic_effects` is a shared child table (used by SPEL, ENCH, ALCH, INGR)

---

## CLI Commands

```
omw [--db PATH] [--json] COMMAND

omw load   FILE.esm [FILE2.esp ...]   [--encoding utf-8] [--lenient]
           # also accepts .omwgame, .omwaddon (binary ESM format)
omw scripts load   FILE.omwscripts    # load text-format Lua config
omw scripts dump   [--mod-id N]       # show parsed script entries
omw info   [--mod-id N]
omw dump   [--rec-type TYPE] [--id ID] [--mod-id N] [--output FILE]
omw export --output FILE [--rec-type TYPE] [--id ID] [--mod-id N] [--whole-mod]
omw import FILE.json [--mod-id N]
omw query  "SELECT ..."               [--params A B ...]
omw write  --output FILE.esp --mod-id N  [--format-version N]
           # output extension may be .esp, .esm, .omwaddon, .omwgame
omw validate [--mod-id N]
```

- Every command: `--json` flag forces JSON output to stdout
- `omw query` accepts arbitrary SELECT SQL; returns JSON array of row objects
- Errors: JSON `{"error": "...", "type": "ErrorClassName"}` to stderr + non-zero exit

---

## Roundtrip Pipeline

```
ESM binary (.esm/.esp/.omwgame/.omwaddon)
  → ESMReader.iter_records()         RawRecord stream
  → parse_record(raw, fmt_version)   typed BaseRecord objects
  → ModStore.insert_record()         SQLite rows
         ↕  (user edits SQL / JSON import)
  → ModStore.iter_records_ordered()  typed BaseRecord objects
  → ESMWriter.write_record()         ESM binary

.omwscripts text file
  → parse_omwscripts(text)           list[ScriptEntry]
  → ModStore.insert_omwscripts()     SQLite rows (lua_script_cfgs)
         ↕  (user edits)
  → render_omwscripts(entries)       .omwscripts text
```

**DIAL/INFO write order**: after writing a `DIAL` record, immediately write all child `INFO` records ordered by `dialogue_infos.sort_order`; rebuild `mPrev`/`mNext` from sort position before encode.

**Unknown records**: `UnknownRecord.encode_subrecords()` returns `self._raw_data` unchanged. The `records.raw_blob` column stores this. Fidelity guaranteed for any record type not in the registry.

---

## `pyproject.toml` (key parts)

```toml
[project]
name = "omwtools"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []          # zero external deps for core (stdlib only: struct, sqlite3, json)

[project.optional-dependencies]
json-schema = ["jsonschema>=4.20"]
dev = ["pytest>=8.0", "pytest-cov", "hypothesis", "ruff", "mypy"]

[project.scripts]
omw = "omwtools.cli.main:main"
```

---

## Testing Strategy

**Unit tests** (`tests/unit/`):
- `test_refid_codec.py` — all 7 RefId types × 2 format versions; edge cases (empty, long string, exterior cell)
- `test_record_parsing.py` — for each record type: construct minimal raw bytes, assert parsed fields
- `test_npc_encode.py` — build NPC dataclass, encode, re-parse, compare field-by-field
- `test_cell_refs.py` — CELL with 3 FRMR references, encode + re-parse
- `test_db_schema.py` — `make_db()` succeeds, all tables exist
- `test_omwscripts.py` — parse/render round-trip for all flag/type combinations

**Integration tests** (`tests/integration/`):
- `test_roundtrip.py` — load real `.esm` (path from env var), write, compare non-LAND records byte-for-byte. `pytest.mark.skipif` if file unavailable.
- `test_cli.py` — subprocess invocations against fixture ESM files
- `test_json_roundtrip.py` — export → import → write → compare

**Property tests** (`tests/property/`):
- `hypothesis`-generated random NPC data: encode → decode → assert equality
- RefId identity property: `decode(encode(x)) == x` for all subtypes

**Fixtures** (`tests/fixtures/`):
- `minimal.esm` — TES3 header only (hand-crafted binary)
- `npc_test.esm` — 3 NPC records with known field values
- `cell_test.esm` — 1 interior cell with 2 references

---

## Phased Milestones

### Phase 1 — Working Prototype
1. `io/codec.py`, `io/refid.py`, `io/reader.py` + unit tests
2. `records/base.py`, `records/tes3.py`, `db/schema.py`, `db/store.py` (basic insert) + `omw load`, `omw info`
   → All records stored as `UnknownRecord` BLOBs; file fully loadable
3. `records/npc_.py`, `records/cell.py`, `records/scpt.py`, `records/lual.py` + typed DB inserts
4. `io/writer.py` + `omw write` → NPC roundtrip verified
5. `omwscripts/` module + `omw scripts load/dump`

**Milestone check**: `omw load Morrowind.esm && omw query "SELECT * FROM npcs LIMIT 5" --json`

### Phase 2 — Full Record Coverage
5. Tier 2 records: SPEL, ENCH, ALCH, WEAP, ARMO, CLOT, INGR, BOOK, MISC, LIGH, DOOR, CONT, ACTI, STAT
6. DIAL + INFO (with condition parsing); RACE, FACT, CLAS, BSGN
7. `json_io/` module + `omw export`, `omw import`, `omw dump`
8. LEVC, LEVI, REGN, SNDG, SOUN, LTEX, GLOB, GMST, MGEF, SKIL + `omw validate`

**Milestone check**: Full ESM → JSON → ESM roundtrip; output loads in OpenMW

### Phase 3 — Completion
9. LAND, PGRD, CREA + terrain blob handling
10. Remaining records: LOCK, PROB, REPA, APPA, SSCR + schema migrations
11. Performance: bulk `executemany` inserts, streaming LAND parse, `--batch-size` option
12. Packaging, CI (GitHub Actions, Python 3.11–3.13 matrix), PyPI publish
