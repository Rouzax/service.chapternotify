# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
# pyright: reportArgumentType=false
"""Tests for chapters.py parsing logic and player._resolve_chapter_name."""
from unittest.mock import patch

from resources.lib.chapters import (
    parse_chapter_name, _build_formatted_name,
    _find_seekhead_positions,
    _CHAPTERS_ID_BYTES, _TAGS_ID_BYTES, _SEEKHEAD_ID_BYTES,
)
from resources.lib import player as player_mod


# ---------------------------------------------------------------------------
# parse_chapter_name
# ---------------------------------------------------------------------------

def test_parse_full_format():
    r = parse_chapter_name("FISHER - Ocean [CATCH & RELEASE]")
    assert r["artist"] == "FISHER"
    assert r["track"] == "Ocean"
    assert r["label"] == "CATCH & RELEASE"
    assert r["raw"] == "FISHER - Ocean [CATCH & RELEASE]"


def test_parse_no_label():
    r = parse_chapter_name("FISHER - Ocean")
    assert r["artist"] == "FISHER"
    assert r["track"] == "Ocean"
    assert r["label"] == ""


def test_parse_no_match_is_raw():
    r = parse_chapter_name("Intro")
    assert r["artist"] == ""
    assert r["track"] == ""
    assert r["raw"] == "Intro"


def test_parse_empty_string():
    r = parse_chapter_name("")
    assert r["artist"] == ""
    assert r["raw"] == ""


def test_parse_language_prefix_stripped_from_raw():
    r = parse_chapter_name("en:FISHER - Ocean [CATCH & RELEASE]")
    assert r["raw"] == "FISHER - Ocean [CATCH & RELEASE]"
    assert r["artist"] == "FISHER"


def test_parse_multi_artist_with_vs():
    r = parse_chapter_name("Armin van Buuren & Adam Beyer vs. D-Shake - Techno Trance [DRUMCODE]")
    assert r["artist"] == "Armin van Buuren & Adam Beyer vs. D-Shake"
    assert r["track"] == "Techno Trance"
    assert r["label"] == "DRUMCODE"


def test_parse_id_id():
    r = parse_chapter_name("ID - ID")
    assert r["artist"] == "ID"
    assert r["track"] == "ID"
    assert r["label"] == ""


# ---------------------------------------------------------------------------
# _build_formatted_name
# ---------------------------------------------------------------------------

def test_build_full_with_prefixed_fields():
    fields = {
        "CRATEDIGGER_TRACK_PERFORMER": "FISHER",
        "CRATEDIGGER_TRACK_TITLE": "Ocean",
        "CRATEDIGGER_TRACK_LABEL": "CATCH & RELEASE",
    }
    assert _build_formatted_name(fields) == "FISHER - Ocean [CATCH & RELEASE]"


def test_build_no_label():
    fields = {"PERFORMER": "FISHER", "TITLE": "Ocean"}
    assert _build_formatted_name(fields) == "FISHER - Ocean"


def test_build_prefers_prefixed_over_legacy():
    fields = {
        "PERFORMER": "Legacy Artist",
        "CRATEDIGGER_TRACK_PERFORMER": "Current Artist",
        "TITLE": "Legacy Title",
        "CRATEDIGGER_TRACK_TITLE": "Current Title",
        "LABEL": "Old Label",
        "CRATEDIGGER_TRACK_LABEL": "New Label",
    }
    assert _build_formatted_name(fields) == "Current Artist - Current Title [New Label]"


def test_build_legacy_title_fallback():
    fields = {
        "CRATEDIGGER_TRACK_PERFORMER": "FISHER",
        "TITLE": "Ocean",
        "CRATEDIGGER_TRACK_LABEL": "CATCH & RELEASE",
    }
    assert _build_formatted_name(fields) == "FISHER - Ocean [CATCH & RELEASE]"


def test_build_missing_title_returns_none():
    assert _build_formatted_name({"PERFORMER": "FISHER"}) is None


def test_build_missing_performer_returns_none():
    assert _build_formatted_name({"TITLE": "Ocean"}) is None


