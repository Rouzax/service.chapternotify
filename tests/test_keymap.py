# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
from resources.lib import keymap


def test_render_yellow_button():
    xml = keymap._render("yellow")
    assert "<yellow>RunScript(service.chapternotify,show)</yellow>" in xml
    assert '<key id="61591">RunScript(service.chapternotify,show)</key>' in xml
    assert "<FullscreenVideo>" in xml
    assert "</keymap>" in xml


def test_render_red_button():
    xml = keymap._render("red")
    assert "<red>RunScript(service.chapternotify,show)</red>" in xml
    assert '<key id="61588">RunScript(service.chapternotify,show)</key>' in xml


def test_render_green_button():
    xml = keymap._render("green")
    assert "<green>RunScript(service.chapternotify,show)</green>" in xml
    assert '<key id="61589">RunScript(service.chapternotify,show)</key>' in xml


def test_render_blue_button():
    xml = keymap._render("blue")
    assert "<blue>RunScript(service.chapternotify,show)</blue>" in xml
    assert '<key id="61590">RunScript(service.chapternotify,show)</key>' in xml


def test_render_unknown_button_raises():
    import pytest
    with pytest.raises(ValueError):
        keymap._render("purple")
