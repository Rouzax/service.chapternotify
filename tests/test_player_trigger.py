# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import time
from unittest.mock import MagicMock, patch


class _Stub:
    """Minimal stand-in for ChapterPlayer that exposes only the fields
    `_handle_manual_trigger` reads/writes."""

    def __init__(self):
        self._last_trigger_ts = 0
        self.fired = False

    def _on_manual_trigger(self):
        self.fired = True


def _make_window(prop_value):
    win = MagicMock()
    win.getProperty.return_value = prop_value
    return win


def test_handle_manual_trigger_fires_on_fresh_timestamp():
    from resources.lib import player
    stub = _Stub()
    now_ms = int(time.time() * 1000)
    win = _make_window(str(now_ms))
    with patch("xbmcgui.Window", return_value=win):
        player.ChapterPlayer._handle_manual_trigger(stub)  # type: ignore[arg-type]
    assert stub.fired is True
    assert stub._last_trigger_ts == now_ms
    win.clearProperty.assert_called_once_with(player.TRIGGER_PROPERTY)


def test_handle_manual_trigger_ignores_empty_property():
    from resources.lib import player
    stub = _Stub()
    win = _make_window("")
    with patch("xbmcgui.Window", return_value=win):
        player.ChapterPlayer._handle_manual_trigger(stub)  # type: ignore[arg-type]
    assert stub.fired is False


def test_handle_manual_trigger_ignores_garbage():
    from resources.lib import player
    stub = _Stub()
    win = _make_window("not-a-number")
    with patch("xbmcgui.Window", return_value=win):
        player.ChapterPlayer._handle_manual_trigger(stub)  # type: ignore[arg-type]
    assert stub.fired is False
    win.clearProperty.assert_called_once()


def test_handle_manual_trigger_ignores_duplicate_timestamp():
    from resources.lib import player
    stub = _Stub()
    now_ms = int(time.time() * 1000)
    stub._last_trigger_ts = now_ms
    win = _make_window(str(now_ms))
    with patch("xbmcgui.Window", return_value=win):
        player.ChapterPlayer._handle_manual_trigger(stub)  # type: ignore[arg-type]
    assert stub.fired is False


def test_handle_manual_trigger_discards_stale():
    from resources.lib import player
    stub = _Stub()
    stale_ms = int(time.time() * 1000) - 5000  # 5 seconds old
    win = _make_window(str(stale_ms))
    with patch("xbmcgui.Window", return_value=win):
        player.ChapterPlayer._handle_manual_trigger(stub)  # type: ignore[arg-type]
    assert stub.fired is False
    assert stub._last_trigger_ts == stale_ms  # consumed but not fired
    win.clearProperty.assert_called_once()
