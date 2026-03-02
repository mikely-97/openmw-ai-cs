# openmw-ai-cs

A toolchain for generating complete OpenMW game content programmatically — no GUI editor required.

Two tools work together to cover the full pipeline:

| Tool | What it does |
|------|-------------|
| [`asset-forge/`](asset-forge/) | Generates 3D meshes, PBR textures, inventory icons, and sound effects from a text description |
| [`omwtools/`](omwtools/) | Reads, writes, and queries OpenMW binary content files (`.omwgame`, `.omwaddon`, `.esm`, `.esp`) |

---

## Combined pipeline

```
Text description + record type
  ──► forge generate WEAP "An ancient elven longsword"
        │
        ├── Stable Diffusion     → reference image, PBR texture, inventory icon
        ├── Hunyuan3D            → COLLADA mesh (.dae)
        ├── Blender              → UV-unwrap, texture application, sanitize
        ├── AudioCraft           → sound effects (.wav)  [optional]
        └── manifest.json        → asset paths + ESM record field defaults
                │
                ▼
  omw --db mod.db import <manifest-derived JSON> --mod-id 1
  omw --db mod.db write  --output my_mod.omwaddon --mod-id 1
        │
        ▼
  my_mod.omwaddon   ← load into OpenMW alongside the generated assets
```

`asset-forge` produces the physical files and a `manifest.json` with suggested record field values
(name, weight, value, mesh path, texture path, …). `omwtools` takes those values and writes them
into the binary ESM format that OpenMW loads.

---

## Tools

### `asset-forge` — AI-powered asset generation

Converts a record type and a text description into a complete asset bundle:

```bash
cd asset-forge/
poetry install
forge generate CONT "A heavy iron strongbox with a combination lock wheel"
```

Output:

```
output/iron_strongbox/
├── iron_strongbox.dae        COLLADA mesh (textured, triangulated, Z-up)
├── iron_strongbox_d.png      PBR diffuse texture
├── iron_strongbox.png        Inventory icon (128×128, RGBA)
└── manifest.json             ESM record field defaults + asset paths
```

Requires: NVIDIA GPU (CUDA 12.1+, ≥12 GB VRAM), Blender 3.6+, Stable Diffusion WebUI, Hunyuan3D-2.

Full documentation: [asset-forge/README.md](asset-forge/README.md)

**Supported record types (19):**

| Category | Types |
|---|---|
| Static world objects | `STAT`, `ACTI`, `CONT`, `DOOR` |
| Light sources | `LIGH` |
| Inventory items | `MISC`, `BOOK`, `ALCH`, `INGR` |
| Tools | `LOCK`, `PROB`, `APPA`, `REPA` |
| Weapons | `WEAP` |
| Armour / clothing | `ARMO`, `CLOT` |
| Terrain | `LTEX` |
| Characters | `NPC_`, `CREA`, `BODY` |

---

### `omwtools` — ESM content file I/O

Reads, writes, and queries OpenMW binary content files. Uses SQLite as primary storage and JSON
for import/export, so content can be queried with SQL, edited with any tool, and written back to
binary without touching the GUI editor.

```bash
cd omwtools/
poetry install

# Load a content file
omw --db mod.db load the_hub.omwaddon

# Query records directly
omw --db mod.db query "SELECT record_id_text, name FROM npcs LIMIT 10"

# Export, edit, import, write back
omw --db mod.db export --rec-type NPC_ --output npcs.json
# edit npcs.json
omw --db mod.db import npcs.json --mod-id 1
omw --db mod.db write --output my_modified.omwaddon --mod-id 1
```

Requires: Python ≥ 3.11, Poetry. Zero external dependencies for the core library.

Full documentation: [omwtools/README.md](omwtools/) *(see below)*

