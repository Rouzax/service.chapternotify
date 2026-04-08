# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
"""Manages this addon's keymap file at userdata/keymaps/service.chapternotify.xml.

Owns the full lifecycle: install, remove, sync to settings. Never reads,
parses, or modifies any other keymap file.
"""

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
