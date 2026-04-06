import time
import xbmc
import xbmcaddon
from resources.lib.chapters import get_chapters, parse_chapter_name
from resources.lib.overlay import create_chapter_overlay


class ChapterPlayer(xbmc.Player):
    """Monitors playback and shows chapter notifications for configured paths."""

    def __init__(self):
        super().__init__()
        self._active = False
        self._chapters = []
        self._current_chapter_index = -1
        self._overlay = None
        self._overlay_show_time = 0
        self._duration = 5

    def onAVStarted(self):
        try:
            filepath = self.getPlayingFile()
        except RuntimeError:
            return

        if not self._matches_configured_path(filepath):
            xbmc.log("service.chapternotify: path not monitored: {}".format(filepath),
                     xbmc.LOGDEBUG)
            return

        chapters = get_chapters()
        if not chapters:
            xbmc.log("service.chapternotify: no chapters found", xbmc.LOGDEBUG)
            return

        addon = xbmcaddon.Addon("service.chapternotify")
        self._duration = int(addon.getSetting("duration") or "5")
        self._chapters = chapters
        self._current_chapter_index = -1
        self._active = True
        xbmc.log("service.chapternotify: monitoring {} chapters".format(len(chapters)),
                 xbmc.LOGINFO)

    def onPlayBackStopped(self):
        self._deactivate()

    def onPlayBackEnded(self):
        self._deactivate()

    def cleanup(self):
        self._deactivate()

    def tick(self):
        """Called from the main service loop every ~1 second.

        Checks chapter transitions and manages overlay lifetime.
        Must be called from the main thread.
        """
        if not self._active:
            return

        # Auto-hide overlay after duration
        if self._overlay is not None:
            if time.time() - self._overlay_show_time >= self._duration:
                self._dismiss_overlay()

        try:
            current_time = self.getTime()
        except RuntimeError:
            self._deactivate()
            return

        chapter_index = self._get_chapter_for_time(current_time)
        if chapter_index != self._current_chapter_index and chapter_index >= 0:
            self._current_chapter_index = chapter_index
            chapter = self._chapters[chapter_index]
            parsed = parse_chapter_name(chapter["name"])
            xbmc.log(
                "service.chapternotify: chapter {} - {}".format(
                    chapter_index + 1, chapter["name"]
                ),
                xbmc.LOGINFO,
            )
            self._dismiss_overlay()
            self._overlay = create_chapter_overlay(parsed)
            self._overlay_show_time = time.time()

    def _matches_configured_path(self, filepath):
        addon = xbmcaddon.Addon("service.chapternotify")
        for key in ("path1", "path2", "path3"):
            path = addon.getSetting(key)
            if path and filepath.startswith(path):
                return True
        return False

    def _deactivate(self):
        self._active = False
        self._chapters = []
        self._current_chapter_index = -1
        self._dismiss_overlay()

    def _dismiss_overlay(self):
        if self._overlay is not None:
            try:
                self._overlay.close()
            except RuntimeError:
                pass
            self._overlay = None

    def _get_chapter_for_time(self, current_time):
        """Return the index of the chapter that contains current_time."""
        result = -1
        for i, ch in enumerate(self._chapters):
            if current_time >= ch["time"]:
                result = i
            else:
                break
        return result
