local core   = require('openmw.core')
local self   = require('openmw.self')
local ui     = require('openmw.ui')
local nearby = require('openmw.nearby')
local types = require('openmw.types')

local spawned = false

local HARVEST_NODES = {
    jtt_herb_node=true, jtt_mushroom_patch=true, jtt_tidal_pool=true,
    jtt_spider_web=true, jtt_iron_vein=true, jtt_rock=true,
    jtt_tree_oak=true, jtt_tree_pine=true, jtt_tree_palm=true, jtt_tree_dead=true,
}

local CRAFTING_STATIONS = {
    jtt_workbench  = "workbench",
    jtt_campfire   = "campfire",
    jtt_forge      = "forge",
    jtt_tannery    = "tannery",
    jtt_cauldron   = "cauldron",
    jtt_voodoo_hut = "voodoo_hut",
}

local DUNGEON_ENTRANCES = {
    jtt_bear_den   = 'bear_den',
    jtt_cave_portal = 'bear_den',
}

local DUNGEON_EXITS = {
    jtt_dungeon_entrance = true,
    jtt_dungeon_exit     = true,
}

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
                core.sendGlobalEvent('JTT_DebugMenuOpen', {})
            end
            if key.symbol == 'j' and key.withShift and not key.withCtrl and not key.withAlt then
                debugIdx = (debugIdx % #DEBUG_PARTS) + 1
                local partId = DEBUG_PARTS[debugIdx]
                ui.showMessage(debugIdx .. '/' .. #DEBUG_PARTS .. ': ' .. partId .. ' (Ctrl+J removes)')
                core.sendGlobalEvent('JTT_DebugSpawn', { part = partId })
            end
            if key.symbol == 'j' and not key.withShift and key.withCtrl and not key.withAlt then
                debugIdx = 0
                core.sendGlobalEvent('JTT_DebugRemove', {})
            end
            if key.symbol == 'g' and not key.withShift and not key.withCtrl and not key.withAlt then
                core.sendGlobalEvent('JTT_ResummonGolem', {})
            end
        end,
        onUpdate = function(dt)
            if not spawned then
                spawned = true
                core.sendGlobalEvent('JTT_SpawnWorld', {})
            end
        end,
    },
    eventHandlers = {
        JTT_Notify = function(data)
            ui.showMessage(data.msg)
        end,
    },
}
