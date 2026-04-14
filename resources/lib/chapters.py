# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import re
import xbmc
import xbmcvfs


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


# ---------------------------------------------------------------------------
# Minimal EBML/Matroska reader for extracting chapter display strings.
#
# MKV files created by CrateDig store two ChapterDisplay entries per chapter:
#   - language "und" (undetermined): just the track title  <- Kodi uses this
#   - language "en": full "Artist - Track [Label]" string  <- we want this
#
# We read the raw file and parse the Chapters EBML element to get the
# preferred-language display string for each chapter.
# ---------------------------------------------------------------------------

# Matroska element IDs
_ID_EDITION  = 0x45B9       # 2-byte
_ID_ATOM     = 0xB6         # 1-byte
_ID_DISPLAY  = 0x80         # 1-byte
_ID_STRING   = 0x85         # 1-byte
_ID_LANG     = 0x437C       # 2-byte


def _ebml_id(b, p):
    """Read EBML element ID from bytearray b at offset p.
    Returns (id_int, bytes_consumed) or (None, 0)."""
    if p >= len(b):
        return None, 0
    c = b[p]
    if c & 0x80:
        return c, 1
    if c & 0x40:
        if p + 1 >= len(b): return None, 0
        return (c << 8) | b[p + 1], 2
    if c & 0x20:
        if p + 2 >= len(b): return None, 0
        return (c << 16) | (b[p + 1] << 8) | b[p + 2], 3
    if c & 0x10:
        if p + 3 >= len(b): return None, 0
        return (c << 24) | (b[p + 1] << 16) | (b[p + 2] << 8) | b[p + 3], 4
    return None, 0


def _ebml_sz(b, p):
    """Read EBML data-size VINT from bytearray b at offset p.
    Returns (size, bytes_consumed) or (None, 0). size=-1 means unknown."""
    if p >= len(b):
        return None, 0
    c = b[p]
    if c & 0x80:
        v, w = c & 0x7F, 1
    elif c & 0x40:
        if p + 1 >= len(b): return None, 0
        v, w = ((c & 0x3F) << 8) | b[p + 1], 2
    elif c & 0x20:
        if p + 2 >= len(b): return None, 0
        v, w = ((c & 0x1F) << 16) | (b[p + 1] << 8) | b[p + 2], 3
    elif c & 0x10:
        if p + 3 >= len(b): return None, 0
        v, w = ((c & 0x0F) << 24) | (b[p + 1] << 16) | (b[p + 2] << 8) | b[p + 3], 4
    elif c & 0x08:
        if p + 4 >= len(b): return None, 0
        v = ((c & 0x07) << 32) | (b[p + 1] << 24) | (b[p + 2] << 16) | (b[p + 3] << 8) | b[p + 4]
        w = 5
    elif c & 0x04:
        if p + 5 >= len(b): return None, 0
        v = ((c & 0x03) << 40) | (b[p + 1] << 32) | (b[p + 2] << 24) | (b[p + 3] << 16) | (b[p + 4] << 8) | b[p + 5]
        w = 6
    elif c & 0x02:
        if p + 6 >= len(b): return None, 0
        v = ((c & 0x01) << 48) | (b[p + 1] << 40) | (b[p + 2] << 32) | (b[p + 3] << 24) | (b[p + 4] << 16) | (b[p + 5] << 8) | b[p + 6]
        w = 7
    elif c & 0x01:
        if p + 7 >= len(b): return None, 0
        v = (b[p + 1] << 48) | (b[p + 2] << 40) | (b[p + 3] << 32) | (b[p + 4] << 24) | (b[p + 5] << 16) | (b[p + 6] << 8) | b[p + 7]
        w = 8
    else:
        return None, 0
    unknown = (1 << (7 * w)) - 1
    return (-1 if v == unknown else v), w


def _pick_lang(displays, preferred):
    """Pick best (lang, string) from displays list, prioritising preferred."""
    for lang in (preferred, "eng", "und", ""):
        for l, s in displays:
            if l == lang:
                return s
    return displays[0][1] if displays else None


