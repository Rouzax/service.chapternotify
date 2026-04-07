# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import sys
import xbmc

if __name__ == "__main__":
    args = sys.argv[1:]
    action = args[0] if args else ""

    if action == "test_overlay":
        from resources.lib.chapters import parse_chapter_name
        from resources.lib.overlay import create_chapter_overlay

        parsed = parse_chapter_name("FISHER & AR/CO - Ocean [CATCH & RELEASE]")
        overlay = create_chapter_overlay(parsed)
        xbmc.sleep(6000)
        try:
            overlay.close()
        except RuntimeError:
            pass
