# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
# pyright: reportArgumentType=false
"""Tests for chapters.py parsing logic and player._resolve_chapter_name."""
from unittest.mock import patch

from resources.lib.chapters import parse_chapter_name, _build_formatted_name
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
        "TITLE": "Ocean",
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
        "TITLE": "Ocean",
        "LABEL": "Old Label",
        "CRATEDIGGER_TRACK_LABEL": "New Label",
    }
    assert _build_formatted_name(fields) == "Current Artist - Ocean [New Label]"


def test_build_missing_title_returns_none():
    assert _build_formatted_name({"PERFORMER": "FISHER"}) is None


def test_build_missing_performer_returns_none():
    assert _build_formatted_name({"TITLE": "Ocean"}) is None


def test_build_empty_fields_returns_none():
    assert _build_formatted_name({}) is None


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