def read_mkv_chapter_names(filepath, preferred_lang="en"):
    """Read per-language chapter display strings from an MKV file.

    Reads the first 4 MiB (enough for chapters in ffmpeg/yt-dlp generated
    files) and returns {1-based chapter index: display_string} using the
    preferred language, falling back to "eng" then "und" then first available.
    Returns an empty dict if the Chapters element cannot be found or parsed.
    """
    if not filepath or not filepath.lower().endswith(".mkv"):
        return {}
    try:
        fh = xbmcvfs.File(filepath)
        # readBytes() returns bytes in Kodi 19+; fall back to read() for older builds
        if hasattr(fh, "readBytes"):
            raw = fh.readBytes(4 * 1024 * 1024)
        else:
            raw = fh.read(4 * 1024 * 1024)
        fh.close()
        if not raw:
            return {}
        if isinstance(raw, (bytes, bytearray)):
            buf = bytearray(raw)
        else:
            buf = bytearray(raw.encode("latin-1"))
    except Exception:
        return {}

    # Locate Chapters element by scanning for its 4-byte ID
    needle = bytes([0x10, 0x43, 0xA7, 0x70])
    idx = bytes(buf).find(needle)
    if idx == -1:
        return {}

    pos = idx + 4
    ch_sz, ch_w = _ebml_sz(buf, pos)
    if ch_sz is None or ch_sz < 0:
        return {}
    pos += ch_w
    ch_end = min(pos + ch_sz, len(buf))

    result = {}
    chapter_idx = 0

    # Chapters > EditionEntry > ChapterAtom > ChapterDisplay > ChapterString/ChapterLanguage
    while pos < ch_end:
        eid, ew = _ebml_id(buf, pos)
        if not ew:
            break
        pos += ew
        esz, ew2 = _ebml_sz(buf, pos)
        if esz is None:
            break
        pos += ew2
        if esz < 0:
            break
        eend = min(pos + esz, ch_end)

        if eid == _ID_EDITION:
            apos = pos
            while apos < eend:
                aid, aw = _ebml_id(buf, apos)
                if not aw:
                    break
                apos += aw
                asz, aw2 = _ebml_sz(buf, apos)
                if asz is None:
                    break
                apos += aw2
                if asz < 0:
                    break
                aend = min(apos + asz, eend)

                if aid == _ID_ATOM:
                    displays = []
                    dpos = apos
                    while dpos < aend:
                        did, dw = _ebml_id(buf, dpos)
                        if not dw:
                            break
                        dpos += dw
                        dsz, dw2 = _ebml_sz(buf, dpos)
                        if dsz is None:
                            break
                        dpos += dw2
                        if dsz < 0:
                            break
                        dend = min(dpos + dsz, aend)

                        if did == _ID_DISPLAY:
                            lang = "und"
                            string = None
                            spos = dpos
                            while spos < dend:
                                sid, sw = _ebml_id(buf, spos)
                                if not sw:
                                    break
                                spos += sw
                                ssz, sw2 = _ebml_sz(buf, spos)
                                if ssz is None:
                                    break
                                spos += sw2
                                if ssz < 0:
                                    break
                                send = min(spos + ssz, dend)
                                if sid == _ID_STRING:
                                    try:
                                        string = bytes(buf[spos:send]).decode("utf-8")
                                    except Exception:
                                        pass
                                elif sid == _ID_LANG:
                                    try:
                                        lang = bytes(buf[spos:send]).decode("ascii").rstrip("\x00").lower()
                                    except Exception:
                                        pass
                                spos = send
                            if string is not None:
                                displays.append((lang, string))

                        dpos = dend

                    chosen = _pick_lang(displays, preferred_lang)
                    if chosen:
                        chapter_idx += 1
                        result[chapter_idx] = chosen

                apos = aend
        pos = eend

    return result
