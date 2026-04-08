# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Rouzax
import xbmc

if __name__ == "__main__":
    try:
        from resources.lib import log
        log.init()
        log.info("Service starting", event="service.start")

        from resources.lib.player import ChapterPlayer, ChapterMonitor
        player = ChapterPlayer()
        monitor = ChapterMonitor(player)
        log.info("Service started", event="service.ready")
    except Exception as e:
        xbmc.log("[ChapterNotify] Failed to start: {}".format(e), xbmc.LOGERROR)
        import traceback
        xbmc.log("[ChapterNotify] {}".format(traceback.format_exc()), xbmc.LOGERROR)
        # Keep service alive to avoid Kodi restart loops
        fallback = xbmc.Monitor()
        while not fallback.abortRequested():
            if fallback.waitForAbort(10):
                break
        raise SystemExit

    while not monitor.abortRequested():
        player.tick()
        interval_s = player.get_tick_interval_ms() / 1000.0
        if monitor.waitForAbort(interval_s):
            break

    player.cleanup()
    log.info("Service stopped", event="service.stop")
