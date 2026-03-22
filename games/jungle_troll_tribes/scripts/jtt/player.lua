local core = require('openmw.core')

return {
    engineHandlers = {
        onKeyPress = function(key)
            if key.symbol == 'b' and not key.withShift and not key.withCtrl and not key.withAlt then
                core.sendGlobalEvent('JTT_Build', {})
            end
        end
    }
}
