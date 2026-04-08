# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
def test_harness_imports():
    """Verify the conftest mocks expose the API the addon code uses."""
    import xbmc
    import xbmcgui
    import xbmcvfs

    # Constants the addon uses
    assert xbmc.LOGERROR == 3
    assert callable(xbmc.log)
    assert callable(xbmc.executebuiltin)
    assert callable(xbmc.getInfoLabel)

    # Stub classes that addon code subclasses
    assert callable(xbmc.Player)
    assert callable(xbmcgui.Window)
    assert callable(xbmcgui.WindowXMLDialog)

    # Window stub gives functional property storage
    win = xbmcgui.Window(10000)
    win.setProperty("test.key", "value")
    assert win.getProperty("test.key") == "value"
    win.clearProperty("test.key")
    assert win.getProperty("test.key") == ""

    # translatePath is a pass-through (no hidden rewrites)
    assert xbmcvfs.translatePath("special://userdata/keymaps/") == "special://userdata/keymaps/"
