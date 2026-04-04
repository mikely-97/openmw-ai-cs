# JTT / openmw-ai-cs — Claude working guide

## Role

The human operator does not run scripts, paste logs, or copy files on Claude's behalf.
Claude has shell access and must do all of that itself. If something needs to be read,
built, searched, or validated — Claude does it.

---

## Hard protocols (no exceptions)

**When something is "not working": read `~/.config/openmw/openmw.log` before touching any code.**
Never guess at a root cause. The log tells you exactly what failed — Lua errors, missing records,
rejected activations. One read = one diagnosis = one fix.

**Before referencing any record ID in Lua: verify it exists.**
```bash
grep -r '"record_id": "jtt_spider"' games/jungle_troll_tribes/records/
```
If it returns nothing, the record does not exist. Create it first or fix the ID.

**Every non-trivial Lua branch must have a `print` call.**
Silent failures are invisible. Log at every fork so one test cycle = one diagnosis.
Never remove log lines — they're cheap and invaluable.

---

## Project layout

```
openmw-ai-cs/
  omwtools/               — ESM binary I/O tool (poetry run omw ...)
  games/jungle_troll_tribes/
    build.sh              — full build pipeline (run from omwtools/ dir)
    gen_meshes.py         — Blender script generating all placeholder .dae meshes
    jtt.omwscripts        — script bindings (PLAYER/GLOBAL tags)
    records/              — JSON source for all game records (imported in numeric order)
    scripts/jtt/          — Lua scripts (player.lua, global.lua, craft_menu.lua)
    scripts/jungle_troll_tribes/  — dungeon configs
    meshes/jtt/           — generated .dae meshes (output of gen_meshes.py)
```

## Build & launch

```bash
# From omwtools/:
bash games/jungle_troll_tribes/build.sh

# Launch (standalone — no Morrowind.esm):
flatpak run --command=openmw org.openmw.OpenMW --skip-menu --new-game
```

`openmw.cfg` must contain only:
```
content=jungle_troll_tribes.omwgame
content=jtt.omwscripts
```

Log: `~/.var/app/org.openmw.OpenMW/config/openmw/openmw.log` (flatpak install)

---

## Lua architecture

### jtt.omwscripts bindings
```
PLAYER: scripts/jtt/player.lua       — key bindings, onUpdate (world spawn trigger)
PLAYER: scripts/jtt/craft_menu.lua   — craft menu UI
GLOBAL: scripts/jtt/global.lua       — all game logic
```
`ACTIVATOR:` scripts are NOT used. All activation handling is in global.lua via:
```lua
interfaces.Activation.addHandlerForType(types.Activator, function(obj, actor)
    local rid = tostring(obj.recordId):lower()
    ...
    return false  -- prevents default C++ handling
end)
```

### global.lua event flow
- `JTT_SpawnWorld` — fired once on first onUpdate; spawns all biome objects
- Activation handler dispatches to: dungeon enter/exit, harvest nodes, crafting stations
- `JTT_Craft` — consumes ingredients, gives output (or spawns golem)
- `JTT_EnterDungeon` / `JTT_ExitDungeon` — teleport player, spawn/despawn dungeon contents
- `JTT_Notify` → forwarded to player.lua → `ui.showMessage`

### Key player bindings (player.lua)
| Key | Event |
|-----|-------|
| B | JTT_Build |
| N | JTT_Quest |
| H | JTT_Status |
| G | JTT_ResummonGolem |
| J | JTT_DebugMenuOpen |
| Shift+J | JTT_DebugSpawn (cycle cave parts) |
| Ctrl+J | JTT_DebugRemove |

---

## Active dungeon types
| Type | Surface activator | Config file |
|------|-------------------|-------------|
| bear_den | jtt_bear_den, jtt_cave_portal | dungeon_config_bear_den.lua |
| spider_cave | jtt_spider_cave | dungeon_config_spider_cave.lua |

Dungeon configs return a table:
```lua
{ variants=[{cell_id, entrance_pos, exit_exterior, anchors}], creatures, creatures_per_room, containers, loot_per_room }
```

---

## Record conventions (critical — re-read before writing new records)

- **Mesh paths**: NO `meshes\` prefix. `"jtt\\spider.dae"` not `"meshes\\jtt\\spider.dae"`.
- **Python mesh path escaping**: in Python source use ONE backslash: `r['mesh'] = 'jtt\\spider.dae'` → JSON `"jtt\\spider.dae"` → OpenMW `jtt/spider.dae`. Two backslashes (`'jtt\\\\spider.dae'`) → `jtt//spider.dae` → broken.
- **Dungeon JSON files** must have numeric prefixes (e.g. `20_dungeons_bear_den.json`) — build.sh only imports `[0-9]*.json`.
- **Lua logging**: use `print()`, not `util.log()`. `util.log` is nil in global script context.
- **CONT records**: `cont_flags: 8` always (bit 0x08 = normal container).
- **CREA inventory**: key is `"item"` not `"item_id"`. NPC_ inventory uses `"item_id"`.
- **AI_W raw_hex**: must be 28 hex chars (14 bytes). Append `00` if 26 chars.
- **Sound paths**: NO `Sound\` prefix. OpenMW auto-prepends.
- **NPC hello**: always 0. `hello > 0` causes freeze in standalone games.
- **ACTI scripts**: leave `"script": ""` unless a MW script is specifically needed. MW scripts consume the OnActivate event before Lua sees it.

---

## Creatures that exist
`jtt_jungle_panther`, `jtt_giant_spider`, `jtt_jungle_bear`, `jtt_jungle_bird`,
`jtt_jungle_boar`, `jtt_jungle_croc`, `jtt_jungle_elk`, `jtt_jungle_rabbit`,
`jtt_jungle_snake`, `jtt_jungle_tiger`, `jtt_jungle_tortoise`, `jtt_jungle_wolf`,
`jtt_raccoon`, `jtt_golem`, `jtt_spider`

---

## Diagnosing failures

### Lua script not running
Check log for: `Not supported handler` or `unknown identifier` or `attempt to call`.

### Record not loading
Check log for: `Cell reference "X" is not found` or `Failed to load mesh`.

### Activation doing nothing
Add to the handler: `print("JTT: activation rid=" .. rid)`
Then check log after clicking the object.

### Dungeon entry failing
Add: `print("JTT: enterDungeon type=" .. typeName .. " cfg=" .. tostring(cfg))`
Common causes: dungeon config not found (require path wrong), creature ID doesn't exist.

---

## What OpenMW handles natively (don't implement)
- Player death and respawn
- Inventory UI
- NPC combat AI
- Save/load
