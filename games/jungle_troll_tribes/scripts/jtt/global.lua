local world = require('openmw.world')

local function onJTTBuild(data)
    local globals = world.mwscript.getGlobalVariables()
    globals.JTT_BuildMenu = 1
end

local function onJTTQuest(data)
    local globals = world.mwscript.getGlobalVariables()
    globals.JTT_QuestMenu = 1
end

return {
    eventHandlers = {
        JTT_Build = onJTTBuild,
        JTT_Quest = onJTTQuest
    }
}
