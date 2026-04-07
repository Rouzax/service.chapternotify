# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import xbmc

if __name__ == "__main__":
    monitor = xbmc.Monitor()

    try:
        from resources.lib import log
        log.init()
        log.info("Service starting", event="service.start")

        from resources.lib.player import ChapterPlayer
        player = ChapterPlayer()
        log.info("Service started", event="service.ready")
    except Exception as e:
        xbmc.log("[ChapterNotify] Failed to start: {}".format(e), xbmc.LOGERROR)
        import traceback
        xbmc.log("[ChapterNotify] {}".format(traceback.format_exc()), xbmc.LOGERROR)
        # Still need to keep service alive to avoid Kodi restart loops
        while not monitor.abortRequested():
            if monitor.waitForAbort(10):
                break
        raise SystemExit

    while not monitor.abortRequested():
        player.tick()
        if monitor.waitForAbort(1):
            break

    player.cleanup()
    log.info("Service stopped", event="service.stop")
