# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
def test_harness_imports():
    """Verify the conftest mocks let us import xbmc without a real Kodi."""
    import xbmc
    import xbmcgui
    import xbmcvfs
    assert xbmc is not None
    assert xbmcgui is not None
    assert xbmcvfs is not None
