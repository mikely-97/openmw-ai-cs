local core = require('openmw.core')
local self = require('openmw.self')
local ui = require('openmw.ui')
local types = require('openmw.types')

local spawned = false

local DEBUG_PARTS = {
    "jtt_cave_room_a", "jtt_cave_room_b", "jtt_cave_room_c",
    "jtt_cave_room_d", "jtt_cave_room_e", "jtt_cave_room_f",
    "jtt_cave_room_g", "jtt_cave_room_h", "jtt_cave_room_i",
    "jtt_cave_room_j", "jtt_cave_corridor",
}
local debugIdx = 0

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
            if key.symbol == 'j' and not key.withShift and not key.withCtrl and not key.withAlt then
                debugIdx = (debugIdx % #DEBUG_PARTS) + 1
                local partId = DEBUG_PARTS[debugIdx]
                ui.showMessage(debugIdx .. '/' .. #DEBUG_PARTS .. ': ' .. partId .. ' (Shift+J removes)')
                core.sendGlobalEvent('JTT_DebugSpawn', { part = partId })
            end
            if key.symbol == 'j' and key.withShift and not key.withCtrl and not key.withAlt then
                debugIdx = 0
                core.sendGlobalEvent('JTT_DebugRemove', {})
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
