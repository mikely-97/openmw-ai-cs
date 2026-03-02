"""omwscripts — parser and writer for .omwscripts text format.

.omwscripts is a plain-text configuration format for OpenMW Lua scripts.
It is NOT the binary ESM format — it is a line-by-line text file.

Format per line:
    FLAG1, FLAG2, TYPE1 : path/to/script.lua

Sources:
    components/lua/configuration.cpp:parseOMWScripts()
    components/lua/configuration.cpp:scriptCfgToString()
"""

from omwtools.omwscripts.parser import (
    ScriptEntry,
    SCRIPT_FLAGS,
    SCRIPT_TYPES,
    parse_omwscripts,
)
from omwtools.omwscripts.writer import render_omwscripts

__all__ = [
    "ScriptEntry",
    "SCRIPT_FLAGS",
    "SCRIPT_TYPES",
    "parse_omwscripts",
    "render_omwscripts",
]
