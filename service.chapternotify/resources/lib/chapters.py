import json
import re
import xbmc


def get_chapters():
    """Fetch chapters for the active video player via JSON-RPC.

    Returns a list of dicts: [{"index": int, "name": str, "time": float_seconds}, ...]
    Returns empty list if no chapters, no active player, or on error.
    """
    request = json.dumps({
        "jsonrpc": "2.0",
        "method": "Player.GetChapters",
        "params": {"playerid": 1},
        "id": 1
    })
    try:
        raw = xbmc.executeJSONRPC(request)
        response = json.loads(raw)
    except (ValueError, TypeError) as e:
        xbmc.log("service.chapternotify: JSON-RPC error: {}".format(e),
                 xbmc.LOGWARNING)
        return []

    if "error" in response:
        xbmc.log("service.chapternotify: JSON-RPC returned error: {}".format(
            response["error"].get("message", "unknown")), xbmc.LOGDEBUG)
        return []

    chapters_raw = response.get("result", {}).get("chapters", [])
    chapters = []
    for ch in chapters_raw:
        time_seconds = ch.get("time", 0)
        chapters.append({
            "index": ch.get("index", 0),
            "name": ch.get("name", ""),
            "time": float(time_seconds),
        })
    return chapters


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
