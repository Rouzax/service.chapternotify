# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import re
import xbmc
import xbmcvfs
from resources.lib import log


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
# Minimal EBML/Matroska reader for extracting per-chapter track metadata.
#
# CrateDig stores track info as MKV Tags (TargetTypeValue=30) linked to
# chapters via ChapterUID. The Tags section contains CRATEDIGGER_TRACK_PERFORMER
# (or legacy PERFORMER), TITLE, and CRATEDIGGER_TRACK_LABEL (or legacy LABEL).
#
# Strategy: read the first 64 KB, parse the SeekHead to get exact file offsets
# for the Chapters and Tags elements, then seek to those positions and read
# only what is needed. This is reliable regardless of where in the file those
# elements appear (some muxers place them after several MB of other data).
# ---------------------------------------------------------------------------

# Element IDs for SeekHead navigation
_ID_SEEK      = 0x4DBB      # 2-byte
_ID_SEEK_ID   = 0x53AB      # 2-byte
_ID_SEEK_POS  = 0x53AC      # 2-byte

# Element IDs for Chapters parsing
_ID_EDITION     = 0x45B9    # 2-byte: EditionEntry
_ID_ATOM        = 0xB6      # 1-byte: ChapterAtom
_ID_CHAPTER_UID = 0x73C4    # 2-byte: ChapterUID inside ChapterAtom

# Element IDs for Tags parsing
_ID_TAG                = 0x7373  # 2-byte: Tag block
_ID_TARGETS            = 0x63C0  # 2-byte: Targets inside Tag
_ID_TARGET_CHAPTER_UID = 0x63C5  # 2-byte: TagChapterUID inside Targets
_ID_SIMPLE_TAG         = 0x67C8  # 2-byte: SimpleTag
_ID_TAG_NAME           = 0x45A3  # 2-byte: TagName
_ID_TAG_STRING         = 0x4487  # 2-byte: TagString

# 4-byte element IDs as raw bytes (for SeekID comparisons)
_CHAPTERS_ID_BYTES = bytes([0x10, 0x43, 0xA7, 0x70])
_TAGS_ID_BYTES     = bytes([0x12, 0x54, 0xC3, 0x67])


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


def _read_uint(buf, start, end):
    """Read big-endian unsigned integer from buf[start:end]."""
    v = 0
    for byte in buf[start:end]:
        v = (v << 8) | byte
    return v


def _find_seekhead_positions(buf):
    """Parse the Segment SeekHead to find absolute file positions of Chapters and Tags.

    Returns (chapters_pos, tags_pos) as absolute byte offsets into the file.
    Either value is None if not found.
    """
    buf_bytes = bytes(buf)

    # Find the Segment element - its data start is the base for SeekPosition values
    seg_needle = bytes([0x18, 0x53, 0x80, 0x67])
    seg_idx = buf_bytes.find(seg_needle)
    if seg_idx == -1:
        return None, None
    pos = seg_idx + 4
    seg_sz, seg_w = _ebml_sz(buf, pos)
    if seg_sz is None:
        return None, None
    seg_data_start = seg_idx + 4 + seg_w

    # Find SeekHead - always the first or second element in the Segment
    sh_needle = bytes([0x11, 0x4D, 0x9B, 0x74])
    sh_idx = buf_bytes.find(sh_needle, seg_data_start, min(len(buf), seg_data_start + 8192))
    if sh_idx == -1:
        return None, None
    pos = sh_idx + 4
    sh_sz, sh_w = _ebml_sz(buf, pos)
    if sh_sz is None or sh_sz < 0:
        return None, None
    pos += sh_w
    sh_end = min(pos + sh_sz, len(buf))

    chapters_pos = None
    tags_pos = None

    while pos < sh_end:
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
        eend = min(pos + esz, sh_end)

        if eid == _ID_SEEK:
            seek_id_bytes = None
            seek_pos_val = None
            spos = pos
            while spos < eend:
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
                send = min(spos + ssz, eend)
                if sid == _ID_SEEK_ID:
                    seek_id_bytes = bytes(buf[spos:send])
                elif sid == _ID_SEEK_POS and ssz > 0:
                    seek_pos_val = _read_uint(buf, spos, send)
                spos = send

            if seek_pos_val is not None:
                abs_pos = seg_data_start + seek_pos_val
                if seek_id_bytes == _CHAPTERS_ID_BYTES:
                    chapters_pos = abs_pos
                elif seek_id_bytes == _TAGS_ID_BYTES:
                    tags_pos = abs_pos

        pos = eend

    return chapters_pos, tags_pos


