import time
import xbmc
import xbmcaddon
from resources.lib import log
from resources.lib.chapters import get_current_chapter, parse_chapter_name
from resources.lib.overlay import create_chapter_overlay


class ChapterPlayer(xbmc.Player):
    """Monitors playback and shows chapter notifications for configured paths."""

    def __init__(self):
        super().__init__()
        self._active = False
        self._current_chapter = -1
        self._overlay = None
        self._overlay_show_time = 0
        self._duration = 5

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
        """Called from the main service loop every ~1 second."""
        if not self._active:
            return

        # Auto-hide overlay after duration
        if self._overlay is not None:
            if time.time() - self._overlay_show_time >= self._duration:
                self._dismiss_overlay()

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
                log.error("Failed to show overlay", event="overlay.error", error=str(e))

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
