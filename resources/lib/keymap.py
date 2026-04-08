# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
"""Manages this addon's keymap file at userdata/keymaps/service.chapternotify.xml.

Owns the full lifecycle: install, remove, sync to settings. Never reads,
parses, or modifies any other keymap file.
"""

import os

import xbmc
import xbmcvfs

from resources.lib import log

KEYMAP_DIR = xbmcvfs.translatePath("special://userdata/keymaps/")
KEYMAP_FILE = KEYMAP_DIR + "service.chapternotify.xml"

# Button name -> spec dict with "keyboard" tag (required) and optional "remote" tag.
# Keyboard tags are Kodi keymap names from xbmc/input/keymaps/keyboard/KeyboardTranslator.cpp.
# All entries are verified free in <FullscreenVideo> against system/keymaps/keyboard.xml
# in Kodi 21 (Omega). F8/F9/F10 are intentionally excluded - they're bound globally to
# Mute/VolumeDown/VolumeUp. F11 is bound globally to HDRToggle.
_BUTTONS = {
    # Color buttons - bound on both <keyboard> (rare keyboards with color keys)
    # and <remote> (CEC, MCE remotes that send color codes). Many remotes including
    # Logitech Harmony do NOT send these, so they may not fire.
    "yellow": {"keyboard": "yellow", "remote": "yellow"},
    "red":    {"keyboard": "red",    "remote": "red"},
    "green":  {"keyboard": "green",  "remote": "green"},
    "blue":   {"keyboard": "blue",   "remote": "blue"},
    # F-keys - reliably free in FullscreenVideo. Programmable remotes (Harmony, Flirc)
    # can be configured to send these.
    "f1":  {"keyboard": "f1"},
    "f2":  {"keyboard": "f2"},
    "f3":  {"keyboard": "f3"},
    "f4":  {"keyboard": "f4"},
    "f5":  {"keyboard": "f5"},
    "f6":  {"keyboard": "f6"},
    "f7":  {"keyboard": "f7"},
    "f12": {"keyboard": "f12"},
    # Letter keys - free in default FullscreenVideo. Excludes letters bound by default
    # (f, r, m, i, o, z, t, l, a, c, v, b) and common user customizations.
    "e": {"keyboard": "e"},
    "h": {"keyboard": "h"},
    "j": {"keyboard": "j"},
    "k": {"keyboard": "k"},
    "p": {"keyboard": "p"},
    "s": {"keyboard": "s"},
    "u": {"keyboard": "u"},
    "w": {"keyboard": "w"},
    "x": {"keyboard": "x"},
    "y": {"keyboard": "y"},
}


def _render(button):
    """Render the keymap XML for the given button.

    Generates a <FullscreenVideo>-scoped binding with a <keyboard> entry and an
    optional <remote> entry depending on the button spec.

    Raises ValueError for unknown buttons.
    """
    spec = _BUTTONS.get(button)
    if spec is None:
        raise ValueError("Unknown button: {}".format(button))

    kb_tag = spec["keyboard"]
    remote_tag = spec.get("remote")

    lines = [
        "<keymap>",
        "  <FullscreenVideo>",
        "    <keyboard>",
        "      <{tag}>RunScript(service.chapternotify,show)</{tag}>".format(tag=kb_tag),
        "    </keyboard>",
    ]
    if remote_tag:
        lines.extend([
            "    <remote>",
            "      <{tag}>RunScript(service.chapternotify,show)</{tag}>".format(tag=remote_tag),
            "    </remote>",
        ])
    lines.extend([
        "  </FullscreenVideo>",
        "</keymap>",
        "",
    ])
    return "\n".join(lines)


def is_installed():
    """Return True if our keymap file exists."""
    return os.path.exists(KEYMAP_FILE)


def install(button):
    """Write the keymap file for the given button and reload Kodi keymaps.

    Returns True on success, False on failure (unknown button or filesystem error).
    Idempotent: always overwrites the existing file completely; never appends.
    """
    try:
        content = _render(button)
    except ValueError as e:
        log.error("keymap install: unknown button",
                  event="keymap.install.fail", error=str(e))
        return False

    try:
        if not os.path.exists(KEYMAP_DIR):
            os.makedirs(KEYMAP_DIR)
        with open(KEYMAP_FILE, "w") as f:
            f.write(content)
    except (OSError, IOError) as e:
        log.error("keymap install: write failed",
                  event="keymap.install.fail", error=str(e))
        return False

    log.info("keymap installed", event="keymap.install.ok", button=button)
    reload()
    return True


def remove():
    """Delete our keymap file if it exists and reload Kodi keymaps.

    Returns True on success or no-op (file already absent), False on filesystem error.
    """
    if not os.path.exists(KEYMAP_FILE):
        return True

    try:
        os.remove(KEYMAP_FILE)
    except (OSError, IOError) as e:
        log.error("keymap remove: delete failed",
                  event="keymap.remove.fail", error=str(e))
        return False

    log.info("keymap removed", event="keymap.remove.ok")
    reload()
    return True


def reload():
    """Tell Kodi to re-scan userdata/keymaps/ live.

    Wrapped in try/except so a failure here still leaves the file on disk
    for the next Kodi restart.
    """
    try:
        xbmc.executebuiltin("Action(reloadkeymaps)")
        log.debug("keymap reload requested", event="keymap.reload")
    except Exception as e:
        log.error("keymap reload failed",
                  event="keymap.reload.fail", error=str(e))


# Index -> button name (matches settings.xml option order)
_BUTTON_BY_INDEX = [
    "yellow", "red", "green", "blue",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f12",
    "e", "h", "j", "k", "p", "s", "u", "w", "x", "y",
]

# Mode constants (mirror player.py for clarity in tests)
MODE_AUTO = 0
MODE_MANUAL = 1
MODE_BOTH = 2


def sync(mode, button):
    """Reconcile the keymap file with desired settings state.

    Idempotent: only writes/removes when the current state does not match
    the desired state. Safe to call from startup and from settings-change
    callbacks.
    """
    desired_installed = mode in (MODE_MANUAL, MODE_BOTH)

    if not desired_installed:
        if is_installed():
            log.debug("keymap sync: removing", event="keymap.sync",
                      mode=mode, action="remove")
            remove()
        return

    if 0 <= button < len(_BUTTON_BY_INDEX):
        button_name = _BUTTON_BY_INDEX[button]
    else:
        button_name = "yellow"

    # If installed, check whether the current button matches what we want.
    if is_installed():
        try:
            with open(KEYMAP_FILE, "r") as f:
                current = f.read()
            if "<{}>".format(button_name) in current:
                # Already correct, no-op
                return
        except (OSError, IOError):
            pass  # Fall through to reinstall

    log.debug("keymap sync: installing", event="keymap.sync",
              mode=mode, button=button_name, action="install")
    install(button_name)
