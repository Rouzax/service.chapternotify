# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import time
import xbmc
import xbmcaddon
import xbmcgui
from resources.lib import keymap, log
from resources.lib.chapters import get_current_chapter, parse_chapter_name
from resources.lib.overlay import create_chapter_overlay

MODE_AUTO = 0
MODE_MANUAL = 1
MODE_BOTH = 2

TRIGGER_PROPERTY = "chapternotify.trigger"
STALE_THRESHOLD_MS = 3000


class ChapterPlayer(xbmc.Player):
    """Monitors playback and shows chapter notifications for configured paths."""

    def __init__(self):
        super().__init__()
        self._active = False
        self._current_chapter = -1
        self._overlay = None
        self._overlay_show_time = 0
        self._duration = 5
        self._trigger_mode = MODE_AUTO
        self._trigger_button = 0
        self._last_trigger_ts = 0
        self._load_trigger_settings()
        # Clear any stale trigger property from a previous session
        try:
            xbmcgui.Window(10000).clearProperty(TRIGGER_PROPERTY)
        except Exception:
            pass
        keymap.sync(self._trigger_mode, self._trigger_button)

    def _load_trigger_settings(self):
        addon = xbmcaddon.Addon("service.chapternotify")
        try:
            self._trigger_mode = int(addon.getSetting("trigger_mode") or "0")
        except ValueError:
            self._trigger_mode = MODE_AUTO
        try:
            self._trigger_button = int(addon.getSetting("trigger_button") or "0")
        except ValueError:
            self._trigger_button = 0

    def reload_settings(self):
        """Re-read settings and reconcile keymap state. Called by ChapterMonitor
        when the user changes any addon setting."""
        old_mode = self._trigger_mode
        old_button = self._trigger_button
        self._load_trigger_settings()
        # Re-read duration since it can change live too
        addon = xbmcaddon.Addon("service.chapternotify")
        try:
            self._duration = int(addon.getSetting("duration") or "5")
        except ValueError:
            self._duration = 5
        if (self._trigger_mode != old_mode) or (self._trigger_button != old_button):
            log.info("Trigger settings changed",
                     event="settings.trigger.change",
                     mode=self._trigger_mode, button=self._trigger_button)
            keymap.sync(self._trigger_mode, self._trigger_button)

    def get_tick_interval_ms(self):
        """Adaptive tick interval: 250ms in Manual/Both for responsive button trigger,
        1000ms in Auto-only to minimize wakeups."""
        if self._trigger_mode in (MODE_MANUAL, MODE_BOTH):
            return 250
        return 1000

    def onAVStarted(self):
        try:
            filepath = self.getPlayingFile()
        except RuntimeError:
            return

        log.debug("Playback started", event="playback.start", file=filepath)

        if not self._matches_configured_path(filepath):
            log.debug("Path not monitored", event="playback.skip")
            return

        log.info("Path matched, monitoring chapters", event="playback.match", file=filepath)

        addon = xbmcaddon.Addon("service.chapternotify")
        self._duration = int(addon.getSetting("duration") or "5")
        self._current_chapter = -1
        self._active = True

    def onPlayBackStopped(self):
        if self._active:
            log.debug("Playback stopped", event="playback.stopped")
        self._deactivate()

    def onPlayBackEnded(self):
        if self._active:
            log.debug("Playback ended", event="playback.ended")
        self._deactivate()

    def cleanup(self):
        self._deactivate()

    def tick(self):
        """Called from the main service loop on an adaptive interval."""
        # 1. Auto-hide expired overlay (regardless of mode)
        if self._overlay is not None:
            if time.time() - self._overlay_show_time >= self._duration:
                self._dismiss_overlay()

        # 2. Handle manual trigger if Manual or Both mode
        if self._trigger_mode in (MODE_MANUAL, MODE_BOTH):
            self._handle_manual_trigger()

        # 3. Auto chapter detection: only if Auto/Both AND on a monitored path
        if self._trigger_mode in (MODE_AUTO, MODE_BOTH) and self._active:
            self._poll_chapter_change()

    def _poll_chapter_change(self):
        """Existing auto chapter-change detection, extracted from tick()."""
        chapter_info = get_current_chapter()
        if chapter_info is None:
            return

        chapter_num = chapter_info["chapter"]
        if chapter_num != self._current_chapter:
            self._current_chapter = chapter_num
            parsed = parse_chapter_name(chapter_info["name"])
            log.info("Chapter changed",
                     event="chapter.change",
                     chapter=chapter_num,
                     total=chapter_info["count"],
                     name=chapter_info["name"])
            self._dismiss_overlay()
            try:
                self._overlay = create_chapter_overlay(parsed)
                self._overlay_show_time = time.time()
            except Exception as e:
                log.error("Failed to show overlay",
                          event="overlay.error", error=str(e))

    def _matches_configured_path(self, filepath):
        addon = xbmcaddon.Addon("service.chapternotify")
        for key in ("path1", "path2", "path3"):
            path = addon.getSetting(key)
            log.debug("Checking path setting", event="path.check", key=key, configured=path)
            if path and filepath.startswith(path):
                log.debug("Path matched", event="path.match", key=key)
                return True
        return False

    def _deactivate(self):
        self._active = False
        self._current_chapter = -1
        self._dismiss_overlay()

    def _dismiss_overlay(self):
        if self._overlay is not None:
            try:
                self._overlay.close()
            except RuntimeError:
                pass
            self._overlay = None

    def _handle_manual_trigger(self):
        """Read the trigger property; if fresh and unseen, call _on_manual_trigger.

        Idempotent: ignores duplicate or stale timestamps. Always clears the
        property after reading a non-empty value, so it never lingers.
        """
        win = xbmcgui.Window(10000)
        raw = win.getProperty(TRIGGER_PROPERTY)
        if not raw:
            return

        try:
            ts_ms = int(raw)
        except ValueError:
            log.debug("Manual trigger: garbage value",
                      event="manual.trigger.garbage", raw=raw)
            win.clearProperty(TRIGGER_PROPERTY)
            return

        if ts_ms == self._last_trigger_ts:
            return

        now_ms = int(time.time() * 1000)
        if now_ms - ts_ms > STALE_THRESHOLD_MS:
            log.debug("Manual trigger: stale",
                      event="manual.trigger.stale",
                      age_ms=(now_ms - ts_ms))
            self._last_trigger_ts = ts_ms
            win.clearProperty(TRIGGER_PROPERTY)
            return

        log.debug("Manual trigger: received",
                  event="manual.trigger.received", ts_ms=ts_ms)
        self._last_trigger_ts = ts_ms
        win.clearProperty(TRIGGER_PROPERTY)
        self._on_manual_trigger()

    def _on_manual_trigger(self):
        """Toggle: if overlay is showing, dismiss. Otherwise show current chapter
        info regardless of monitored-path filter. Silent no-op if no chapter info.
        """
        # Toggle off if already visible
        if self._overlay is not None:
            log.debug("Manual trigger: toggling off", event="manual.toggle.off")
            self._dismiss_overlay()
            return

        # Show: fetch chapter info regardless of path filter
        chapter_info = get_current_chapter()
        if chapter_info is None:
            log.debug("Manual trigger: no chapter info available",
                      event="manual.noinfo")
            return

        parsed = parse_chapter_name(chapter_info["name"])
        log.info("Manual trigger: showing overlay",
                 event="manual.show",
                 chapter=chapter_info["chapter"])
        try:
            self._overlay = create_chapter_overlay(parsed)
            self._overlay_show_time = time.time()
            # Sync _current_chapter so Auto-mode (in Both) does not immediately
            # re-show the same chapter on the next tick.
            self._current_chapter = chapter_info["chapter"]
        except Exception as e:
            log.error("Manual trigger: overlay failed",
                      event="manual.error", error=str(e))


class ChapterMonitor(xbmc.Monitor):
    """Monitor subclass that forwards onSettingsChanged to the player."""

    def __init__(self, player):
        super().__init__()
        self._player = player

    def onSettingsChanged(self):
        log.debug("Settings changed", event="settings.changed")
        self._player.reload_settings()
