# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
from unittest.mock import patch

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


def _patch_keymap_dir(tmpdir):
    """Helper to point keymap module at a temp directory for the duration of a test."""
    return patch.object(keymap, "KEYMAP_DIR", tmpdir + "/", create=True), \
           patch.object(keymap, "KEYMAP_FILE", tmpdir + "/service.chapternotify.xml", create=True)


def test_is_installed_false_when_missing(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2:
        assert keymap.is_installed() is False


def test_is_installed_true_when_present(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2:
        (tmp_path / "service.chapternotify.xml").write_text("<keymap></keymap>")
        assert keymap.is_installed() is True


def test_install_writes_file(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        ok = keymap.install("yellow")
        assert ok is True
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "<yellow>" in content
        assert '<key id="61591">' in content
        ebi.assert_called_once_with("Action(reloadkeymaps)")


def test_install_creates_directory(tmp_path):
    nested = tmp_path / "nested" / "keymaps"
    p1, p2 = _patch_keymap_dir(str(nested))
    with p1, p2, patch("xbmc.executebuiltin"):
        ok = keymap.install("red")
        assert ok is True
        assert (nested / "service.chapternotify.xml").exists()


def test_install_overwrites_existing(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    (tmp_path / "service.chapternotify.xml").write_text("OLD CONTENT")
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.install("green")
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "OLD CONTENT" not in content
        assert "<green>" in content


def test_remove_deletes_file(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    (tmp_path / "service.chapternotify.xml").write_text("<keymap></keymap>")
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        ok = keymap.remove()
        assert ok is True
        assert not (tmp_path / "service.chapternotify.xml").exists()
        ebi.assert_called_once_with("Action(reloadkeymaps)")


def test_remove_noop_when_missing(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        ok = keymap.remove()
        assert ok is True  # treated as success
        ebi.assert_not_called()  # no need to reload


def test_install_unknown_button_returns_false(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2:
        ok = keymap.install("purple")
        assert ok is False
        assert not (tmp_path / "service.chapternotify.xml").exists()


def test_sync_auto_mode_removes_existing(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    (tmp_path / "service.chapternotify.xml").write_text("<keymap></keymap>")
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=0, button=0)  # 0 = Auto
        assert not (tmp_path / "service.chapternotify.xml").exists()


def test_sync_auto_mode_noop_when_already_absent(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        keymap.sync(mode=0, button=0)
        ebi.assert_not_called()


def test_sync_manual_mode_installs_when_missing(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=1, button=0)  # 1 = Manual, 0 = Yellow
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "<yellow>" in content


def test_sync_both_mode_installs(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=2, button=1)  # 2 = Both, 1 = Red
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "<red>" in content


def test_sync_manual_mode_noop_when_already_correct(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=1, button=0)
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        keymap.sync(mode=1, button=0)
        ebi.assert_not_called()


def test_sync_button_change_rewrites(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=1, button=0)  # Yellow
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        keymap.sync(mode=1, button=2)  # Green
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "<green>" in content
        assert "<yellow>" not in content
        ebi.assert_called_once_with("Action(reloadkeymaps)")
