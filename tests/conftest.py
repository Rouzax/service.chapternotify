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

    Real Kodi behavior: Window(id) is a singleton per window_id - any two
    calls with the same id return the same backing store. This stub matches
    that behavior so tests that set a property on Window(10000) in one call
    and read it from a separate Window(10000) call see the same value.
    """

    _instances: dict = {}

    def __new__(cls, window_id=0):
        if window_id not in cls._instances:
            instance = super().__new__(cls)
            instance._window_id = window_id
            instance._properties = {}
            cls._instances[window_id] = instance
        return cls._instances[window_id]

    def __init__(self, window_id=0):
        pass  # already initialised in __new__

    def getProperty(self, key):
        return self._properties.get(key, "")

    def setProperty(self, key, value):
        self._properties[key] = value

    def clearProperty(self, key):
        self._properties.pop(key, None)


class _FakeWindowXMLDialog:
    """Stub for xbmcgui.WindowXMLDialog so addon dialog classes can subclass it.

    Stores properties in an instance dict so tests can assert what the
    overlay code wrote. The real Kodi class stores window properties
    on the dialog's backing window; this dict-backed version is a
    reasonable test approximation.
    """

    def __init__(self, *args, **kwargs):
        self._properties = {}

    def show(self):
        pass

    def close(self):
        pass

    def setProperty(self, key, value):
        self._properties[key] = value

    def getProperty(self, key):
        return self._properties.get(key, "")


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
    _FakeWindow._instances.clear()
    yield
    xbmc.executebuiltin.reset_mock()
    xbmc.log.reset_mock()
    xbmc.getInfoLabel.reset_mock()
    xbmcvfs.translatePath.reset_mock()
    xbmcvfs.exists.reset_mock()
    xbmcvfs.mkdirs.reset_mock()
    xbmcvfs.delete.reset_mock()
    _FakeWindow._instances.clear()
