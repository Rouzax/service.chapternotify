import threading
import xbmc
import xbmcaddon
from resources.lib.chapters import get_chapters, parse_chapter_name
from resources.lib.overlay import show_chapter_overlay


class ChapterPlayer(xbmc.Player):
    """Monitors playback and shows chapter notifications for configured paths."""

    def __init__(self):
        super().__init__()
        self._polling = False
        self._poll_thread = None
        self._chapters = []
        self._current_chapter_index = -1
        self._current_overlay = None

    def onAVStarted(self):
        try:
            filepath = self.getPlayingFile()
        except RuntimeError:
            return

        if not self._matches_configured_path(filepath):
            return

        chapters = get_chapters()
        if not chapters:
            return

        self._chapters = chapters
        self._current_chapter_index = -1
        self._start_polling()

    def onPlayBackStopped(self):
        self._stop_polling()

    def onPlayBackEnded(self):
        self._stop_polling()

    def cleanup(self):
        self._stop_polling()

    def _matches_configured_path(self, filepath):
        addon = xbmcaddon.Addon("service.chapternotify")
        for key in ("path1", "path2", "path3"):
            path = addon.getSetting(key)
            if path and filepath.startswith(path):
                return True
        return False

    def _start_polling(self):
        self._stop_polling()
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _stop_polling(self):
        self._polling = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=2)
            self._poll_thread = None
        self._chapters = []
        self._current_chapter_index = -1
        self._dismiss_overlay()

    def _dismiss_overlay(self):
        if self._current_overlay is not None:
            try:
                self._current_overlay.cancel_timer()
                self._current_overlay.close()
            except RuntimeError:
                pass
            self._current_overlay = None

    def _poll_loop(self):
        monitor = xbmc.Monitor()
        while self._polling and not monitor.abortRequested():
            try:
                current_time = self.getTime()
            except RuntimeError:
                break

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
                self._current_overlay = show_chapter_overlay(parsed)

            if monitor.waitForAbort(1):
                break

    def _get_chapter_for_time(self, current_time):
        """Return the index of the chapter that contains current_time."""
        result = -1
        for i, ch in enumerate(self._chapters):
            if current_time >= ch["time"]:
                result = i
            else:
                break
        return result
