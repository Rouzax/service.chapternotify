# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
"""Pytest configuration: mock the xbmc* modules so addon code can be imported
in a non-Kodi environment for unit testing.

Real Kodi behavior is verified via the manual smoke test matrix in
docs/plans/2026-04-08-button-trigger-design.md.
"""
import sys
import types
from unittest.mock import MagicMock


def _make_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


# xbmc
xbmc = _make_module("xbmc")
xbmc.log = MagicMock()
xbmc.LOGDEBUG = 0
xbmc.LOGINFO = 1
xbmc.LOGWARNING = 2
xbmc.LOGERROR = 3
xbmc.LOGFATAL = 4
xbmc.executebuiltin = MagicMock()
xbmc.Player = MagicMock
xbmc.Monitor = MagicMock
xbmc.sleep = MagicMock()


# xbmcgui
xbmcgui = _make_module("xbmcgui")
xbmcgui.Window = MagicMock
xbmcgui.WindowXMLDialog = MagicMock
xbmcgui.Dialog = MagicMock
xbmcgui.NOTIFICATION_INFO = "info"
xbmcgui.NOTIFICATION_WARNING = "warning"
xbmcgui.NOTIFICATION_ERROR = "error"


# xbmcaddon
xbmcaddon = _make_module("xbmcaddon")
xbmcaddon.Addon = MagicMock


# xbmcvfs
xbmcvfs = _make_module("xbmcvfs")
xbmcvfs.translatePath = MagicMock(side_effect=lambda p: p.replace("special://userdata/", "/tmp/test_userdata/"))
xbmcvfs.exists = MagicMock(return_value=False)
xbmcvfs.mkdirs = MagicMock(return_value=True)
xbmcvfs.delete = MagicMock(return_value=True)
