local core = require('openmw.core')
local self = require('openmw.self')
local ui = require('openmw.ui')
local types = require('openmw.types')

local spawned = false

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
                local player = require('openmw.self')
                core.sendGlobalEvent('JTT_DebugParts', {
                    x = player.position.x,
                    y = player.position.y,
                    z = player.position.z,
                })
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
