# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
"""Integration-style tests for overlay.create_chapter_overlay.

Patches the addon settings and WindowXMLDialog so we can assert
which window properties the overlay sets for each layout.
"""
from unittest.mock import MagicMock, patch

from resources.lib.overlay import create_chapter_overlay


def _parsed(artist="", track="", label="", raw=""):
    return {"artist": artist, "track": track, "label": label, "raw": raw or f"{artist} - {track}"}


def _fake_addon(show_label="true", **overrides):
    """Return a MagicMock addon whose getSetting returns configurable values."""
    defaults = {
        "position": "0",
        "opacity": "70",
        "animation": "0",
        "theme": "0",
        "show_background": "true",
        "show_label": show_label,
    }
    defaults.update(overrides)
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: defaults.get(key, "")
    addon.getAddonInfo.return_value = "/fake/path"
    return addon


def test_full_layout_sets_track_artist_and_label():
    parsed = _parsed(artist="FISHER", track="Ocean", label="CATCH & RELEASE")
    with patch("resources.lib.overlay.xbmcaddon.Addon", return_value=_fake_addon()):
        overlay = create_chapter_overlay(parsed)
    assert overlay.getProperty("layout") == "full"
    assert overlay.getProperty("track") == "Ocean"
    assert overlay.getProperty("artist") == "FISHER"
    assert overlay.getProperty("label") == "CATCH & RELEASE"
    assert overlay.getProperty("prefix_track") == "Track:"
    assert overlay.getProperty("prefix_artist") == "Artist:"
    assert overlay.getProperty("prefix_label") == "Label:"


def test_medium_layout_when_label_setting_off():
    parsed = _parsed(artist="FISHER", track="Ocean", label="CATCH & RELEASE")
    with patch("resources.lib.overlay.xbmcaddon.Addon", return_value=_fake_addon(show_label="false")):
        overlay = create_chapter_overlay(parsed)
    assert overlay.getProperty("layout") == "medium"
    assert overlay.getProperty("track") == "Ocean"
    assert overlay.getProperty("artist") == "FISHER"
    # Label stays unset
    assert overlay.getProperty("label") == ""


def test_medium_layout_when_parsed_has_no_label():
    parsed = _parsed(artist="FISHER", track="Ocean")
    with patch("resources.lib.overlay.xbmcaddon.Addon", return_value=_fake_addon()):
        overlay = create_chapter_overlay(parsed)
    assert overlay.getProperty("layout") == "medium"
    assert overlay.getProperty("track") == "Ocean"
    assert overlay.getProperty("artist") == "FISHER"
    assert overlay.getProperty("label") == ""


def test_single_layout_for_raw_chapter():
    parsed = {"artist": "", "track": "", "label": "", "raw": "Opening ceremony"}
    with patch("resources.lib.overlay.xbmcaddon.Addon", return_value=_fake_addon()):
        overlay = create_chapter_overlay(parsed)
    assert overlay.getProperty("layout") == "single"
    assert overlay.getProperty("raw") == "Opening ceremony"
    # No festival fields set in single mode
    assert overlay.getProperty("track") == ""
    assert overlay.getProperty("artist") == ""
