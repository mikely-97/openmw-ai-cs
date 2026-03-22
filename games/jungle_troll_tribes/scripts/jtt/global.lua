local world = require('openmw.world')

local function onJTTBuild(data)
    -- Set the MW global variable so the Morrowind script can detect it
    local globals = world.mwscript.getGlobalVariables()
    globals.JTT_BuildMenu = 1
end

return {
    eventHandlers = {
        JTT_Build = onJTTBuild
    }
}
