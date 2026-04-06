import xbmc
from resources.lib.player import ChapterPlayer

if __name__ == "__main__":
    monitor = xbmc.Monitor()
    player = ChapterPlayer()
    xbmc.log("service.chapternotify: started", xbmc.LOGINFO)

    while not monitor.abortRequested():
        player.tick()
        if monitor.waitForAbort(1):
            break

    player.cleanup()
    xbmc.log("service.chapternotify: stopped", xbmc.LOGINFO)
