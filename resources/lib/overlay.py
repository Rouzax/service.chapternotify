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


def _decide_layout(parsed_name, show_label_setting):
    """Return 'full', 'medium', or 'single' based on parser result + setting.

    - 'single': parser did not match the festival format; show the raw name only.
    - 'full': parser matched AND the user wants the label AND the chapter
      name actually included a [Label] tag.
    - 'medium': parser matched but either the user disabled the label or
      there was no [Label] tag to show.
    """
    has_parsed = bool(parsed_name["artist"])
    if not has_parsed:
        return "single"
    has_label_text = bool(parsed_name["label"])
    if show_label_setting and has_label_text:
        return "full"
    return "medium"


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
    opacity = min(100, max(0, int(addon.getSetting("opacity") or "70")))
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

    # Theme colors - accent border and separator at full opacity
    colors = THEME_COLORS.get(theme, THEME_COLORS[0])
    overlay.setProperty("accent", colors['accent'])
    overlay.setProperty("accentglow", colors['accentglow'])

    # Background - dark panel with configurable opacity
    alpha_hex = "{:02X}".format(int(opacity * 255 / 100))
    overlay.setProperty("bgvisible", "true" if show_bg else "false")
    overlay.setProperty("bgcolor", alpha_hex + "0D1117")

    if animation == 0:
        overlay.setProperty("animation", "fade")
    else:
        is_top = position_key.startswith("top_")
        overlay.setProperty("animation", "slide_down" if is_top else "slide_up")

    show_label_setting = addon.getSetting("show_label") == "true"
    layout = _decide_layout(parsed_name, show_label_setting)
    overlay.setProperty("layout", layout)

    if layout == "single":
        overlay.setProperty("raw", parsed_name["raw"])
    else:
        overlay.setProperty("prefix_track", "Track:")
        overlay.setProperty("track", parsed_name["track"])
        overlay.setProperty("prefix_artist", "Artist:")
        overlay.setProperty("artist", parsed_name["artist"])
        if layout == "full":
            overlay.setProperty("prefix_label", "Label:")
            overlay.setProperty("label", parsed_name["label"])

    overlay.show()
    return overlay
