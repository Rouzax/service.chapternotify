import xbmc
import xbmcaddon

ADDON_ID = "service.chapternotify"
PREFIX = "[ChapterNotify]"

_debug_enabled = False


def init():
    """Initialize logging from addon settings."""
    global _debug_enabled
    try:
        addon = xbmcaddon.Addon(ADDON_ID)
        _debug_enabled = addon.getSetting("debug") == "true"
    except RuntimeError:
        _debug_enabled = False


def info(message, **kwargs):
    """Log at INFO level (always visible in Kodi log)."""
    _log(message, xbmc.LOGINFO, **kwargs)


def debug(message, **kwargs):
    """Log at DEBUG level when debug disabled, INFO when debug enabled."""
    if _debug_enabled:
        _log(message, xbmc.LOGINFO, **kwargs)
    else:
        _log(message, xbmc.LOGDEBUG, **kwargs)


def warning(message, **kwargs):
    """Log at WARNING level (always visible)."""
    _log(message, xbmc.LOGWARNING, **kwargs)


def error(message, **kwargs):
    """Log at ERROR level (always visible)."""
    _log(message, xbmc.LOGERROR, **kwargs)


def _log(message, level, **kwargs):
    """Format and write a log line."""
    if kwargs:
        pairs = ", ".join("{}={}".format(k, v) for k, v in kwargs.items())
        line = "{} {} | {}".format(PREFIX, message, pairs)
    else:
        line = "{} {}".format(PREFIX, message)
    xbmc.log(line, level)