def _parse_chapters_from_buf(buf):
    """Parse a buffer that starts with the Chapters element. Returns {uid_int: 1-based-index}."""
    # The buffer starts with the Chapters element ID (10 43 A7 70)
    pos = 4  # skip the 4-byte ID we already know
    ch_sz, ch_w = _ebml_sz(buf, pos)
    if ch_sz is None or ch_sz < 0:
        return {}
    pos += ch_w
    ch_end = min(pos + ch_sz, len(buf))

    uid_to_idx = {}
    chapter_idx = 0
    edition_count = 0
    atom_count = 0

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
            edition_count += 1
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
                    atom_count += 1
                    uid = None
                    spos = apos
                    while spos < aend:
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
                        send = min(spos + ssz, aend)
                        if sid == _ID_CHAPTER_UID and ssz > 0:
                            uid = _read_uint(buf, spos, send)
                        spos = send
                    if uid is not None:
                        chapter_idx += 1
                        uid_to_idx[uid] = chapter_idx

                apos = aend
        pos = eend

    log.debug("MKV chapters: parse done",
              event="mkv.ch.parse.done",
              editions=edition_count, atoms=atom_count, uids=len(uid_to_idx))
    return uid_to_idx


def _parse_tags_from_buf(buf):
    """Parse a buffer that starts with the Tags element.

    Returns (uid_to_tags, title_map) where:
      uid_to_tags  -- {uid_int: {TagName: TagString}} for tags with TagChapterUID
      title_map    -- {TITLE_string: formatted_name} for all tags with PERFORMER+TITLE
    """
    # Verify we're actually at the Tags element
    if len(buf) < 5 or bytes(buf[:4]) != _TAGS_ID_BYTES:
        log.info("MKV tags: Tags element ID mismatch in buffer",
                 event="mkv.tags.id.mismatch",
                 got=bytes(buf[:4]).hex() if len(buf) >= 4 else "short")
        return {}, {}

    pos = 4  # skip the 4-byte ID we already know
    tags_sz, tags_w = _ebml_sz(buf, pos)
    if tags_sz is None:
        return {}, {}
    pos += tags_w
    # tags_sz == -1 means unknown/unbounded size; scan to end of buffer
    tags_end = len(buf) if tags_sz < 0 else min(pos + tags_sz, len(buf))
    return _parse_tags_content(buf, pos, tags_end)


def _build_formatted_name(fields):
    """Build a 'PERFORMER - TITLE [LABEL]' string from a tag fields dict.

    Returns the formatted string if PERFORMER (or CRATEDIGGER_TRACK_PERFORMER)
    and TITLE are both present, otherwise returns None.
    """
    performer = fields.get("CRATEDIGGER_TRACK_PERFORMER") or fields.get("PERFORMER", "")
    title = fields.get("TITLE", "")
    label = fields.get("CRATEDIGGER_TRACK_LABEL") or fields.get("LABEL", "")
    if not (performer and title):
        return None
    name = "{} - {}".format(performer, title)
    if label:
        name += " [{}]".format(label)
    return name