**Supported record types (39):** TES3, NPC_, CELL, SCPT, LUAL, SPEL, ENCH, ALCH, INGR, WEAP,
ARMO, CLOT, BOOK, MISC, LOCK, PROB, REPA, APPA, LIGH, DOOR, ACTI, STAT, CONT, CREA, DIAL, INFO,
RACE, BSGN, FACT, CLAS, GLOB, GMST, SKIL, MGEF, REGN, SOUN, SNDG, LTEX, LEVC, LEVI, LAND, PGRD,
SSCR — plus `UnknownRecord` pass-through for anything else.

---

## Installation

Each tool is an independent Poetry project. Install them separately:

```bash
# Asset generation
cd asset-forge/
poetry install          # core pipeline
# For audio support (requires CUDA PyTorch first):
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
# poetry install -E audio

# Content file I/O
cd omwtools/
poetry install
poetry install --with dev   # adds pytest, ruff, mypy
```

---

## Workflow: generating a full game

A rough end-to-end workflow for creating content from scratch:

### 1. Generate assets

```bash
cd asset-forge/
# Generate all the physical files for a record
forge generate WEAP "A bone-handled hunting knife with a serrated edge"
# → output/bone_handled_hunting_knife/  (mesh, texture, icon, manifest.json)
```

### 2. Create or load a mod

```bash
cd omwtools/
# Start from a blank mod, or load an existing one
omw --db mymod.db load template.omwgame   # optional base to work from
```

### 3. Import the record

Using the ESM field defaults from `manifest.json`, build a record JSON and import it:

```bash
# Write a minimal WEAP record JSON using the manifest defaults, then:
omw --db mymod.db import weapon.json --mod-id 1
```

### 4. Write to binary

```bash
omw --db mymod.db write --output mymod.omwaddon --mod-id 1
```

### 5. Drop assets into the data directory

Copy the mesh, texture, and icon from `asset-forge/output/<object_id>/` into the game's
`Data Files/meshes/` and `Data Files/textures/` and `Data Files/icons/` directories.
The `manifest.json` `openmw_paths` block shows the exact paths each ESM field should contain.

---

## OpenMW content file format

All four extensions are the same binary ESM3 format:

| Extension | Equivalent to | Role |
|-----------|--------------|------|
| `.omwgame` | `.esm` | Game master file — no parent masters |
| `.omwaddon` | `.esp` | Plugin/addon — may reference master files |
| `.esm` | `.omwgame` | Same format, older convention |
| `.esp` | `.omwaddon` | Same format, older convention |

`.omwscripts` is a **completely different text format** — a manifest of Lua scripts loaded as a
separate `content=` entry in `openmw.cfg`.

---

## omwtools — full reference

### Installation

```bash
cd omwtools/
poetry install
```

### Quick start

```bash
omw --db mymod.db load the_hub.omwaddon
omw --db mymod.db info
omw --db mymod.db query "SELECT record_id_text, name FROM npcs LIMIT 10"
omw --db mymod.db export --rec-type NPC_ --output npcs.json
omw --db mymod.db import npcs.json --mod-id 1
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

rows = conn.execute("SELECT * FROM npcs").fetchall()
for r in rows:
    print(r["name"], r["record_id_text"])

write_mod(conn, mod_id, "output.omwaddon")
conn.close()
```

### CLI reference

Global options:

```
omw [--db PATH] [--json] COMMAND
```

- `--db PATH` — SQLite database. Default: `:memory:` (in-session only). Always specify a file for real work.
- `--json` — Force JSON output.

#### `omw load`

```bash
omw --db mod.db load FILE [FILE ...]
omw --db mod.db load template.omwgame the_hub.omwaddon
```

Options: `--encoding` (default `cp1252`), `--lenient` (warn instead of raise on malformed records).

#### `omw dump`

```bash
omw --db mod.db dump --mod-id 1
omw --db mod.db dump --rec-type NPC_ --id "caius cosades"
omw --db mod.db dump --output records.json
```

#### `omw export`

Same filters as `dump`; `--output` is required.

```bash
omw --db mod.db export --output all_npcs.json --rec-type NPC_ --mod-id 1
```

#### `omw import`

```bash
omw --db mod.db import modified_npcs.json --mod-id 1
```

