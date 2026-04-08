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

# Color name -> (remote tag, keyboard key id)
# Key ids are Kodi's full button codes: KEY_VKEY (0xF000) | XBMCVK_Fn.
# Verified against xbmc/input/keyboard/XBMC_vkeys.h and
# xbmc/input/keymaps/keyboard/KeyboardTranslator.cpp in Kodi 21 (Omega).
_BUTTONS = {
    "yellow": ("yellow", 61591),  # F8 = 0xF000 | 0x97
    "red":    ("red",    61588),  # F5 = 0xF000 | 0x94
    "green":  ("green",  61589),  # F6 = 0xF000 | 0x95
    "blue":   ("blue",   61590),  # F7 = 0xF000 | 0x96
}

_TEMPLATE = """\
<keymap>
  <FullscreenVideo>
    <keyboard>
      <key id="{key_id}">RunScript(service.chapternotify,show)</key>
    </keyboard>
    <remote>
      <{tag}>RunScript(service.chapternotify,show)</{tag}>
    </remote>
  </FullscreenVideo>
</keymap>
"""


def _render(button):
    """Render the keymap XML for the given color button.

    Raises ValueError for unknown buttons.
    """
    if button not in _BUTTONS:
        raise ValueError("Unknown button: {}".format(button))
    tag, key_id = _BUTTONS[button]
    return _TEMPLATE.format(key_id=key_id, tag=tag)


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