def _parse_tags_content(buf, start, end):
    """Parse Tag blocks within a Tags element.

    Returns (uid_to_tags, title_map):
      uid_to_tags  -- {uid_int: {TagName: TagString}} for tags with TagChapterUID (0x63C5)
      title_map    -- {TITLE_string: formatted_name} for every tag with PERFORMER+TITLE fields
                      Used as a title-based fallback when UID matching yields no hits.
    """
    uid_to_tags = {}
    title_map = {}
    pos = start
    tag_total = 0
    tag_with_chapter = 0

    while pos < end:
        eid, ew = _ebml_id(buf, pos)
        if not ew:
            break
        pos += ew
        esz, ew2 = _ebml_sz(buf, pos)
        if esz is None:
            break
        pos += ew2
        if esz < 0:
            # Unknown-size element: skip to end of buffer (can't navigate past it)
            log.debug("MKV tags: unknown-size element in Tags content",
                      event="mkv.tags.unknown_sz",
                      eid="0x{:x}".format(eid) if eid is not None else "?")
            break
        eend = min(pos + esz, end)

        if eid == _ID_TAG:
            tag_total += 1
            chapter_uid = None
            tag_fields = {}

            tpos = pos
            while tpos < eend:
                tid, tw = _ebml_id(buf, tpos)
                if not tw:
                    break
                tpos += tw
                tsz, tw2 = _ebml_sz(buf, tpos)
                if tsz is None:
                    break
                tpos += tw2
                if tsz < 0:
                    break
                tend = min(tpos + tsz, eend)

                if tid == _ID_TARGETS:
                    rpos = tpos
                    while rpos < tend:
                        rid, rw = _ebml_id(buf, rpos)
                        if not rw:
                            break
                        rpos += rw
                        rsz, rw2 = _ebml_sz(buf, rpos)
                        if rsz is None:
                            break
                        rpos += rw2
                        if rsz < 0:
                            break
                        rend = min(rpos + rsz, tend)
                        if rid == _ID_TARGET_CHAPTER_UID and rsz > 0:
                            chapter_uid = _read_uint(buf, rpos, rend)
                        rpos = rend

                elif tid == _ID_SIMPLE_TAG:
                    name_str = None
                    value_str = None
                    spos = tpos
                    while spos < tend:
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
                        send = min(spos + ssz, tend)
                        if sid == _ID_TAG_NAME and ssz > 0:
                            try:
                                name_str = bytes(buf[spos:send]).decode("utf-8")
                            except Exception:
                                pass
                        elif sid == _ID_TAG_STRING and ssz > 0:
                            try:
                                value_str = bytes(buf[spos:send]).decode("utf-8")
                            except Exception:
                                pass
                        spos = send
                    if name_str is not None and value_str is not None:
                        tag_fields[name_str] = value_str

                tpos = tend

            if chapter_uid is not None and tag_fields:
                uid_to_tags[chapter_uid] = tag_fields
                tag_with_chapter += 1

            # Build title_map entry regardless of UID - used as title-based fallback.
            # CrateDig writes the same track title into both the chapter name and the
            # TITLE SimpleTag, so matching by TITLE against Player.ChapterName works
            # even when TagChapterUID doesn't match any chapter in uid_to_idx.
            formatted = _build_formatted_name(tag_fields)
            if formatted is not None:
                title = tag_fields.get("TITLE", "")
                if title:
                    title_map[title] = formatted

        pos = eend

    log.info("MKV tags: content scan done",
             event="mkv.tags.content.scan",
             tag_total=tag_total,
             tag_with_chapter=tag_with_chapter,
             by_title=len(title_map))
    return uid_to_tags, title_map


