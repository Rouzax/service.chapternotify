import threading
import xbmcaddon
import xbmcgui


class ChapterOverlay(xbmcgui.WindowXMLDialog):
    """Overlay window that displays chapter info and auto-dismisses."""

    def __init__(self, *args, **kwargs):
        self._close_timer = None

    def onInit(self):
        pass

    def onAction(self, action):
        # Any key/remote press dismisses the overlay
        self.cancel_timer()
        self.close()

    def cancel_timer(self):
        if self._close_timer is not None:
            self._close_timer.cancel()
            self._close_timer = None


def _get_position_key(setting_value):
    positions = {0: "bottom_center", 1: "bottom_left", 2: "top_right"}
    return positions.get(setting_value, "bottom_center")


def _get_opacity_hex(percent):
    """Convert opacity percentage (40-90) to hex alpha value."""
    alpha = int(percent * 255 / 100)
    return "{:02X}000000".format(alpha)


def show_chapter_overlay(parsed_name):
    """Show the chapter overlay with the given parsed chapter info.

    Args:
        parsed_name: dict with keys "artist", "track", "label", "raw"
    """
    addon = xbmcaddon.Addon("service.chapternotify")
    addon_path = addon.getAddonInfo("path")

    duration = int(addon.getSetting("duration") or "5")
    position = int(addon.getSetting("position") or "0")
    opacity = int(addon.getSetting("opacity") or "70")
    animation = int(addon.getSetting("animation") or "0")

    overlay = ChapterOverlay(
        "chapternotify.xml",
        addon_path,
        "default",
        "1080i",
    )

    # Set window properties before showing
    overlay.setProperty("position", _get_position_key(position))
    overlay.setProperty("bgcolor", _get_opacity_hex(opacity))
    overlay.setProperty("animation", "fade" if animation == 0 else "slide")

    if parsed_name["artist"]:
        overlay.setProperty("artist", parsed_name["artist"])
        overlay.setProperty("track", parsed_name["track"])
        overlay.setProperty("label", parsed_name["label"])
    else:
        overlay.setProperty("artist", parsed_name["raw"])
        overlay.setProperty("track", "")
        overlay.setProperty("label", "")

    def _safe_close(ovl):
        try:
            ovl.close()
        except RuntimeError:
            pass

    overlay.show()
    # Auto-dismiss after duration
    timer = threading.Timer(duration, _safe_close, args=[overlay])
    overlay._close_timer = timer
    timer.start()

    return overlay
