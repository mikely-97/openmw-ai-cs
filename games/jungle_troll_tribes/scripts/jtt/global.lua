local core = require('openmw.core')
local world = require('openmw.world')
local util = require('openmw.util')

local DEBUG_CELL_ENTRANCES = {
    [0] = { cell='jtt_bear_den_0', x=2816.0, y=4864.0, z=50.0 },
    [1] = { cell='jtt_bear_den_1', x=1536.0, y=4608.0, z=50.0 },
    [2] = { cell='jtt_bear_den_2', x=2816.0, y=5632.0, z=50.0 },
    [3] = { cell='jtt_bear_den_3', x=5632.0, y=4608.0, z=50.0 },
    [4] = { cell='jtt_bear_den_4', x=1280.0, y=1280.0, z=50.0 },
    [5] = { cell='jtt_bear_den_5', x=1536.0, y=3584.0, z=50.0 },
    [6] = { cell='jtt_bear_den_6', x=1792.0, y=6144.0, z=50.0 },
    [7] = { cell='jtt_bear_den_7', x=1024.0, y=1280.0, z=50.0 },
}

local function onJTTBuild(data)
    local globals = world.mwscript.getGlobalVariables()
    globals.JTT_BuildMenu = 1
end

local function onJTTQuest(data)
    local globals = world.mwscript.getGlobalVariables()
    globals.JTT_QuestMenu = 1
end

local function onJTTStatus(data)
    local globals = world.mwscript.getGlobalVariables()
    globals.JTT_StatusMenu = 1
end

local function onJTTEat(data)
    local globals = world.mwscript.getGlobalVariables()
    globals.JTT_EatMenu = 1
end

-- ═══ WORLD SPAWNING ═══

local placed = {}

local function isClear(x, y, minDist)
    for _, p in ipairs(placed) do
        local dx = p.x - x
        local dy = p.y - y
        if math.sqrt(dx*dx + dy*dy) < minDist then
            return false
        end
    end
    return true
end

local function spawn(recordId, x, y, z, count)
    count = count or 1
    local obj = world.createObject(recordId, count)
    obj:teleport('', util.vector3(x, y, z))
    table.insert(placed, {x=x, y=y})
    return obj
end

local function randRange(min, max)
    return min + math.random() * (max - min)
end

local function spawnScattered(recordId, cx, cy, z, count, radius, minDist)
    minDist = minDist or 400
    for i = 1, count do
        for attempt = 1, 30 do
            local x = randRange(cx - radius, cx + radius)
            local y = randRange(cy - radius, cy + radius)
            if isClear(x, y, minDist) then
                spawn(recordId, x, y, z)
                break
            end
        end
    end
end

local uniqueNodes = {
    east  = 'jtt_spider_web',
    ridge = 'jtt_bear_den',
    shore = 'jtt_tidal_pool',
    marsh = 'jtt_mushroom_patch',
}

