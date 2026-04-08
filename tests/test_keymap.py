# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
from unittest.mock import patch

from resources.lib import keymap


# ----- normalize_key -----

def test_normalize_key_lowercases():
    assert keymap.normalize_key("F1") == "f1"


def test_normalize_key_strips_whitespace():
    assert keymap.normalize_key("  yellow  ") == "yellow"


def test_normalize_key_falls_back_on_empty():
    assert keymap.normalize_key("") == keymap.DEFAULT_KEY


def test_normalize_key_falls_back_on_none():
    assert keymap.normalize_key(None) == keymap.DEFAULT_KEY


def test_normalize_key_rejects_punctuation():
    assert keymap.normalize_key("a-b") == keymap.DEFAULT_KEY
    assert keymap.normalize_key("foo!") == keymap.DEFAULT_KEY
    assert keymap.normalize_key("<yellow>") == keymap.DEFAULT_KEY


def test_normalize_key_accepts_underscore_and_digits():
    assert keymap.normalize_key("browser_back") == "browser_back"
    assert keymap.normalize_key("f12") == "f12"


# ----- _render -----

def test_render_yellow_emits_keyboard_and_remote():
    xml = keymap._render("yellow")
    assert "<keyboard>" in xml
    assert "<yellow>RunScript(service.chapternotify,show)</yellow>" in xml
    assert "<remote>" in xml
    assert "<FullscreenVideo>" in xml
    assert "</keymap>" in xml


def test_render_emits_both_fullscreenvideo_and_global():
    """Both scopes are needed: FullscreenVideo for normal playback context,
    global for when our overlay dialog is the active window."""
    xml = keymap._render("f1")
    assert "<FullscreenVideo>" in xml
    assert "</FullscreenVideo>" in xml
    assert "<global>" in xml
    assert "</global>" in xml
    # The key tag should appear twice - once per scope
    assert xml.count("<f1>RunScript(service.chapternotify,show)</f1>") == 2


def test_render_red_emits_remote():
    xml = keymap._render("red")
    assert "<red>RunScript(service.chapternotify,show)</red>" in xml
    assert "<remote>" in xml


def test_render_green_emits_remote():
    xml = keymap._render("green")
    assert "<remote>" in xml


def test_render_blue_emits_remote():
    xml = keymap._render("blue")
    assert "<remote>" in xml


def test_render_f1_keyboard_only():
    xml = keymap._render("f1")
    assert "<f1>RunScript(service.chapternotify,show)</f1>" in xml
    assert "<keyboard>" in xml
    assert "<remote>" not in xml


def test_render_f12_keyboard_only():
    xml = keymap._render("f12")
    assert "<f12>RunScript(service.chapternotify,show)</f12>" in xml
    assert "<remote>" not in xml


def test_render_letter_keyboard_only():
    xml = keymap._render("p")
    assert "<p>RunScript(service.chapternotify,show)</p>" in xml
    assert "<remote>" not in xml


def test_render_invalid_falls_back_to_default():
    xml = keymap._render("a-b")
    assert "<{}>".format(keymap.DEFAULT_KEY) in xml


# ----- filesystem -----

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
        assert "<remote>" in content
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


def test_install_invalid_key_writes_default(tmp_path):
    """Invalid input is normalized to DEFAULT_KEY rather than raising."""
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        ok = keymap.install("a-b")
        assert ok is True
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "<{}>".format(keymap.DEFAULT_KEY) in content


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
        assert ok is True
        ebi.assert_not_called()


# ----- sync -----

def test_sync_auto_mode_removes_existing(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    (tmp_path / "service.chapternotify.xml").write_text("<keymap></keymap>")
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=0, key="yellow")
        assert not (tmp_path / "service.chapternotify.xml").exists()


def test_sync_auto_mode_noop_when_already_absent(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        keymap.sync(mode=0, key="yellow")
        ebi.assert_not_called()


def test_sync_manual_mode_installs_when_missing(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=1, key="yellow")
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "<yellow>" in content


def test_sync_both_mode_installs(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=2, key="red")
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "<red>" in content


def test_sync_manual_mode_noop_when_already_correct(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=1, key="yellow")
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        keymap.sync(mode=1, key="yellow")
        ebi.assert_not_called()


def test_sync_key_change_rewrites(tmp_path):
    p1, p2 = _patch_keymap_dir(str(tmp_path))
    with p1, p2, patch("xbmc.executebuiltin"):
        keymap.sync(mode=1, key="yellow")
    with p1, p2, patch("xbmc.executebuiltin") as ebi:
        keymap.sync(mode=1, key="green")
        content = (tmp_path / "service.chapternotify.xml").read_text()
        assert "<green>" in content
        assert "<yellow>" not in content
        ebi.assert_called_once_with("Action(reloadkeymaps)")
