local core = require('openmw.core')
local self = require('openmw.self')

local DUNGEON_ENTRANCES = {
    jtt_cave_portal  = 'bear_den',
    jtt_bear_den     = 'bear_den',
}

local DUNGEON_EXITS = {
    jtt_dungeon_exit      = true,
    jtt_dungeon_entrance  = true,
}

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

local recordId = tostring(self.recordId):lower()

if DUNGEON_EXITS[recordId] then
    return {
        engineHandlers = {
            onActivate = function(activator)
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
                core.sendGlobalEvent('JTT_EnterDungeon', { dungeon_type = dungeonType })
            end
        }
    }
end

if HARVEST_NODES[recordId] then
    return {
        engineHandlers = {
            onActivate = function(activator)
                core.sendGlobalEvent('JTT_HarvestNode', { node_type = recordId })
            end
        }
    }
end

local stationKey = CRAFTING_STATIONS[recordId]
if stationKey then
    return {
        engineHandlers = {
            onActivate = function(activator)
                core.sendGlobalEvent('JTT_OpenCraftMenu', { station = stationKey })
            end
        }
    }
end

return {}
