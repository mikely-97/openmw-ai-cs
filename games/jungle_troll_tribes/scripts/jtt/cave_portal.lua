local core = require('openmw.core')
local self = require('openmw.self')
local ui = require('openmw.ui')

local DEBUG_PORTALS = {
    jtt_debug_portal_0 = { cell='jtt_bear_den_0', x=2816.0, y=4864.0, z=50.0 },
    jtt_debug_portal_1 = { cell='jtt_bear_den_1', x=1536.0, y=4608.0, z=50.0 },
    jtt_debug_portal_2 = { cell='jtt_bear_den_2', x=2816.0, y=5632.0, z=50.0 },
    jtt_debug_portal_3 = { cell='jtt_bear_den_3', x=5632.0, y=4608.0, z=50.0 },
    jtt_debug_portal_4 = { cell='jtt_bear_den_4', x=1280.0, y=1280.0, z=50.0 },
    jtt_debug_portal_5 = { cell='jtt_bear_den_5', x=1536.0, y=3584.0, z=50.0 },
    jtt_debug_portal_6 = { cell='jtt_bear_den_6', x=1792.0, y=6144.0, z=50.0 },
    jtt_debug_portal_7 = { cell='jtt_bear_den_7', x=1024.0, y=1280.0, z=50.0 },
}

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

local dbg = DEBUG_PORTALS[recordId]
if dbg then
    return {
        engineHandlers = {
            onActivate = function(activator)
                core.sendGlobalEvent('JTT_EnterDungeonDirect',
                    { cell=dbg.cell, x=dbg.x, y=dbg.y, z=dbg.z })
            end
        }
    }
end

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
