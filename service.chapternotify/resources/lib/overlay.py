# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import xbmcaddon
import xbmcgui

THEME_COLORS = {
    0: {  # Golden Hour
        'accent': 'FFF5A623',
        'accentglow': 'FFF5C564',
    },
    1: {  # Ultraviolet
        'accent': 'FFA78BFA',
        'accentglow': 'FFC4B5FD',
    },
    2: {  # Ember
        'accent': 'FFF87171',
        'accentglow': 'FFFCA5A5',
    },
    3: {  # Nightfall
        'accent': 'FF60A5FA',
        'accentglow': 'FF93C5FD',
    },
}

class ChapterOverlay(xbmcgui.WindowXMLDialog):
    """Overlay that displays chapter info.

    Any button press closes the overlay instantly (no animation).
    """

    def onInit(self):
        pass

    def onAction(self, action):
        self.setProperty("quickclose", "true")
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
    theme = int(addon.getSetting("theme") or "0")
    show_bg = addon.getSetting("show_background") == "true"

    overlay = ChapterOverlay(
        "chapternotify.xml",
        addon_path,
        "default",
        "1080i",
    )

    position_key = _get_position_key(position)
    overlay.setProperty("position", position_key)

    # Theme colors — accent border and separator at full opacity
    colors = THEME_COLORS.get(theme, THEME_COLORS[0])
    overlay.setProperty("accent", colors['accent'])
    overlay.setProperty("accentglow", colors['accentglow'])

    # Background — dark panel with configurable opacity
    alpha_hex = "{:02X}".format(int(opacity * 255 / 100))
    overlay.setProperty("bgvisible", "true" if show_bg else "false")
    overlay.setProperty("bgcolor", alpha_hex + "0D1117")

    if animation == 0:
        overlay.setProperty("animation", "fade")
    else:
        is_top = position_key.startswith("top_")
        overlay.setProperty("animation", "slide_down" if is_top else "slide_up")

    if parsed_name["artist"]:
        overlay.setProperty("prefix_artist", "Track:")
        overlay.setProperty("artist", parsed_name["track"])
        overlay.setProperty("prefix_track", "Artist:")
        overlay.setProperty("track", parsed_name["artist"])
        if parsed_name["label"]:
            overlay.setProperty("prefix_label", "Label:")
            overlay.setProperty("label", parsed_name["label"])
    else:
        overlay.setProperty("artist", parsed_name["raw"])

    overlay.show()
    return overlay
