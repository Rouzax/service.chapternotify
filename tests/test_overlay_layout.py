# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
"""Unit tests for the layout decision in overlay._decide_layout."""
from resources.lib.overlay import _decide_layout


def _parsed(artist="", track="", label="", raw=""):
    return {"artist": artist, "track": track, "label": label, "raw": raw or artist or track}


def test_raw_unparsed_chapter_is_single():
    parsed = _parsed(raw="Intro Part 1")
    assert _decide_layout(parsed, show_label_setting=True) == "single"


def test_parsed_without_label_is_medium():
    parsed = _parsed(artist="FISHER", track="Ocean")
    assert _decide_layout(parsed, show_label_setting=True) == "medium"


def test_parsed_with_label_and_setting_on_is_full():
    parsed = _parsed(artist="FISHER", track="Ocean", label="CATCH & RELEASE")
    assert _decide_layout(parsed, show_label_setting=True) == "full"


def test_parsed_with_label_but_setting_off_is_medium():
    parsed = _parsed(artist="FISHER", track="Ocean", label="CATCH & RELEASE")
    assert _decide_layout(parsed, show_label_setting=False) == "medium"


def test_parsed_without_label_and_setting_off_is_medium():
    parsed = _parsed(artist="FISHER", track="Ocean")
    assert _decide_layout(parsed, show_label_setting=False) == "medium"


def test_raw_unparsed_ignores_setting():
    parsed = _parsed(raw="Intro")
    assert _decide_layout(parsed, show_label_setting=False) == "single"