local function spawnBiome(cx, cy, z, biomeType)
    placed = {}
    table.insert(placed, {x=cx, y=cy})

    -- Unique biome harvest nodes (3 per biome)
    local uniqueNode = uniqueNodes[biomeType]
    if uniqueNode then
        spawnScattered(uniqueNode, cx, cy, z, 3, 2500, 400)
    end

    -- Herb patches (still clickable nodes) + iron veins (mineable)
    spawnScattered('jtt_herb_node', cx, cy, z, 3, 3000, 400)
    local ironCount = {jungle=1, east=1, ridge=3, shore=1, marsh=1}
    spawnScattered('jtt_iron_vein', cx, cy, z, ironCount[biomeType] or 1, 3000, 400)

    -- Portal
    spawn('jtt_fast_travel', cx + randRange(-500, 500), cy + randRange(-500, 500), z)

    -- Trees
    local trees = {
        jungle = {'jtt_tree_palm', 'jtt_tree_oak'},
        east   = {'jtt_tree_palm', 'jtt_tree_palm', 'jtt_tree_oak'},
        ridge  = {'jtt_tree_pine', 'jtt_tree_oak'},
        shore  = {'jtt_tree_palm'},
        marsh  = {'jtt_tree_dead', 'jtt_tree_palm'},
    }
    local treePool = trees[biomeType] or trees.jungle
    for i = 1, 150 do
        for attempt = 1, 20 do
            local x = randRange(cx - 3500, cx + 3500)
            local y = randRange(cy - 3500, cy + 3500)
            if isClear(x, y, 120) then
                local tree = treePool[math.random(#treePool)]
                spawn(tree, x, y, z)
                break
            end
        end
    end

    -- Rocks (mineable)
    local rockCount = {jungle=8, east=6, ridge=15, shore=5, marsh=4}
    local nRocks = rockCount[biomeType] or 8
    for i = 1, nRocks do
        for attempt = 1, 20 do
            local x = randRange(cx - 3500, cx + 3500)
            local y = randRange(cy - 3500, cy + 3500)
            if isClear(x, y, 200) then
                spawn('jtt_rock', x, y, z)
                break
            end
        end
    end

    -- Creatures
    local creatures = {
        jungle = {'jtt_jungle_boar', 'jtt_jungle_boar', 'jtt_jungle_bird', 'jtt_raccoon', 'jtt_jungle_rabbit'},
        east   = {'jtt_jungle_panther', 'jtt_giant_spider', 'jtt_giant_spider', 'jtt_jungle_snake', 'jtt_jungle_snake'},
        ridge  = {'jtt_jungle_bear', 'jtt_jungle_wolf', 'jtt_jungle_wolf', 'jtt_jungle_elk', 'jtt_jungle_elk'},
        shore  = {'jtt_jungle_croc', 'jtt_jungle_croc', 'jtt_jungle_tortoise', 'jtt_jungle_bird', 'jtt_raccoon'},
        marsh  = {'jtt_jungle_croc', 'jtt_giant_spider', 'jtt_jungle_snake', 'jtt_jungle_tiger', 'jtt_jungle_boar'},
    }
    local creaturePool = creatures[biomeType] or creatures.jungle
    for _, cid in ipairs(creaturePool) do
        for attempt = 1, 20 do
            local x = randRange(cx - 3500, cx + 3500)
            local y = randRange(cy - 3500, cy + 3500)
            if isClear(x, y, 300) then
                spawn(cid, x, y, z)
                break
            end
        end
    end

    -- Lying-around items (NO raw_meat - that's hunting only)
    local items = {'jtt_stick', 'jtt_stone_item', 'jtt_flint', 'jtt_tinder', 'jtt_jungle_berry'}
    for i = 1, 8 do
        local item = items[math.random(#items)]
        for attempt = 1, 20 do
            local x = randRange(cx - 3000, cx + 3000)
            local y = randRange(cy - 3000, cy + 3000)
            if isClear(x, y, 200) then
                spawn(item, x, y, z)
                break
            end
        end
    end
end

local function onJTTSpawnWorld(data)
    -- Use MW global to persist across save/load (but resets on new game)
    local globals = world.mwscript.getGlobalVariables()
    if globals.JTT_WorldSpawned == 1 then
        return
    end
    globals.JTT_WorldSpawned = 1

    local z = 16  -- normal terrain (base_height=2, 2*8=16)

    -- Base Camp (0,0)
    spawnBiome(4096, 4096, z, 'jungle')
    spawn('jtt_workbench', 4096 + 250, 4096 + 100, z)
    spawn('jtt_campfire', 4096 - 200, 4096 + 150, z)

    -- East Jungle (1,0)
    spawnBiome(8192 + 4096, 4096, z, 'east')

    -- North Ridge (0,1)
    spawnBiome(4096, 8192 + 4096, z, 'ridge')

    -- West Shore (-1,0)
    spawnBiome(-8192 + 4096, 4096, z, 'shore')

    -- South Marsh (0,-1) — at sea level
    spawnBiome(4096, -8192 + 4096, 4, 'marsh')
end

-- ============================================================
-- DUNGEON SYSTEM
-- ============================================================

local JTT_DungeonState = {}

local function loadDungeonConfig(typeName)
    local ok, dungeons_tbl = pcall(require, "scripts.jungle_troll_tribes.dungeon_config_" .. typeName)
    if not ok then
        util.log("JTT: dungeon config not found: " .. typeName)
        return nil
    end
    -- dungeons_tbl is JTT_Dungeons = { bear_den = { variants=..., creatures=... }, ... }
    return dungeons_tbl and dungeons_tbl[typeName] or nil
end

local function onJTTEnterDungeon(data)
    local typeName = data.dungeon_type
    local cfg = loadDungeonConfig(typeName)
    if not cfg then return end

    local variants = cfg.variants
    local idx = math.random(1, #variants)
    local variant = variants[idx]
    local player = world.players[1]

    local pos = util.vector3(variant.entrance_pos.x, variant.entrance_pos.y, variant.entrance_pos.z)
    player:teleport(variant.cell_id, pos, util.transform.identity)

    JTT_DungeonState[variant.cell_id] = { variant = variant, dungeon_type = typeName, spawned = {} }

    core.sendGlobalEvent("JTT_PopulateDungeon", {
        cell_id      = variant.cell_id,
        dungeon_type = typeName,
        anchors      = variant.anchors,
    })
end

local function onJTTPopulateDungeon(data)
    local cfg = loadDungeonConfig(data.dungeon_type)
    if not cfg then return end

    local cellId  = data.cell_id
    local anchors = data.anchors
    local state   = JTT_DungeonState[cellId]

    for _, anchor in ipairs(anchors) do
        local pos = util.vector3(anchor.x, anchor.y, anchor.z)

        if #cfg.creatures > 0 then
            local count = math.random(cfg.creatures_per_room[1], cfg.creatures_per_room[2])
            for _ = 1, count do
                local creatureId = cfg.creatures[math.random(1, #cfg.creatures)]
                local obj = world.createObject(creatureId, 1)
                local jitter = util.vector3(math.random(-2, 2), math.random(-2, 2), 0)
                obj:teleport(cellId, pos + jitter, util.transform.identity)
                if state then table.insert(state.spawned, obj) end
            end
        end

        if #cfg.containers > 0 then
            local roll = math.random(cfg.loot_per_room[1], cfg.loot_per_room[2])
            if roll > 0 then
                local contId = cfg.containers[math.random(1, #cfg.containers)]
                local lootObj = world.createObject(contId, 1)
                lootObj:teleport(cellId, pos + util.vector3(1.5, 0, 0), util.transform.identity)
                if state then table.insert(state.spawned, lootObj) end
            end
        end
    end
end

local debugObj = nil

local function onJTTEnterDungeonDirect(data)
    local player = world.players[1]
    player:teleport(data.cell, util.vector3(data.x, data.y, data.z), util.transform.identity)
end

local function onJTTDebugMenuOpen(data)
    local globals = world.mwscript.getGlobalVariables()
    globals.JTT_DebugMenu = 1
end

local function onJTTDebugSpawn(data)
    if debugObj and debugObj:isValid() then debugObj:remove() end
    local pos = world.players[1].position + util.vector3(0, 1200, 50)
    debugObj = world.createObject(data.part, 1)
    debugObj:teleport('', pos, util.transform.identity)
end

local function onJTTDebugRemove(data)
    if debugObj and debugObj:isValid() then debugObj:remove() end
    debugObj = nil
end

local function onJTTExitDungeon(data)
    local cellId = data.cell_id
    local state  = JTT_DungeonState[cellId]
    if not state then return end

    for _, obj in ipairs(state.spawned) do
        if obj and obj:isValid() then
            obj:remove()
        end
    end

    local ext    = state.variant.exit_exterior
    local player = world.players[1]
    local pos    = util.vector3(ext.x, ext.y, ext.z)
    local target = (ext.cell == "" or ext.cell == "default") and "" or ext.cell
    player:teleport(target, pos, util.transform.identity)

    JTT_DungeonState[cellId] = nil
end

return {
    engineHandlers = {
        onUpdate = function(dt)
            local globals = world.mwscript.getGlobalVariables()
            if globals.JTT_EnterCave == 1 then
                globals.JTT_EnterCave = 0
                onJTTEnterDungeon({ dungeon_type = 'bear_den' })
            end
            if globals.JTT_EnterCave == 2 then
                globals.JTT_EnterCave = 0
                local idx = math.floor(globals.JTT_DbgV)
                local cfg = DEBUG_CELL_ENTRANCES[idx]
                if cfg then
                    local player = world.players[1]
                    player:teleport(cfg.cell, util.vector3(cfg.x, cfg.y, cfg.z), util.transform.identity)
                end
            end
        end,
    },
    eventHandlers = {
        JTT_EnterDungeonDirect = onJTTEnterDungeonDirect,
        JTT_DebugMenuOpen    = onJTTDebugMenuOpen,
        JTT_DebugSpawn       = onJTTDebugSpawn,
        JTT_DebugRemove      = onJTTDebugRemove,
        JTT_Build            = onJTTBuild,
        JTT_Quest            = onJTTQuest,
        JTT_Status           = onJTTStatus,
        JTT_Eat              = onJTTEat,
        JTT_SpawnWorld       = onJTTSpawnWorld,
        JTT_EnterDungeon     = onJTTEnterDungeon,
        JTT_PopulateDungeon  = onJTTPopulateDungeon,
        JTT_ExitDungeon      = onJTTExitDungeon,
    }
}