def read_mkv_chapter_tags(filepath):
    """Read per-chapter track data from MKV Tags section.

    Parses the SeekHead from the file header to find the exact byte positions
    of the Chapters and Tags elements, seeks to each, and reads only what is
    needed. This works regardless of where those elements appear in the file.

    CrateDig stores track metadata as Tags linked to chapters by ChapterUID.
    Returns a dict with two kinds of keys:
      {1-based_int: "PERFORMER - TITLE [LABEL]"}  -- from UID matching
      {TITLE_string: "PERFORMER - TITLE [LABEL]"}  -- title-based fallback

    The title-based entries allow _resolve_chapter_name to match by the Kodi
    Player.ChapterName InfoLabel value (which equals the CrateDig TITLE tag)
    when UID matching yields no results.

    Returns {} if the file cannot be read or has no CrateDig chapter tags.
    """
    if not filepath or not filepath.lower().endswith(".mkv"):
        return {}

    def _read(fh, n):
        if hasattr(fh, "readBytes"):
            return fh.readBytes(n)
        return fh.read(n)

    def _to_buf(raw):
        if not raw:
            return None
        if isinstance(raw, (bytes, bytearray)):
            return bytearray(raw)
        return bytearray(raw.encode("latin-1"))

    fh = None
    try:
        fh = xbmcvfs.File(filepath)

        # Read file header to parse SeekHead
        hdr = _to_buf(_read(fh, 65536))
        if not hdr:
            log.debug("MKV tags: header read empty",
                      event="mkv.tags.hdr.empty", file=filepath)
            return {}

        ch_pos, tags_pos = _find_seekhead_positions(hdr)
        log.info("MKV tags: SeekHead parsed",
                 event="mkv.tags.seekhead",
                 ch_pos=ch_pos, tags_pos=tags_pos, file=filepath)

        if ch_pos is None or tags_pos is None:
            log.debug("MKV tags: Chapters or Tags not found in SeekHead",
                      event="mkv.tags.seekhead.miss", file=filepath)
            return {}

        # Read and parse Chapters section
        fh.seek(ch_pos, 0)
        ch_buf = _to_buf(_read(fh, 512 * 1024))
        if not ch_buf:
            log.debug("MKV tags: Chapters read empty",
                      event="mkv.tags.ch.empty", file=filepath)
            return {}

        uid_to_idx = _parse_chapters_from_buf(ch_buf)
        if not uid_to_idx:
            # No chapter UIDs in Chapters section. Title fallback can still work
            # via the Tags section, so continue rather than returning early.
            log.debug("MKV tags: no chapter UIDs found, title fallback only",
                      event="mkv.tags.chapters.empty", file=filepath)
        else:
            log.debug("MKV tags: chapter UIDs parsed",
                      event="mkv.tags.chapters.ok", count=len(uid_to_idx), file=filepath)

        # Read and parse Tags section.
        # For large files the Tags element sits beyond 4 GB.  Some platforms
        # (Amlogic/OSMC, 32-bit vfs wrappers) silently truncate absolute seek
        # positions to 32 bits, landing in the middle of video data.  We
        # detect this by checking whether the buffer starts with the Tags
        # element ID, and retry using SEEK_END (iWhence=2) with a small
        # backwards offset that is never close to the 32-bit limit.
        fh.seek(tags_pos, 0)
        tags_buf = _to_buf(_read(fh, 1024 * 1024))

        if tags_buf and bytes(tags_buf[:4]) != _TAGS_ID_BYTES:
            log.info("MKV tags: SEEK_SET mismatch, retrying with SEEK_END",
                     event="mkv.tags.seek.retry",
                     got=bytes(tags_buf[:4]).hex(), tags_pos=tags_pos)
            # fh.seek(0, 2) returns the absolute end-of-file position (file size)
            file_size = fh.seek(0, 2)
            log.debug("MKV tags: file size from SEEK_END",
                      event="mkv.tags.file_size", size=file_size)
            if file_size and file_size > tags_pos:
                back = file_size - tags_pos  # small: Tags are near end
                fh.seek(-back, 2)
                tags_buf = _to_buf(_read(fh, min(1024 * 1024, back + 65536)))
                log.info("MKV tags: SEEK_END retry done",
                         event="mkv.tags.seek.end.done",
                         back=back,
                         ok=(bool(tags_buf) and bytes(tags_buf[:4]) == _TAGS_ID_BYTES))
            else:
                tags_buf = None

        if not tags_buf:
            log.debug("MKV tags: Tags read empty",
                      event="mkv.tags.tags.empty", file=filepath)
            return {}

        uid_to_tags, title_map = _parse_tags_from_buf(tags_buf)
        if not uid_to_tags and not title_map:
            log.info("MKV tags: no usable tag blocks found",
                     event="mkv.tags.blocks.empty", file=filepath)
            return {}
        log.info("MKV tags: tag blocks parsed",
                 event="mkv.tags.blocks.ok",
                 by_uid=len(uid_to_tags), by_title=len(title_map), file=filepath)

        # Build result: integer keys from UID matching, string keys as title fallback.
        # _resolve_chapter_name tries the title string key first (always present for
        # CrateDig files), then falls back to the integer chapter-index key from UID
        # matching.
        result = {}

        # UID-matched entries (indexed by 1-based chapter number)
        for uid, fields in uid_to_tags.items():
            idx = uid_to_idx.get(uid)
            if idx is None:
                continue
            formatted = _build_formatted_name(fields)
            if formatted is not None:
                result[idx] = formatted
            else:
                log.debug("MKV tags: chapter missing performer or title",
                          event="mkv.tags.chapter.incomplete",
                          chapter=idx, fields=list(fields.keys()))

        # Title-keyed fallback entries (indexed by TITLE string)
        result.update(title_map)

        log.info("MKV tags: done",
                 event="mkv.tags.done",
                 by_uid=len(result) - len(title_map), by_title=len(title_map),
                 file=filepath)
        return result

    except Exception as e:
        log.debug("MKV tags: exception",
                  event="mkv.tags.error", error=str(e), file=filepath)
        return {}
    finally:
        if fh is not None:
            try:
                fh.close()
            except Exception:
                pass
