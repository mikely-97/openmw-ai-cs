# openmw-ai-cs

Python library and CLI for reading, writing, and programmatically editing OpenMW content files (`.omwgame`, `.omwaddon`, `.omwscripts`, `.esm`, `.esp`).

Built around **SQLite as primary storage** and **JSON for import/export**, so content can be queried with SQL, edited in any text editor, and fed to AI agents without touching the GUI editor.

---

## Background: OpenMW Content Files

OpenMW uses a binary format (ESM3) for game content. The file extensions are just conventions — all four are the same binary format:

| Extension | Equivalent to | Role |
|-----------|--------------|------|
| `.omwgame` | `.esm` | Game master file — no parent masters |
| `.omwaddon` | `.esp` | Plugin/addon — may reference master files |
| `.esm` | `.omwgame` | Same format, older convention |
| `.esp` | `.omwaddon` | Same format, older convention |

`.omwscripts` is a **completely different text format** — a manifest of Lua scripts. It is loaded as a separate `content=` entry in `openmw.cfg`.

### The Example Suite

The [OpenMW Example Suite](https://openmw.readthedocs.io/en/stable/reference/modding/openmw-game-template.html) lets you run OpenMW without owning Morrowind. It ships:

- `game_template/data/template.omwgame` — minimal base assets (player mesh, sky, UI)
- `the_hub/data/the_hub.omwaddon` — a small hub world with NPCs and doors
- `example_animated_creature/data/landracer.omwaddon` — an animated creature example
- `integration_tests/data/mwscript.omwaddon` — MWScript test content

**openmw.cfg for the example suite** (minimal):
```
data="/path/to/example-suite/game_template/data"
data="/path/to/example-suite/the_hub/data"
content=template.omwgame
content=the_hub.omwaddon
```

**settings.cfg** — the template requires pointing all animation model keys at `meshes/BasicPlayer.dae` (see `example-suite/settings.cfg` for the full list).

---

## Installation

Requires Python ≥ 3.11. Uses [Poetry](https://python-poetry.org/) for dependency management.

```bash
cd omwtools/
poetry install
```

This installs the `omw` CLI entry point.

For development tools (linting, type checking, tests):
```bash
poetry install --with dev
```

---

## Quick Start

### Load a content file and inspect it

```bash
# Load into a persistent SQLite database
omw --db mymod.db load the_hub.omwaddon

# List what was loaded
omw --db mymod.db info

# Query NPCs directly with SQL
omw --db mymod.db query "SELECT record_id_text, name FROM npcs LIMIT 10"

# Export all NPC records to JSON
omw --db mymod.db export --rec-type NPC_ --output npcs.json
```

### Edit and write back

```bash
# Edit npcs.json in any editor or script, then import changes
omw --db mymod.db import npcs.json --mod-id 1

# Write the modified content back to binary
omw --db mymod.db write --output my_modified.omwaddon --mod-id 1
```

### Python API

```python
import sqlite3
from omwtools.db.store import ModStore
from omwtools.db.schema import apply_schema
from omwtools.cli.cmd_write import write_mod

conn = sqlite3.connect("mymod.db")
conn.row_factory = sqlite3.Row
apply_schema(conn)

store = ModStore(conn)
mod_id = store.load_file("the_hub.omwaddon")
conn.commit()

# Query
rows = conn.execute("SELECT * FROM npcs").fetchall()
for r in rows:
    print(r["name"], r["record_id_text"])

# Write binary output
write_mod(conn, mod_id, "output.omwaddon")
conn.close()
```

---

## CLI Reference

Global options apply to every command:

```
omw [--db PATH] [--json] COMMAND
```

- `--db PATH` — SQLite database to use. Default: `:memory:` (data lost after command).
  For any real workflow, always specify a file path.
- `--json` — Force JSON output to stdout even for non-JSON commands.

### `omw load`

Load one or more ESM/omwgame/omwaddon files into the database.

```bash
omw --db mod.db load FILE [FILE ...]
omw --db mod.db load template.omwgame the_hub.omwaddon
```

Options:
- `--encoding` — String encoding (default: `cp1252`). Vanilla Morrowind content uses cp1252.
- `--lenient` — Log warnings instead of raising on malformed records.

Each file becomes one `mod_id` in the database. Multiple files loaded into the same DB are independent mods with separate `mod_id` values.

Output (JSON):
```json
[{"file": "the_hub.omwaddon", "mod_id": 1, "status": "ok"}]
```

### `omw info`

Show metadata for loaded mods.

```bash
omw --db mod.db info
omw --db mod.db info --mod-id 1
```

### `omw dump`

Dump records as JSON to stdout (or a file).

```bash
# All records in a mod
omw --db mod.db dump --mod-id 1

# All NPC records
omw --db mod.db dump --rec-type NPC_

# One specific record by ID
omw --db mod.db dump --rec-type NPC_ --id "caius cosades"

# To file
omw --db mod.db dump --output records.json
```

Record IDs are stored **lowercase** (case-insensitive matching). Use lowercase when filtering.

### `omw export`

Export records to a JSON file. Same filtering options as `dump`, but `--output` is required.

```bash
omw --db mod.db export --output all_npcs.json --rec-type NPC_ --mod-id 1
```

### `omw import`

Import records from a previously exported JSON file. Requires `--mod-id`.

```bash
omw --db mod.db import modified_npcs.json --mod-id 1
```

The JSON must contain an array of record dicts matching the export format. Unknown fields are ignored. Records are matched by `record_id` and upserted.

### `omw query`

Execute arbitrary SQL against the database. Returns JSON.

```bash
# List all weapons with their enchantment IDs
omw --db mod.db query "SELECT record_id_text, name, enchantment FROM typed_records
  JOIN records ON typed_records.record_id = records.id
  WHERE records.rec_type = 'WEAP' LIMIT 20"

# NPCs with gold > 100
omw --db mod.db query "SELECT record_id_text, gold FROM npcs WHERE gold > 100"

# Cells with refs count
omw --db mod.db query "SELECT c.cell_name, COUNT(r.id) as ref_count
  FROM cells c JOIN cell_refs r ON r.cell_id = c.record_id
  GROUP BY c.cell_name ORDER BY ref_count DESC LIMIT 10"
```

### `omw write`

Write a mod back to binary ESM format.

```bash
omw --db mod.db write --output output.omwaddon --mod-id 1

# Force a specific format version (default: preserve the source file's version)
omw --db mod.db write --output output.omwaddon --mod-id 1 --format-version 0
```

The output extension (`.esm`, `.esp`, `.omwgame`, `.omwaddon`) is cosmetic — the binary format is identical.

**Format versions:**
- `0` — Old string RefIds (compatible with vanilla Morrowind and the example suite)
- `1` — New typed RefIds (default for fresh OpenMW-only content)

If `--format-version` is not specified, the source file's own format version is preserved.

### `omw validate`

Run basic validation checks on loaded records.

```bash
omw --db mod.db validate --mod-id 1
```

Currently checks: MGEF coverage (143 magic effects), SKIL coverage (27 skills).

### `omw scripts load` / `omw scripts dump`

Load and inspect `.omwscripts` Lua manifest files.

```bash
omw --db mod.db scripts load mymod.omwscripts
omw --db mod.db scripts dump
```

`.omwscripts` files are text format — completely separate from the binary ESM format. Each non-comment line:
```
FLAG1, FLAG2, TYPE1 : scripts/mymod/main.lua
```

Valid flags: `GLOBAL`, `CUSTOM`, `PLAYER`, `MENU`
Valid types: `ACTIVATOR`, `ARMOR`, `BOOK`, `CLOTHING`, `CONTAINER`, `CREATURE`, `DOOR`,
`INGREDIENT`, `LIGHT`, `MISC_ITEM`, `NPC`, `POTION`, `WEAPON`, `APPARATUS`, `LOCKPICK`,
`PROBE`, `REPAIR`

---

## SQLite Schema Overview

The database uses typed satellite tables for known record types, plus a fallback `raw_blob` column for unknown types (guaranteeing pass-through fidelity for any record type not in the registry).

**Core tables:**

| Table | Contents |
|-------|----------|
| `mods` | One row per loaded file (mod_id, filename, format_version, author, description) |
| `master_files` | Master file dependencies per mod |
| `records` | Universal index — every record has a row here (rec_type, record_id_text, flags, sort_order, raw_blob) |

**Satellite tables** (one per record type, foreign-keyed to `records.id`):

| Table(s) | Record types |
|----------|-------------|
| `npcs`, `npc_inventory`, `npc_spells`, `npc_ai_packages`, `npc_transport` | NPC_ |
| `cells`, `cell_refs` | CELL |
| `scripts` | SCPT |
| `lua_script_cfgs`, `lua_script_entries` | LUAL |
| `typed_records` | All Phase 2 types (WEAP, ARMO, SPEL, ENCH, ALCH, CONT, CREA, DIAL, INFO, RACE, FACT, CLAS, BSGN, GLOB, GMST, SKIL, MGEF, REGN, SOUN, SNDG, LTEX, INGR, BOOK, CLOT, MISC/LOCK/PROB/REPA/APPA, LIGH, DOOR/ACTI/STAT, LEVC, LEVI, LAND, PGRD, SSCR) |
| `dialogue_infos` | INFO (linked to parent DIAL topic) |

**RefId encoding in the database:**

RefIds are stored as canonical text strings. The encoding distinguishes all RefId types:

| DB text | Meaning |
|---------|---------|
| `""` (empty) | `EmptyRefId` — subrecord was absent |
| `":"` | `StringRefId("")` — subrecord was present with empty string |
| `"caius cosades"` | `StringRefId` — lowercased string |
| `"FormId:0x00000001:0"` | `FormIdRefId` |
| `"Generated:0x0000000000000001"` | `GeneratedRefId` |
| `"Index:SKIL:3"` | `IndexRefId` |
| `"Esm3ExteriorCell:2:-4"` | `ESM3ExteriorCellRefId` |

---

## Supported Record Types (39)

| Record type | Class | Notes |
|-------------|-------|-------|
| `TES3` | `TES3Header` | File header — always first |
| `NPC_` | `NPC` | Full satellite tables |
| `CELL` | `Cell` | Full satellite tables including cell refs, DODT/DNAM |
| `SCPT` | `Script` | MWScript bytecode + source |
| `LUAL` | `LUALRecord` | Lua script configuration (binary form of .omwscripts) |
| `SPEL` | `Spell` | |
| `ENCH` | `Enchantment` | |
| `ALCH` | `Potion` | |
| `INGR` | `Ingredient` | |
| `WEAP` | `Weapon` | |
| `ARMO` | `Armour` | Includes body part table |
| `CLOT` | `Clothing` | |
| `BOOK` | `Book` | |
| `MISC` | `MiscItem` | |
| `LOCK` | `Lockpick` | |
| `PROB` | `Probe` | |
| `REPA` | `RepairItem` | |
| `APPA` | `Apparatus` | |
| `LIGH` | `Light` | |
| `DOOR` | `Door` | |
| `ACTI` | `Activator` | |
| `STAT` | `Static` | |
| `CONT` | `Container` | |
| `CREA` | `Creature` | |
| `DIAL` | `Dialogue` | |
| `INFO` | `DialogueInfo` | Linked to parent DIAL; PNAM/NNAM rebuilt from sort order |
| `RACE` | `Race` | |
| `BSGN` | `Birthsign` | |
| `FACT` | `Faction` | |
| `CLAS` | `Class` | |
| `GLOB` | `GlobalVariable` | |
| `GMST` | `GameSetting` | |
| `SKIL` | `Skill` | |
| `MGEF` | `MagicEffect` | |
| `REGN` | `Region` | |
| `SOUN` | `Sound` | |
| `SNDG` | `SoundGenerator` | |
| `LTEX` | `LandTexture` | |
| `LEVC` | `LevelledCreature` | |
| `LEVI` | `LevelledItem` | |
| `LAND` | `Land` | Terrain blob |
| `PGRD` | `Pathgrid` | |
| `SSCR` | `StartupScript` | |
| *(any other)* | `UnknownRecord` | Stored as raw blob — guaranteed pass-through |

---

## Known Binary Format Gotchas

These apply when creating content directly; `omwtools` handles them internally.

**Subrecord sizes are strict** — the engine crashes on wrong sizes:
- `CELL/DATA` — exactly 12 bytes (cell header) or 24 bytes (object position)
- `CONT/FLAG` — bit 3 (`0x08`) must always be set, even for plain containers
- `NPC_/NPDT` — 52 bytes (full stats) or 12 bytes (autocalc, when flag `0x0008` is set)
- `NPC_/AIDT` — exactly 12 bytes
- `LIGH/LHDT` — exactly 24 bytes
- `SCPT/SCHD` — exactly 52 bytes; `SCDT` must be present (may be empty)
- `INFO/DATA` — exactly 12 bytes; use `-1` for npc_rank/gender/pc_rank to mean "any"

**Paths omit the leading directory prefix** — the engine adds `meshes/` and `icons/` automatically. `MODL` stores `x/myobj.dae`, not `meshes/x/myobj.dae`.

**`CELL/AMBI` color order** — bytes are `[R, G, B, A]`. Use `struct.pack("<BBBB", r, g, b, a)`, not `struct.pack("<I", rgba_int)` (that reverses the byte order).

**IDs are case-insensitive** — always use lowercase for new IDs. `omwtools` stores them lowercase in the DB.

**DIAL/INFO ordering** — `INFO` records must appear after their parent `DIAL` in the file. `omwtools` handles this automatically via `sort_order`.

**MWScript**: `SetAttribute`/`SetSkill` are not valid MWScript commands — use `ModAttribute`/`ModSkill`. An invalid command silently disables the entire script at runtime with no error shown.

**Player spawn** is controlled by the `EnableMenus` MWScript, not the `sStartCell` GMST alone. Override `EnableMenus` to change the spawn cell.

---

## Development

```bash
cd omwtools/

# Run all tests
poetry run pytest -x -q

# Run with coverage
poetry run pytest --cov=omwtools

# Linting
poetry run ruff check .

# Type checking
poetry run mypy omwtools/
```

**Test fixtures** (`tests/fixtures/`) are hand-crafted binary ESM files generated by `make_fixtures.py`. They are committed to the repo so tests run without any external files.

**Roundtrip validation** — all four example-suite files produce byte-exact output:

```bash
# Load, then write back and compare sizes
omw --db /tmp/t.db load template.omwgame && omw --db /tmp/t.db write --output /tmp/out.omwgame --mod-id 1
```

---

## Data Pipeline

```
ESM binary (.esm / .esp / .omwgame / .omwaddon)
  ──► ESMReader.iter_records()       RawRecord stream
  ──► parse_record(raw, fmt_version) typed BaseRecord objects
  ──► ModStore.load_file()           SQLite rows (satellite tables)
         ↕  (SQL queries / JSON import-export / AI agent edits)
  ──► _export_from_satellite()       typed dict (JSON-serializable)
  ──► BaseRecord.from_dict()         typed BaseRecord objects
  ──► ESMWriter.write_record()       ESM binary

.omwscripts (text)
  ──► parse_omwscripts(text)         list[ScriptEntry]
  ──► ModStore.load_omwscripts_file() SQLite rows
         ↕
  ──► render_omwscripts(entries)     .omwscripts text
```

Unknown record types flow through `UnknownRecord` → stored as `raw_blob` in `records` table → written back verbatim. No information is lost for any record type.
