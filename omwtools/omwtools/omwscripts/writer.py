"""Render ScriptEntry objects back to .omwscripts text format.

Output format mirrors what OpenMW's scriptCfgToString() produces:
  FLAG1 FLAG2 TYPE1 : path/to/script.lua
"""

from __future__ import annotations

from omwtools.omwscripts.parser import ScriptEntry, SCRIPT_FLAGS

# Canonical output order for flags
_FLAG_ORDER = ["GLOBAL", "PLAYER", "CUSTOM", "MENU"]


def render_omwscripts(
    entries: list[ScriptEntry],
    header_comment: str = "",
) -> str:
    """Render a list of ScriptEntry objects to .omwscripts text.

    Parameters
    ----------
    entries:
        Script entries to render.
    header_comment:
        Optional multi-line comment block at the top of the file.
        Each line will be prefixed with '# '.

    Returns
    -------
    str
        Text content suitable for writing to a .omwscripts file.
    """
    lines: list[str] = []

    if header_comment:
        for hline in header_comment.splitlines():
            lines.append(f"# {hline}" if hline.strip() else "#")
        lines.append("")

    for entry in entries:
        # Collect flag names in canonical order
        flag_parts: list[str] = []
        for flag_name in _FLAG_ORDER:
            bit = SCRIPT_FLAGS.get(flag_name, 0)
            if entry.flags & bit:
                flag_parts.append(flag_name)

        # Type names as-is (already uppercase)
        all_tags = flag_parts + list(entry.types)
        tag_str = " ".join(all_tags)
        lines.append(f"{tag_str} : {entry.script_path}")

    return "\n".join(lines) + "\n"
