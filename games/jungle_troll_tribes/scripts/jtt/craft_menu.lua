local ui   = require('openmw.ui')
local core = require('openmw.core')
local util = require('openmw.util')
local async = require('openmw.async')

local craftWindow = nil

local function closeCraftMenu()
    if craftWindow then
        craftWindow:destroy()
        craftWindow = nil
    end
end

local function makeRow(label, recipeIdx)
    return {
        type = ui.TYPE.Widget,
        props = {
            size    = util.vector2(340, 22),
            autoSize = false,
        },
        events = {
            mouseClick = async:callback(function()
                closeCraftMenu()
                core.sendGlobalEvent('JTT_Craft', { recipe_idx = recipeIdx })
            end),
        },
        content = ui.content({
            {
                type = ui.TYPE.Text,
                props = {
                    text      = label,
                    textSize  = 13,
                    textColor = util.color.rgb(1.0, 0.88, 0.6),
                    size      = util.vector2(340, 22),
                    autoSize  = false,
                },
            },
        }),
    }
end

local function onJTTShowCraftMenu(data)
    closeCraftMenu()
    local recipes     = data.recipes       -- list of { idx, label }
    local stationName = data.station_name

    local rows = {}
    for _, r in ipairs(recipes) do
        table.insert(rows, makeRow(r.label, r.idx))
    end
    -- Close row
    table.insert(rows, {
        type = ui.TYPE.Widget,
        props = { size = util.vector2(340, 22), autoSize = false },
        events = {
            mouseClick = async:callback(function() closeCraftMenu() end),
        },
        content = ui.content({
            {
                type = ui.TYPE.Text,
                props = {
                    text      = '[Close]',
                    textSize  = 13,
                    textColor = util.color.rgb(0.7, 0.5, 0.5),
                    size      = util.vector2(340, 22),
                    autoSize  = false,
                },
            },
        }),
    })

    local contentH = #rows * 24
    craftWindow = ui.create({
        layer = 'Windows',
        type  = ui.TYPE.Window,
        props = {
            caption  = stationName .. ' — Crafting',
            size     = util.vector2(360, contentH + 50),
            position = util.vector2(300, 120),
        },
        content = ui.content({
            {
                type  = ui.TYPE.Flex,
                props = {
                    horizontal = false,
                    size       = util.vector2(350, contentH),
                    autoSize   = false,
                },
                content = ui.content(rows),
            },
        }),
    })
end

return {
    eventHandlers = {
        JTT_ShowCraftMenu  = onJTTShowCraftMenu,
        JTT_CloseCraftMenu = function() closeCraftMenu() end,
    },
}