#### `omw query`

```bash
omw --db mod.db query "SELECT record_id_text, name FROM npcs WHERE gold > 100"
omw --db mod.db query "SELECT c.cell_name, COUNT(r.id) as ref_count
  FROM cells c JOIN cell_refs r ON r.cell_id = c.record_id
  GROUP BY c.cell_name ORDER BY ref_count DESC LIMIT 10"
```

#### `omw write`

```bash
omw --db mod.db write --output output.omwaddon --mod-id 1
# Force format version (0 = old string RefIds, 1 = new typed RefIds):
omw --db mod.db write --output output.omwaddon --mod-id 1 --format-version 0
```

#### `omw validate`

```bash
omw --db mod.db validate --mod-id 1
```

Checks MGEF coverage (143 magic effects) and SKIL coverage (27 skills).

#### `omw scripts load` / `omw scripts dump`

```bash
omw --db mod.db scripts load mymod.omwscripts
omw --db mod.db scripts dump
```

### SQLite schema

| Table | Contents |
|-------|----------|
| `mods` | One row per loaded file |
| `master_files` | Master file dependencies per mod |
| `records` | Universal index — every record (rec_type, record_id_text, flags, sort_order, raw_blob) |
| `npcs`, `npc_inventory`, `npc_spells`, `npc_ai_packages`, `npc_transport` | NPC_ satellite |
| `cells`, `cell_refs` | CELL satellite |
| `scripts` | SCPT |
| `lua_script_cfgs`, `lua_script_entries` | LUAL |
| `typed_records` | All Phase 2 types (JSON in `data_json` column) |
| `dialogue_infos` | INFO (linked to parent DIAL) |

**RefId encoding:**

| DB text | Meaning |
|---------|---------|
| `""` | `EmptyRefId` — subrecord absent |
| `":"` | `StringRefId("")` — subrecord present, empty string |
| `"caius cosades"` | `StringRefId` — lowercased |
| `"FormId:0x00000001:0"` | `FormIdRefId` |
| `"Generated:0x0000000000000001"` | `GeneratedRefId` |
| `"Index:SKIL:3"` | `IndexRefId` |
| `"Esm3ExteriorCell:2:-4"` | `ESM3ExteriorCellRefId` |

### Data pipeline

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

Unknown record types flow through `UnknownRecord` → stored as `raw_blob` → written back verbatim.

### Known binary format gotchas

**Subrecord sizes are strict** (engine crashes on wrong sizes):
- `CELL/DATA` — 12 bytes (cell header) or 24 bytes (object position)
- `NPC_/NPDT` — 52 bytes (full stats) or 12 bytes (autocalc, flag `0x0008` set)
- `LIGH/LHDT` — exactly 24 bytes
- `SCPT/SCHD` — exactly 52 bytes; `SCDT` must be present (may be empty)
- `INFO/DATA` — exactly 12 bytes; use `-1` for npc_rank/gender/pc_rank to mean "any"

**Paths omit the leading directory prefix** — the engine adds `meshes/` and `icons/` automatically.
Store `x/myobj.dae`, not `meshes/x/myobj.dae`.

**DIAL/INFO ordering** — `INFO` records must appear after their parent `DIAL`. Handled automatically.

**IDs are case-insensitive** — always use lowercase for new IDs.

### Development

```bash
cd omwtools/
poetry run pytest -x -q         # 65 tests, all passing
poetry run pytest --cov=omwtools
poetry run ruff check .
poetry run mypy omwtools/
```

---

## Project status

| Component | Status |
|-----------|--------|
| `omwtools` Phase 1 (TES3, NPC_, CELL, SCPT, LUAL) | Complete — 56 tests |
| `omwtools` Phase 2 (39 record types total) | Complete — 65 tests passing |
| `omwtools` roundtrip fidelity | Verified — all 4 example-suite files at delta=0 |
| `asset-forge` | v0.1.0 — full pipeline implemented |
| Combined forge → omw workflow | Documented; integration tooling TBD |