def test_build_empty_fields_returns_none():
    assert _build_formatted_name({}) is None


# ---------------------------------------------------------------------------
# _find_seekhead_positions
# ---------------------------------------------------------------------------

def _build_ebml_buf(seekhead_entries, inline_elements=None):
    """Build a minimal EBML buffer with Segment, SeekHead, and optional inline elements.

    seekhead_entries is a list of (id_bytes, seek_position) tuples.
    inline_elements is a list of 4-byte element ID bytes to place after the SeekHead.
    """
    # EBML header (simplified)
    ebml_header = bytes([
        0x1A, 0x45, 0xDF, 0xA3,  # EBML ID
        0x84,                      # size = 4
        0x42, 0x86, 0x81, 0x01,   # DocType stub
    ])

    # Build SeekHead content
    sh_content = bytearray()
    for id_bytes, position in seekhead_entries:
        # SeekID child
        seek_id_child = bytes([0x53, 0xAB]) + bytes([0x80 | len(id_bytes)]) + id_bytes
        # SeekPosition child (encode as 4-byte big-endian)
        pos_bytes = position.to_bytes(4, "big")
        seek_pos_child = bytes([0x53, 0xAC, 0x84]) + pos_bytes
        # Seek element wrapping both children
        seek_payload = seek_id_child + seek_pos_child
        seek_elem = bytes([0x4D, 0xBB]) + bytes([0x80 | len(seek_payload)]) + seek_payload
        sh_content.extend(seek_elem)

    # SeekHead element
    seekhead = bytes([0x11, 0x4D, 0x9B, 0x74])
    sh_size = len(sh_content)
    seekhead += bytes([0x80 | sh_size]) + bytes(sh_content)

    # Inline elements (just ID + minimal size placeholder)
    inline_data = bytearray()
    for elem_id in (inline_elements or []):
        inline_data.extend(elem_id)
        inline_data.extend(bytes([0x80 | 0]))  # zero-size element

    # Segment (unknown size)
    seg_data = seekhead + bytes(inline_data)
    segment = bytes([0x18, 0x53, 0x80, 0x67, 0xFF]) + seg_data

    return bytearray(ebml_header + segment)


def test_seekhead_finds_chapters_and_tags_directly():
    """Standard layout: both Chapters and Tags in the primary SeekHead."""
    buf = _build_ebml_buf([
        (_CHAPTERS_ID_BYTES, 5000),
        (_TAGS_ID_BYTES, 6000),
    ])
    ch_pos, tags_pos, seg_data_start, secondary = _find_seekhead_positions(buf)
    assert ch_pos == seg_data_start + 5000
    assert tags_pos == seg_data_start + 6000
    assert secondary == []


def test_seekhead_inline_fallback_finds_chapters():
    """SeekHead only has Tags; Chapters is inline in the header buffer."""
    buf = _build_ebml_buf(
        [(_TAGS_ID_BYTES, 6000)],
        inline_elements=[_CHAPTERS_ID_BYTES],
    )
    ch_pos, tags_pos, seg_data_start, secondary = _find_seekhead_positions(buf)
    assert ch_pos is not None
    assert tags_pos == seg_data_start + 6000


def test_seekhead_detects_secondary_seekheads():
    """SeekHead references a secondary SeekHead."""
    buf = _build_ebml_buf([
        (_SEEKHEAD_ID_BYTES, 90000),
        (_TAGS_ID_BYTES, 91000),
    ])
    ch_pos, tags_pos, seg_data_start, secondary = _find_seekhead_positions(buf)
    assert ch_pos is None
    assert tags_pos == seg_data_start + 91000
    assert len(secondary) == 1
    assert secondary[0] == seg_data_start + 90000


def test_seekhead_returns_none_when_empty():
    """SeekHead with no entries returns None for both positions."""
    buf = _build_ebml_buf([])
    ch_pos, tags_pos, _, secondary = _find_seekhead_positions(buf)
    assert ch_pos is None
    assert tags_pos is None
    assert secondary == []


