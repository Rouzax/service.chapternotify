# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import sys
import xbmc

if __name__ == "__main__":
    args = sys.argv[1:]
    action = args[0] if args else ""

    if action == "show":
        # Lightweight signal to running service - no resources.lib imports
        # to keep cold-start cost minimal (~50-100ms).
        import time
        import xbmcgui
        xbmcgui.Window(10000).setProperty(
            "chapternotify.trigger",
            str(int(time.time() * 1000))
        )

    elif action == "remove_keymap":
        from resources.lib import keymap
        from resources.lib import log
        log.init()
        import xbmcgui
        if keymap.is_installed():
            ok = keymap.remove()
            if ok:
                xbmcgui.Dialog().notification(
                    "Chapter Notify",
                    "Keymap binding removed",
                    xbmcgui.NOTIFICATION_INFO,
                    3000,
                )
            else:
                xbmcgui.Dialog().notification(
                    "Chapter Notify",
                    "Failed to remove keymap (see log)",
                    xbmcgui.NOTIFICATION_ERROR,
                    3000,
                )
        else:
            xbmcgui.Dialog().notification(
                "Chapter Notify",
                "No keymap binding to remove",
                xbmcgui.NOTIFICATION_INFO,
                3000,
            )

    elif action == "test_overlay":
        from resources.lib import log
        from resources.lib.chapters import parse_chapter_name
        from resources.lib.overlay import create_chapter_overlay
        log.init()

        parsed = parse_chapter_name("FISHER & AR/CO - Ocean [CATCH & RELEASE]")
        overlay = create_chapter_overlay(parsed)
        xbmc.sleep(6000)
        try:
            overlay.close()
        except RuntimeError:
            pass
