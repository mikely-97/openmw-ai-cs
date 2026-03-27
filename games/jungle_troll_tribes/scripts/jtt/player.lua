local core = require('openmw.core')
local self = require('openmw.self')
local ui = require('openmw.ui')
local types = require('openmw.types')

local spawned = false

local DUNGEON_ACTIVATORS = {
    jtt_bear_den_entrance = "bear_den",
    -- add spider_cave and troll_lair when those activators are placed in world
}

local function onActivate(object, activator)
    local id = tostring(object.recordId):lower()
    if id == "jtt_dungeon_exit" then
        core.sendGlobalEvent("JTT_ExitDungeon", { cell_id = object.cell.name })
    elseif DUNGEON_ACTIVATORS[id] then
        core.sendGlobalEvent("JTT_EnterDungeon", { dungeon_type = DUNGEON_ACTIVATORS[id] })
    end
end

return {
    engineHandlers = {
        onKeyPress = function(key)
            if key.symbol == 'b' and not key.withShift and not key.withCtrl and not key.withAlt then
                core.sendGlobalEvent('JTT_Build', {})
            end
            if key.symbol == 'n' and not key.withShift and not key.withCtrl and not key.withAlt then
                core.sendGlobalEvent('JTT_Quest', {})
            end
            if key.symbol == 'h' and not key.withShift and not key.withCtrl and not key.withAlt then
                core.sendGlobalEvent('JTT_Status', {})
            end
        end,
        onUpdate = function(dt)
            if not spawned then
                spawned = true
                core.sendGlobalEvent('JTT_SpawnWorld', {})
            end
        end,
        onActivate = onActivate,
    }
}
