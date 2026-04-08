# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
"""Manages this addon's keymap file at userdata/keymaps/service.chapternotify.xml.

Owns the full lifecycle: install, remove, sync to settings. Never reads,
parses, or modifies any other keymap file.

The trigger key is a free-form Kodi keymap tag (e.g. "f1", "yellow", "p",
"browser_back"). The user is responsible for picking a key their input
device actually sends and that does not collide with their other bindings.
The binding is scoped to <FullscreenVideo> only, so collisions outside
playback are limited to whatever Kodi action is normally bound to that key.
"""

import os
import re

import xbmc
import xbmcvfs

from resources.lib import log

KEYMAP_DIR = xbmcvfs.translatePath("special://userdata/keymaps/")
KEYMAP_FILE = KEYMAP_DIR + "service.chapternotify.xml"

# Mode constants (mirror player.py for clarity in tests)
MODE_AUTO = 0
MODE_MANUAL = 1
MODE_BOTH = 2

DEFAULT_KEY = "f1"

# Color buttons get an additional <remote> binding because some remotes
# (CEC, MCE) send them through the remote input path rather than as
# keyboard scancodes. All other keys are keyboard-only.
_COLOR_KEYS = {"yellow", "red", "green", "blue"}

# Validates that a key name is safe to embed in XML and matches the
# Kodi keymap tag conventions: lowercase letters, digits, underscore.
# This intentionally rejects punctuation, dashes, and uppercase to keep
# the surface area small and predictable.
_KEY_PATTERN = re.compile(r"^[a-z0-9_]+$")


def normalize_key(key):
    """Lowercase, strip whitespace, and validate. Returns DEFAULT_KEY if invalid."""
    if not isinstance(key, str):
        return DEFAULT_KEY
    key = key.strip().lower()
    if not key or not _KEY_PATTERN.match(key):
        return DEFAULT_KEY
    return key


def _render(key):
    """Render the keymap XML for the given key name.

    Generates a <FullscreenVideo>-scoped binding with a <keyboard> entry and
    an additional <remote> entry only for the four color buttons.

    The key is normalized; invalid input falls back to DEFAULT_KEY rather
    than raising, so a bad setting can never crash the service.
    """
    key = normalize_key(key)

    lines = [
        "<keymap>",
        "  <FullscreenVideo>",
        "    <keyboard>",
        "      <{tag}>RunScript(service.chapternotify,show)</{tag}>".format(tag=key),
        "    </keyboard>",
    ]
    if key in _COLOR_KEYS:
        lines.extend([
            "    <remote>",
            "      <{tag}>RunScript(service.chapternotify,show)</{tag}>".format(tag=key),
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


def install(key):
    """Write the keymap file for the given key name and reload Kodi keymaps.

    Returns True on success, False on filesystem error. Idempotent: always
    overwrites the existing file completely; never appends.
    """
    content = _render(key)

    try:
        if not os.path.exists(KEYMAP_DIR):
            os.makedirs(KEYMAP_DIR)
        with open(KEYMAP_FILE, "w") as f:
            f.write(content)
    except (OSError, IOError) as e:
        log.error("keymap install: write failed",
                  event="keymap.install.fail", error=str(e))
        return False

    log.info("keymap installed", event="keymap.install.ok", key=normalize_key(key))
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


def sync(mode, key):
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

    key = normalize_key(key)

    # If installed, check whether the current key matches what we want.
    if is_installed():
        try:
            with open(KEYMAP_FILE, "r") as f:
                current = f.read()
            if "<{}>".format(key) in current:
                return  # Already correct, no-op
        except (OSError, IOError):
            pass  # Fall through to reinstall

    log.debug("keymap sync: installing", event="keymap.sync",
              mode=mode, key=key, action="install")
    install(key)
