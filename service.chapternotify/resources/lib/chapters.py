# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import re
import xbmc


def get_current_chapter():
    """Get the current chapter number, total count, and name via info labels.

    Returns a dict: {"chapter": int, "count": int, "name": str}
    Returns None if no chapter info is available.
    """
    chapter_str = xbmc.getInfoLabel("Player.Chapter")
    count_str = xbmc.getInfoLabel("Player.ChapterCount")
    name = xbmc.getInfoLabel("Player.ChapterName")

    if not chapter_str or not count_str:
        return None

    try:
        chapter = int(chapter_str)
        count = int(count_str)
    except ValueError:
        return None

    if count <= 1:
        return None

    return {"chapter": chapter, "count": count, "name": name}


def parse_chapter_name(name):
    """Parse 'Artist - Track [Label]' into structured dict.

    Returns {"artist": str, "track": str, "label": str, "raw": str}.
    If the format doesn't match, artist/track/label may be empty and raw
    contains the original name.
    """
    result = {"artist": "", "track": "", "label": "", "raw": name}

    # Strip leading language tag like "en:" if present
    cleaned = re.sub(r"^[a-z]{2}:", "", name).strip()
    result["raw"] = cleaned

    # Try to match: Artist - Track [Label]
    match = re.match(r"^(.+?)\s+-\s+(.+?)(?:\s+\[(.+?)\])?\s*$", cleaned)
    if match:
        result["artist"] = match.group(1).strip()
        result["track"] = match.group(2).strip()
        result["label"] = (match.group(3) or "").strip()

    return result
