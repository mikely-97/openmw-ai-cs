"""Parse .omwscripts text files into ScriptEntry objects.

.omwscripts format (from components/lua/configuration.cpp):
  - One script per line
  - Lines starting with '#' are comments
  - Empty lines are ignored
  - Each line: TAGS: path/to/script.lua
    - TAGS is a comma-or-space-separated list of flag/type names
    - Script path must end with .lua (case-insensitive)
  - Tag names are case-insensitive

Flag bits:
  GLOBAL = 1, CUSTOM = 2, PLAYER = 4, MERGE = 8, MENU = 16

Object-type attachment tags map to ESM record type names:
  NPC → NPC_, CREATURE → CREA, CONTAINER → CONT, DOOR → DOOR,
  ACTIVATOR → ACTI, ARMOR → ARMO, BOOK → BOOK, CLOTHING → CLOT,
  INGREDIENT → INGR, LIGHT → LIGH, MISC_ITEM → MISC, POTION → ALCH,
  WEAPON → WEAP, APPARATUS → APPA, LOCKPICK → LOCK, PROBE → PROB,
  REPAIR → REPA
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Flag definitions (from components/lua/configuration.cpp:flagsByName)
# ---------------------------------------------------------------------------

SCRIPT_FLAGS: dict[str, int] = {
    "GLOBAL": 1,
    "CUSTOM": 2,
    "PLAYER": 4,
    "MENU":   16,
    # MERGE (8) is not a text tag — only appears in binary LUAL records
}

# Object-type tags (from components/lua/configuration.cpp:typeTagsByName)
SCRIPT_TYPES: set[str] = {
    "ACTIVATOR",
    "ARMOR",
    "BOOK",
    "CLOTHING",
    "CONTAINER",
    "CREATURE",
    "DOOR",
    "INGREDIENT",
    "LIGHT",
    "MISC_ITEM",
    "NPC",
    "POTION",
    "WEAPON",
    "APPARATUS",
    "LOCKPICK",
    "PROBE",
    "REPAIR",
}

# Map text tags → 4-byte ESM record type (for use in LUAF types list)
TYPE_TAG_TO_RECNAME: dict[str, bytes] = {
    "ACTIVATOR": b"ACTI",
    "ARMOR":     b"ARMO",
    "BOOK":      b"BOOK",
    "CLOTHING":  b"CLOT",
    "CONTAINER": b"CONT",
    "CREATURE":  b"CREA",
    "DOOR":      b"DOOR",
    "INGREDIENT":b"INGR",
    "LIGHT":     b"LIGH",
    "MISC_ITEM": b"MISC",
    "NPC":       b"NPC_",
    "POTION":    b"ALCH",
    "WEAPON":    b"WEAP",
    "APPARATUS": b"APPA",
    "LOCKPICK":  b"LOCK",
    "PROBE":     b"PROB",
    "REPAIR":    b"REPA",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ScriptEntry:
    """One script line from a .omwscripts file."""
    script_path: str
    flags: int = 0          # bitmask of SCRIPT_FLAGS values
    types: list[str] = field(default_factory=list)   # SCRIPT_TYPES names

    def has_flag(self, name: str) -> bool:
        return bool(self.flags & SCRIPT_FLAGS.get(name.upper(), 0))

    def flag_names(self) -> list[str]:
        return [name for name, bit in sorted(SCRIPT_FLAGS.items()) if self.flags & bit]

    def __repr__(self) -> str:
        parts = self.flag_names() + self.types
        tags = " ".join(parts)
        return f"ScriptEntry({tags!r}: {self.script_path!r})"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class OMWScriptsParseError(ValueError):
    pass


def parse_omwscripts(text: str) -> list[ScriptEntry]:
    """Parse a .omwscripts text file and return a list of ScriptEntry objects.

    Parameters
    ----------
    text:
        Full contents of the .omwscripts file.

    Returns
    -------
    list[ScriptEntry]

    Raises
    ------
    OMWScriptsParseError
        On any malformed line.
    """
    entries: list[ScriptEntry] = []
    upper_flags = {k.upper(): v for k, v in SCRIPT_FLAGS.items()}
    upper_types = {t.upper() for t in SCRIPT_TYPES}

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        # Strip line endings and whitespace
        line = raw_line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Script path must end in .lua (case-insensitive)
        if not line.lower().endswith(".lua"):
            raise OMWScriptsParseError(
                f"Line {lineno}: script path must end with '.lua', got: {line[:300]!r}"
            )

        # Split at the colon
        colon_pos = line.find(":")
        if colon_pos < 0:
            raise OMWScriptsParseError(
                f"Line {lineno}: no ':' separator found (expected 'TAGS: script.lua')"
            )

        tags_str   = line[:colon_pos]
        script_path = line[colon_pos + 1:].strip()

        if not script_path:
            raise OMWScriptsParseError(
                f"Line {lineno}: empty script path after ':'"
            )

        # Parse tags
        flags = 0
        types: list[str] = []

        raw_tags = tags_str.replace(",", " ").split()
        for tag in raw_tags:
            upper_tag = tag.upper()
            if upper_tag in upper_flags:
                flags |= upper_flags[upper_tag]
            elif upper_tag in upper_types:
                types.append(upper_tag)
            else:
                raise OMWScriptsParseError(
                    f"Line {lineno}: unknown tag {tag!r}"
                )

        entries.append(ScriptEntry(
            script_path=script_path,
            flags=flags,
            types=types,
        ))

    return entries
