local world = require('openmw.world')
local util = require('openmw.util')

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

local function spawnBiome(cx, cy, z, biomeType)
    placed = {}
    table.insert(placed, {x=cx, y=cy})

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

return {
    eventHandlers = {
        JTT_Build = onJTTBuild,
        JTT_Quest = onJTTQuest,
        JTT_Status = onJTTStatus,
        JTT_Eat = onJTTEat,
        JTT_SpawnWorld = onJTTSpawnWorld,
    }
}
