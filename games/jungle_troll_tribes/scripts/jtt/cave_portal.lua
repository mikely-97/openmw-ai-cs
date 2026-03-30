local core = require('openmw.core')
local self = require('openmw.self')
local ui = require('openmw.ui')

local DUNGEON_ENTRANCES = {
    jtt_cave_portal     = 'bear_den',
    jtt_bear_den        = 'bear_den',
}

local DUNGEON_EXITS = {
    jtt_dungeon_exit     = true,
    jtt_dungeon_entrance = true,  -- entrance portal also exits (back to surface)
}

local recordId = tostring(self.recordId):lower()

ui.showMessage('LUA LOAD: id=' .. recordId)

if DUNGEON_EXITS[recordId] then
    return {
        engineHandlers = {
            onActivate = function(activator)
                ui.showMessage('LUA: exit activated')
                core.sendGlobalEvent('JTT_ExitDungeon', { cell_id = self.cell.name })
            end
        }
    }
end

local dungeonType = DUNGEON_ENTRANCES[recordId]
if dungeonType then
    return {
        engineHandlers = {
            onActivate = function(activator)
                ui.showMessage('LUA: entering ' .. dungeonType)
                core.sendGlobalEvent('JTT_EnterDungeon', { dungeon_type = dungeonType })
            end
        }
    }
end

ui.showMessage('LUA: no handler for ' .. recordId)
return {}