# ---------------------------------------------------------------------------
# _resolve_chapter_name
# ---------------------------------------------------------------------------

class _PlayerStub:
    """Minimal stand-in exposing only the fields _resolve_chapter_name uses."""
    def __init__(self):
        self._mkv_chapters = {}


def test_resolve_title_lookup_takes_priority_over_uid():
    """Title string key is tried first; UID integer key is fallback."""
    stub = _PlayerStub()
    stub._mkv_chapters["/test.mkv"] = {
        1: "Wrong Artist - Wrong Track [OLD]",   # UID-matched
        "Real Track": "Right Artist - Real Track [NEW]",  # title key
    }
    with patch("resources.lib.player.log"):
        result = player_mod.ChapterPlayer._resolve_chapter_name(  # type: ignore[arg-type]
            stub, 1, "/test.mkv", "Real Track")
    assert result == "Right Artist - Real Track [NEW]"


def test_resolve_falls_back_to_uid_when_title_misses():
    stub = _PlayerStub()
    stub._mkv_chapters["/test.mkv"] = {
        1: "FISHER - Ocean [CATCH & RELEASE]",
    }
    with patch("resources.lib.player.log"):
        result = player_mod.ChapterPlayer._resolve_chapter_name(  # type: ignore[arg-type]
            stub, 1, "/test.mkv", "NotInCache")
    assert result == "FISHER - Ocean [CATCH & RELEASE]"


def test_resolve_returns_fallback_when_cache_empty():
    stub = _PlayerStub()
    stub._mkv_chapters["/test.mkv"] = {}
    with patch("resources.lib.player.log"):
        result = player_mod.ChapterPlayer._resolve_chapter_name(  # type: ignore[arg-type]
            stub, 1, "/test.mkv", "Raw Chapter Name")
    assert result == "Raw Chapter Name"


def test_resolve_populates_cache_on_first_call():
    stub = _PlayerStub()
    mock_tags = {"Ocean": "FISHER - Ocean [CATCH & RELEASE]"}
    with patch("resources.lib.player.read_mkv_chapter_tags", return_value=mock_tags) as mock_fn:
        with patch("resources.lib.player.log"):
            result = player_mod.ChapterPlayer._resolve_chapter_name(  # type: ignore[arg-type]
                stub, 1, "/test.mkv", "Ocean")
    mock_fn.assert_called_once_with("/test.mkv")
    assert result == "FISHER - Ocean [CATCH & RELEASE]"
    assert "/test.mkv" in stub._mkv_chapters


def test_resolve_uses_cache_on_repeat_call():
    stub = _PlayerStub()
    stub._mkv_chapters["/test.mkv"] = {"Ocean": "FISHER - Ocean [CATCH & RELEASE]"}
    with patch("resources.lib.player.read_mkv_chapter_tags") as mock_fn:
        with patch("resources.lib.player.log"):
            result = player_mod.ChapterPlayer._resolve_chapter_name(  # type: ignore[arg-type]
                stub, 1, "/test.mkv", "Ocean")
    mock_fn.assert_not_called()
    assert result == "FISHER - Ocean [CATCH & RELEASE]"


def test_resolve_no_filepath_returns_fallback():
    stub = _PlayerStub()
    with patch("resources.lib.player.log"):
        result = player_mod.ChapterPlayer._resolve_chapter_name(  # type: ignore[arg-type]
            stub, 1, None, "Chapter 1")
    assert result == "Chapter 1"


def test_resolve_empty_fallback_uses_uid_only():
    """Empty fallback string skips title lookup and uses UID key."""
    stub = _PlayerStub()
    stub._mkv_chapters["/test.mkv"] = {
        3: "FISHER - Ocean [CATCH & RELEASE]",
    }
    with patch("resources.lib.player.log"):
        result = player_mod.ChapterPlayer._resolve_chapter_name(  # type: ignore[arg-type]
            stub, 3, "/test.mkv", "")
    assert result == "FISHER - Ocean [CATCH & RELEASE]"
