"""Unit tests for .omwscripts text format parser and writer."""

import pytest
from omwtools.omwscripts.parser import (
    parse_omwscripts,
    ScriptEntry,
    OMWScriptsParseError,
    SCRIPT_FLAGS,
)
from omwtools.omwscripts.writer import render_omwscripts


class TestParser:
    def test_empty_file(self):
        entries = parse_omwscripts("")
        assert entries == []

    def test_comment_only(self):
        entries = parse_omwscripts("# just a comment\n# another\n")
        assert entries == []

    def test_global_script(self):
        entries = parse_omwscripts("GLOBAL: scripts/mymod/main.lua")
        assert len(entries) == 1
        e = entries[0]
        assert e.script_path == "scripts/mymod/main.lua"
        assert e.flags == SCRIPT_FLAGS["GLOBAL"]
        assert e.types == []

    def test_player_script(self):
        entries = parse_omwscripts("PLAYER : scripts/player.lua")
        assert len(entries) == 1
        assert entries[0].flags == SCRIPT_FLAGS["PLAYER"]

    def test_custom_script(self):
        entries = parse_omwscripts("CUSTOM : scripts/custom.lua")
        assert entries[0].flags == SCRIPT_FLAGS["CUSTOM"]

    def test_menu_script(self):
        entries = parse_omwscripts("MENU : scripts/menu.lua")
        assert entries[0].flags == SCRIPT_FLAGS["MENU"]

    def test_type_tags(self):
        entries = parse_omwscripts("NPC CREATURE : scripts/creature.lua")
        assert entries[0].flags == 0
        assert "NPC" in entries[0].types
        assert "CREATURE" in entries[0].types

    def test_mixed_flags_and_types(self):
        entries = parse_omwscripts("PLAYER NPC CREATURE : scripts/mixed.lua")
        e = entries[0]
        assert e.flags == SCRIPT_FLAGS["PLAYER"]
        assert "NPC" in e.types
        assert "CREATURE" in e.types

    def test_comma_separated_tags(self):
        entries = parse_omwscripts("GLOBAL, PLAYER: scripts/both.lua")
        e = entries[0]
        assert e.flags == (SCRIPT_FLAGS["GLOBAL"] | SCRIPT_FLAGS["PLAYER"])

    def test_case_insensitive_tags(self):
        entries = parse_omwscripts("global: scripts/main.lua")
        assert entries[0].flags == SCRIPT_FLAGS["GLOBAL"]

    def test_multiple_lines(self):
        text = (
            "GLOBAL: scripts/global.lua\n"
            "PLAYER: scripts/player.lua\n"
            "# comment\n"
            "\n"
            "NPC: scripts/npc.lua\n"
        )
        entries = parse_omwscripts(text)
        assert len(entries) == 3

    def test_crlf_line_endings(self):
        entries = parse_omwscripts("GLOBAL: scripts/main.lua\r\nPLAYER: scripts/p.lua\r\n")
        assert len(entries) == 2

    def test_all_type_tags(self):
        all_types = [
            "ACTIVATOR", "ARMOR", "BOOK", "CLOTHING", "CONTAINER",
            "CREATURE", "DOOR", "INGREDIENT", "LIGHT", "MISC_ITEM",
            "NPC", "POTION", "WEAPON", "APPARATUS", "LOCKPICK",
            "PROBE", "REPAIR",
        ]
        for t in all_types:
            entries = parse_omwscripts(f"{t}: scripts/test.lua")
            assert entries[0].types == [t], f"Failed for type {t}"

    def test_no_extension_error(self):
        with pytest.raises(OMWScriptsParseError, match="must end with"):
            parse_omwscripts("GLOBAL: scripts/main.txt")

    def test_unknown_tag_error(self):
        with pytest.raises(OMWScriptsParseError, match="unknown tag"):
            parse_omwscripts("BOGUSTAG: scripts/main.lua")

    def test_no_colon_no_dot_lua_error(self):
        # Line ends with .lua but has no colon separator → no ':' separator error
        with pytest.raises(OMWScriptsParseError, match="no ':' separator"):
            parse_omwscripts("GLOBAL scripts/main.lua")

    def test_empty_path_colon(self):
        # Line is just "GLOBAL:" — must raise (empty path after strip)
        # Actually the line ends with ":" not ".lua" — fails .lua check first
        with pytest.raises(OMWScriptsParseError):
            parse_omwscripts("GLOBAL:")


class TestWriter:
    def test_render_global(self):
        entries = [ScriptEntry("scripts/main.lua", SCRIPT_FLAGS["GLOBAL"])]
        text = render_omwscripts(entries)
        assert "GLOBAL" in text
        assert "scripts/main.lua" in text

    def test_render_types(self):
        entries = [ScriptEntry("scripts/npc.lua", 0, ["NPC", "CREATURE"])]
        text = render_omwscripts(entries)
        assert "NPC" in text
        assert "CREATURE" in text

    def test_render_round_trip(self):
        text = "GLOBAL: scripts/a.lua\nPLAYER NPC: scripts/b.lua\n"
        entries = parse_omwscripts(text)
        rendered = render_omwscripts(entries)
        re_parsed = parse_omwscripts(rendered)
        assert len(re_parsed) == len(entries)
        for orig, re in zip(entries, re_parsed):
            assert orig.script_path == re.script_path
            assert orig.flags == re.flags
            assert set(orig.types) == set(re.types)

    def test_render_with_header(self):
        entries = [ScriptEntry("scripts/main.lua", SCRIPT_FLAGS["GLOBAL"])]
        text = render_omwscripts(entries, header_comment="My Mod\nVersion 1.0")
        assert "# My Mod" in text
        assert "# Version 1.0" in text
