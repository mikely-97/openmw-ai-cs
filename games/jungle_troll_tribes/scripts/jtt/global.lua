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

-- Spawn objects at specific world positions with collision avoidance
local placed = {}  -- track placed positions

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

local function placeObject(recordId, x, y, z, count)
    count = count or 1
    local obj = world.createObject(recordId, count)
    obj:teleport('', util.vector3(x, y, z))
    table.insert(placed, {x=x, y=y})
    return obj
end

local function randomInRange(min, max)
    return min + math.random() * (max - min)
end

local function spawnBiome(cx, cy, z)
    -- cx, cy = cell center world coords
    local nodes = {
        {id='jtt_wood_node', count=2},
        {id='jtt_stone_node', count=2},
        {id='jtt_herb_node', count=2},
        {id='jtt_iron_deposit', count=1},
        {id='jtt_fast_travel', count=1},
    }

    placed = {}
    -- Reserve center area (player spawn)
    table.insert(placed, {x=cx, y=cy})

    for _, node in ipairs(nodes) do
        for i = 1, node.count do
            -- Try up to 20 times to find a clear spot
            for attempt = 1, 20 do
                local x = randomInRange(cx - 3000, cx + 3000)
                local y = randomInRange(cy - 3000, cy + 3000)
                if isClear(x, y, 400) then
                    placeObject(node.id, x, y, z)
                    break
                end
            end
        end
    end
end

local worldSpawned = false

local function onJTTSpawnWorld(data)
    if worldSpawned then return end
    worldSpawned = true

    local z = 1600

    -- Base Camp (0,0) — also place workbench + campfire
    spawnBiome(4096, 4096, z)
    placeObject('jtt_workbench', 4096 + 250, 4096 + 100, z)
    placeObject('jtt_campfire', 4096 - 200, 4096 + 150, z)

    -- East Jungle (1,0)
    spawnBiome(8192 + 4096, 4096, z)

    -- North Ridge (0,1)
    spawnBiome(4096, 8192 + 4096, z)

    -- West Shore (-1,0)
    spawnBiome(-8192 + 4096, 4096, z)

    -- South Marsh (0,-1)
    spawnBiome(4096, -8192 + 4096, z)
end

return {
    eventHandlers = {
        JTT_Build = onJTTBuild,
        JTT_Quest = onJTTQuest,
        JTT_SpawnWorld = onJTTSpawnWorld,
    }
}
