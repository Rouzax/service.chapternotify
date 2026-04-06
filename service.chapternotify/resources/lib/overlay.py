import xbmcaddon
import xbmcgui

# Action IDs that should dismiss the overlay
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_SELECT_ITEM = 7
ACTION_STOP = 13


class ChapterOverlay(xbmcgui.WindowXMLDialog):
    """Non-blocking overlay that displays chapter info."""

    def onInit(self):
        pass

    def onAction(self, action):
        action_id = action.getId()
        if action_id in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK,
                         ACTION_SELECT_ITEM, ACTION_STOP):
            self.close()


def _get_position_key(setting_value):
    positions = {
        0: "bottom_center",
        1: "bottom_left",
        2: "bottom_right",
        3: "top_center",
        4: "top_left",
        5: "top_right",
    }
    return positions.get(setting_value, "bottom_center")


def _get_opacity_hex(percent):
    """Convert opacity percentage (40-90) to hex alpha value."""
    alpha = int(percent * 255 / 100)
    return "{:02X}000000".format(alpha)


def create_chapter_overlay(parsed_name):
    """Create and show the chapter overlay.

    Returns the overlay window instance. Caller is responsible for
    closing it (via overlay.close()) when the display duration expires
    or a new chapter starts.
    """
    addon = xbmcaddon.Addon("service.chapternotify")
    addon_path = addon.getAddonInfo("path")

    position = int(addon.getSetting("position") or "0")
    opacity = int(addon.getSetting("opacity") or "70")
    animation = int(addon.getSetting("animation") or "0")

    overlay = ChapterOverlay(
        "chapternotify.xml",
        addon_path,
        "default",
        "1080i",
    )

    overlay.setProperty("position", _get_position_key(position))
    overlay.setProperty("bgcolor", _get_opacity_hex(opacity))
    overlay.setProperty("animation", "fade" if animation == 0 else "slide")

    if parsed_name["artist"]:
        overlay.setProperty("artist", "Artist:  " + parsed_name["artist"])
        overlay.setProperty("track", "Track:   " + parsed_name["track"])
        overlay.setProperty("label",
                            "Label:   " + parsed_name["label"] if parsed_name["label"] else "")
    else:
        overlay.setProperty("artist", parsed_name["raw"])
        overlay.setProperty("track", "")
        overlay.setProperty("label", "")

    overlay.show()
    return overlay
