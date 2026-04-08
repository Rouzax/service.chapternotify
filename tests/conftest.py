# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
"""Pytest configuration: mock the xbmc* modules so addon code can be imported
in a non-Kodi environment for unit testing.

Real Kodi behavior is verified via the manual smoke test matrix in
docs/plans/2026-04-08-button-trigger-design.md.
"""
# pyright: reportAttributeAccessIssue=false
import sys
import types
from unittest.mock import MagicMock

import pytest


def _make_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


class _FakePlayer:
    """Stub for xbmc.Player so addon classes can subclass it without a real Kodi."""

    def __init__(self, *args, **kwargs):
        pass

    def isPlaying(self):
        return False

    def getPlayingFile(self):
        return ""

    def getTotalTime(self):
        return 0.0

    def getTime(self):
        return 0.0


class _FakeWindow:
    """Stub for xbmcgui.Window with dict-backed property storage.

    Real Kodi behavior: window properties are global per-Kodi-process.
    This stub gives each Window(id) a fresh dict, which is a reasonable
    test approximation since tests can construct one inline and inspect it.
    """

    def __init__(self, window_id=0):
        self._window_id = window_id
        self._properties = {}

    def getProperty(self, key):
        return self._properties.get(key, "")

    def setProperty(self, key, value):
        self._properties[key] = value

    def clearProperty(self, key):
        self._properties.pop(key, None)


class _FakeWindowXMLDialog:
    """Stub for xbmcgui.WindowXMLDialog so addon dialog classes can subclass it."""

    def __init__(self, *args, **kwargs):
        pass

    def show(self):
        pass

    def close(self):
        pass

    def setProperty(self, key, value):
        pass

    def getProperty(self, key):
        return ""


# xbmc
xbmc = _make_module("xbmc")
xbmc.log = MagicMock()
xbmc.LOGDEBUG = 0
xbmc.LOGINFO = 1
xbmc.LOGWARNING = 2
xbmc.LOGERROR = 3
xbmc.LOGFATAL = 4
xbmc.executebuiltin = MagicMock()
xbmc.getInfoLabel = MagicMock(return_value="")
xbmc.Player = _FakePlayer
xbmc.Monitor = MagicMock
xbmc.sleep = MagicMock()


# xbmcgui
xbmcgui = _make_module("xbmcgui")
xbmcgui.Window = _FakeWindow
xbmcgui.WindowXMLDialog = _FakeWindowXMLDialog
xbmcgui.Dialog = MagicMock
xbmcgui.NOTIFICATION_INFO = "info"
xbmcgui.NOTIFICATION_WARNING = "warning"
xbmcgui.NOTIFICATION_ERROR = "error"


# xbmcaddon
xbmcaddon = _make_module("xbmcaddon")
xbmcaddon.Addon = MagicMock


# xbmcvfs
xbmcvfs = _make_module("xbmcvfs")
xbmcvfs.translatePath = MagicMock(side_effect=lambda p: p)
xbmcvfs.exists = MagicMock(return_value=False)
xbmcvfs.mkdirs = MagicMock(return_value=True)
xbmcvfs.delete = MagicMock(return_value=True)


@pytest.fixture(autouse=True)
def _reset_kodi_mocks():
    """Reset cumulative mock state between tests."""
    yield
    xbmc.executebuiltin.reset_mock()
    xbmc.log.reset_mock()
    xbmc.getInfoLabel.reset_mock()
    xbmcvfs.translatePath.reset_mock()
    xbmcvfs.exists.reset_mock()
    xbmcvfs.mkdirs.reset_mock()
    xbmcvfs.delete.reset_mock()
