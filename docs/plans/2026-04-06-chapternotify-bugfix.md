# service.chapternotify Bugfix & Hardening Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all bugs found during code audit — writable path error, thread-unsafe GUI calls, input swallowing, broken XML includes, missing error handling, and addon.xml issues.

**Architecture:** Seven targeted fixes across settings, overlay, player, chapters, and XML. Each fix is independent except Task 3 (overlay rewrite) which depends on Task 2 (XML fix).

**Tech Stack:** Python 3 (Kodi addon API), Kodi XML skinning, JSON-RPC.

---

### Task 1: Fix path settings writable error

The path settings require writable folders by default. We only read from these paths — add `<writable>false</writable>`.

**Files:**
- Modify: `service.chapternotify/resources/settings.xml`

**Step 1: Add writable constraint to all three path settings**

In each `<constraints>` block for path1, path2, path3, add `<writable>false</writable>` after `<allowempty>true</allowempty>`:

```xml
<constraints>
    <allowempty>true</allowempty>
    <writable>false</writable>
    <sources>
        <source>videos</source>
    </sources>
</constraints>
```

**Step 2: Validate XML**

```bash
python3 -c "import xml.etree.ElementTree as ET; ET.parse('service.chapternotify/resources/settings.xml'); print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add service.chapternotify/resources/settings.xml
git commit -m "fix: allow selecting read-only paths in settings"
```

---

### Task 2: Fix overlay XML — replace broken inline includes with duplicated controls and add Includes.xml

The current `<include name="ChapterNotifyContent">` defined inside the dialog XML does not work for addon WindowXMLDialog. Addon dialog XML files rely on the skin's global include system, not inline definitions.

**Solution:** Create a separate `Includes.xml` in the skin directory that Kodi will load for include resolution.

**Files:**
- Create: `service.chapternotify/resources/skins/default/1080i/Includes.xml`
- Modify: `service.chapternotify/resources/skins/default/1080i/chapternotify.xml`

**Step 1: Create Includes.xml with the shared content definition**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<includes>
    <include name="ChapterNotifyContent">
        <!-- Background -->
        <control type="image" id="100">
            <left>0</left>
            <top>0</top>
            <width>700</width>
            <height>140</height>
            <texture colordiffuse="$INFO[Window.Property(bgcolor)]">colors/white.png</texture>
        </control>

        <!-- Artist label -->
        <control type="label" id="101">
            <left>30</left>
            <top>18</top>
            <width>640</width>
            <height>40</height>
            <font>font13</font>
            <textcolor>FFFFFFFF</textcolor>
            <shadowcolor>AA000000</shadowcolor>
            <label>$INFO[Window.Property(artist)]</label>
        </control>

        <!-- Track label -->
        <control type="label" id="102">
            <left>30</left>
            <top>58</top>
            <width>640</width>
            <height>35</height>
            <font>font12</font>
            <textcolor>FFFFFFFF</textcolor>
            <shadowcolor>AA000000</shadowcolor>
            <label>$INFO[Window.Property(track)]</label>
        </control>

        <!-- Label (record label) -->
        <control type="label" id="103">
            <left>30</left>
            <top>95</top>
            <width>640</width>
            <height>30</height>
            <font>font10</font>
            <textcolor>99FFFFFF</textcolor>
            <label>$INFO[Window.Property(label)]</label>
        </control>
    </include>
</includes>
```

**Step 2: Rewrite chapternotify.xml to reference the include and remove inline definition**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<window type="dialog">
    <zorder>3</zorder>
    <defaultcontrol>-1</defaultcontrol>

    <!-- Fade animations -->
    <animation effect="fade" start="0" end="100" time="500" condition="String.IsEqual(Window.Property(animation),fade)">WindowOpen</animation>
    <animation effect="fade" start="100" end="0" time="500" condition="String.IsEqual(Window.Property(animation),fade)">WindowClose</animation>

    <!-- Slide animations -->
    <animation effect="slide" start="0,80" end="0,0" time="400" tween="sine" easing="out" condition="String.IsEqual(Window.Property(animation),slide)">WindowOpen</animation>
    <animation effect="slide" start="0,0" end="0,80" time="400" tween="sine" easing="in" condition="String.IsEqual(Window.Property(animation),slide)">WindowClose</animation>

    <controls>
        <!-- Bottom Center -->
        <control type="group">
            <visible>String.IsEqual(Window.Property(position),bottom_center)</visible>
            <centerleft>50%</centerleft>
            <bottom>120</bottom>
            <width>700</width>
            <height>140</height>
            <include>ChapterNotifyContent</include>
        </control>

        <!-- Bottom Left -->
        <control type="group">
            <visible>String.IsEqual(Window.Property(position),bottom_left)</visible>
            <left>60</left>
            <bottom>120</bottom>
            <width>700</width>
            <height>140</height>
            <include>ChapterNotifyContent</include>
        </control>

        <!-- Top Right -->
        <control type="group">
            <visible>String.IsEqual(Window.Property(position),top_right)</visible>
            <right>60</right>
            <top>60</top>
            <width>700</width>
            <height>140</height>
            <include>ChapterNotifyContent</include>
        </control>
    </controls>
</window>
```

Key changes:
- Added `<defaultcontrol>-1</defaultcontrol>` to prevent focus issues on notification overlay
- Changed `<include content="ChapterNotifyContent" />` to `<include>ChapterNotifyContent</include>` (correct Kodi syntax)
- Removed the inline `<include name="ChapterNotifyContent">` definition block

**Step 3: Validate both XML files**

```bash
python3 -c "
import xml.etree.ElementTree as ET
ET.parse('service.chapternotify/resources/skins/default/1080i/Includes.xml'); print('Includes.xml OK')
ET.parse('service.chapternotify/resources/skins/default/1080i/chapternotify.xml'); print('chapternotify.xml OK')
"
```

**Step 4: Commit**

```bash
git add service.chapternotify/resources/skins/default/1080i/
git commit -m "fix: move include to Includes.xml, add defaultcontrol"
```

---

### Task 3: Rewrite overlay.py — thread-safe GUI, proper input handling

Three issues in overlay.py:
1. `overlay.show()` called from background thread — GUI operations must run on main thread
2. `onAction` eats all input — should only dismiss on back/escape, pass others through
3. Timer cleanup is not thread-safe

**Solution:** Instead of calling `show()` from the poll thread, use a flag + the main service loop pattern. Actually, the simplest Kodi-idiomatic approach: use `xbmc.executebuiltin('ActivateWindow(...)')` — but that doesn't work for custom addon windows. 

The real fix: overlay creation and show must happen on the calling thread. In Kodi addons, `show()` (non-blocking) is allowed from service threads as long as it's a single call. The actual issue is that `threading.Timer` fires `close()` from yet another thread. Fix: use Kodi's built-in visibility timeout mechanism or poll for close timing in the same thread.

Simplest correct approach: don't use `threading.Timer` at all. Track the overlay show time, and let the poll loop handle closing it when the duration expires.

**Files:**
- Modify: `service.chapternotify/resources/lib/overlay.py`
- Modify: `service.chapternotify/resources/lib/player.py`

**Step 1: Rewrite overlay.py**

```python
import xbmc
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
    positions = {0: "bottom_center", 1: "bottom_left", 2: "top_right"}
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
        overlay.setProperty("artist", parsed_name["artist"])
        overlay.setProperty("track", parsed_name["track"])
        overlay.setProperty("label", parsed_name["label"])
    else:
        overlay.setProperty("artist", parsed_name["raw"])
        overlay.setProperty("track", "")
        overlay.setProperty("label", "")

    overlay.show()
    return overlay
```

Key changes:
- Removed `threading` import entirely — no more Timer
- `onAction` only closes on back/escape/select/stop, all other actions pass through naturally (no super() call needed since we don't call close())
- Renamed to `create_chapter_overlay` — returns the window, caller manages lifetime
- Removed `cancel_timer()` method — no timer to cancel
- `ChapterOverlay.__init__` removed — no state to initialize

**Step 2: Rewrite player.py poll loop to manage overlay lifetime**

```python
import time
import xbmc
import xbmcaddon
from resources.lib.chapters import get_chapters, parse_chapter_name
from resources.lib.overlay import create_chapter_overlay


class ChapterPlayer(xbmc.Player):
    """Monitors playback and shows chapter notifications for configured paths."""

    def __init__(self):
        super().__init__()
        self._active = False
        self._chapters = []
        self._current_chapter_index = -1
        self._overlay = None
        self._overlay_show_time = 0
        self._duration = 5

    def onAVStarted(self):
        try:
            filepath = self.getPlayingFile()
        except RuntimeError:
            return

        if not self._matches_configured_path(filepath):
            xbmc.log("service.chapternotify: path not monitored: {}".format(filepath),
                     xbmc.LOGDEBUG)
            return

        chapters = get_chapters()
        if not chapters:
            xbmc.log("service.chapternotify: no chapters found", xbmc.LOGDEBUG)
            return

        addon = xbmcaddon.Addon("service.chapternotify")
        self._duration = int(addon.getSetting("duration") or "5")
        self._chapters = chapters
        self._current_chapter_index = -1
        self._active = True
        xbmc.log("service.chapternotify: monitoring {} chapters".format(len(chapters)),
                 xbmc.LOGINFO)

    def onPlayBackStopped(self):
        self._deactivate()

    def onPlayBackEnded(self):
        self._deactivate()

    def cleanup(self):
        self._deactivate()

    def tick(self):
        """Called from the main service loop every ~1 second.

        Checks chapter transitions and manages overlay lifetime.
        Must be called from the main thread.
        """
        if not self._active:
            return

        # Auto-hide overlay after duration
        if self._overlay is not None:
            if time.time() - self._overlay_show_time >= self._duration:
                self._dismiss_overlay()

        try:
            current_time = self.getTime()
        except RuntimeError:
            self._deactivate()
            return

        chapter_index = self._get_chapter_for_time(current_time)
        if chapter_index != self._current_chapter_index and chapter_index >= 0:
            self._current_chapter_index = chapter_index
            chapter = self._chapters[chapter_index]
            parsed = parse_chapter_name(chapter["name"])
            xbmc.log(
                "service.chapternotify: chapter {} - {}".format(
                    chapter_index + 1, chapter["name"]
                ),
                xbmc.LOGINFO,
            )
            self._dismiss_overlay()
            self._overlay = create_chapter_overlay(parsed)
            self._overlay_show_time = time.time()

    def _matches_configured_path(self, filepath):
        addon = xbmcaddon.Addon("service.chapternotify")
        for key in ("path1", "path2", "path3"):
            path = addon.getSetting(key)
            if path and filepath.startswith(path):
                return True
        return False

    def _deactivate(self):
        self._active = False
        self._chapters = []
        self._current_chapter_index = -1
        self._dismiss_overlay()

    def _dismiss_overlay(self):
        if self._overlay is not None:
            try:
                self._overlay.close()
            except RuntimeError:
                pass
            self._overlay = None

    def _get_chapter_for_time(self, current_time):
        """Return the index of the chapter that contains current_time."""
        result = -1
        for i, ch in enumerate(self._chapters):
            if current_time >= ch["time"]:
                result = i
            else:
                break
        return result
```

Key changes:
- **No background thread.** Replaced with `tick()` method called from main service loop.
- All GUI operations (create/close overlay) happen on the main thread.
- Overlay lifetime managed by tracking `_overlay_show_time` and checking in `tick()`.
- Added debug logging for path matching and chapter detection.
- `_deactivate()` replaces `_stop_polling()` — simpler, no thread join.

**Step 3: Update service.py to call tick()**

```python
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
```

Only change: added `player.tick()` call in the main loop.

**Step 4: Verify Python syntax**

```bash
python3 -m py_compile service.chapternotify/resources/lib/overlay.py
python3 -m py_compile service.chapternotify/resources/lib/player.py
python3 -m py_compile service.chapternotify/service.py
```

Expected: no output (clean compile). Note: will fail on `import xbmc` etc. since we're not in Kodi runtime. Instead verify with:

```bash
python3 -c "
import ast, sys
for f in ['service.chapternotify/resources/lib/overlay.py',
          'service.chapternotify/resources/lib/player.py',
          'service.chapternotify/service.py']:
    with open(f) as fh:
        ast.parse(fh.read())
    print(f'{f}: syntax OK')
"
```

**Step 5: Commit**

```bash
git add service.chapternotify/resources/lib/overlay.py service.chapternotify/resources/lib/player.py service.chapternotify/service.py
git commit -m "fix: remove background threads, run GUI ops on main thread, fix input handling"
```

---

### Task 4: Add error handling to JSON-RPC chapter fetching

**Files:**
- Modify: `service.chapternotify/resources/lib/chapters.py`

**Step 1: Add error response handling and logging**

```python
import json
import re
import xbmc


def get_chapters():
    """Fetch chapters for the active video player via JSON-RPC.

    Returns a list of dicts: [{"index": int, "name": str, "time": float_seconds}, ...]
    Returns empty list if no chapters, no active player, or on error.
    """
    request = json.dumps({
        "jsonrpc": "2.0",
        "method": "Player.GetChapters",
        "params": {"playerid": 1},
        "id": 1
    })
    try:
        raw = xbmc.executeJSONRPC(request)
        response = json.loads(raw)
    except (ValueError, TypeError) as e:
        xbmc.log("service.chapternotify: JSON-RPC error: {}".format(e),
                 xbmc.LOGWARNING)
        return []

    if "error" in response:
        xbmc.log("service.chapternotify: JSON-RPC returned error: {}".format(
            response["error"].get("message", "unknown")), xbmc.LOGDEBUG)
        return []

    chapters_raw = response.get("result", {}).get("chapters", [])
    chapters = []
    for ch in chapters_raw:
        time_seconds = ch.get("time", 0)
        chapters.append({
            "index": ch.get("index", 0),
            "name": ch.get("name", ""),
            "time": float(time_seconds),
        })
    return chapters


def parse_chapter_name(name):
    """Parse 'Artist - Track [Label]' into structured dict.

    Returns {"artist": str, "track": str, "label": str, "raw": str}.
    If the format doesn't match, artist/track/label may be empty and raw
    contains the original name.
    """
    result = {"artist": "", "track": "", "label": "", "raw": name}

    # Strip leading language tag like "en:" if present
    cleaned = re.sub(r"^[a-z]{2}:", "", name).strip()
    result["raw"] = cleaned

    # Try to match: Artist - Track [Label]
    match = re.match(r"^(.+?)\s+-\s+(.+?)(?:\s+\[(.+?)\])?\s*$", cleaned)
    if match:
        result["artist"] = match.group(1).strip()
        result["track"] = match.group(2).strip()
        result["label"] = (match.group(3) or "").strip()

    return result
```

**Step 2: Test parser still works**

```bash
python3 -c "
import sys; sys.path.insert(0, 'service.chapternotify')
from resources.lib.chapters import parse_chapter_name

r = parse_chapter_name('en:FISHER & AR/CO - Ocean [CATCH & RELEASE]')
assert r['artist'] == 'FISHER & AR/CO'
assert r['track'] == 'Ocean'
assert r['label'] == 'CATCH & RELEASE'

r = parse_chapter_name('Some Random Name')
assert r['artist'] == ''
assert r['raw'] == 'Some Random Name'

print('Parser tests passed')
"
```

**Step 3: Commit**

```bash
git add service.chapternotify/resources/lib/chapters.py
git commit -m "fix: add error handling and logging to JSON-RPC chapter fetching"
```

---

### Task 5: Fix addon.xml language tag

**Files:**
- Modify: `service.chapternotify/addon.xml`

**Step 1: Change lang="en" to lang="en_GB" to match language resource folder**

Change both `lang="en"` occurrences to `lang="en_GB"`:

```xml
<summary lang="en_GB">Show chapter notifications during video playback</summary>
<description lang="en_GB">Displays a styled overlay notification when a new chapter starts playing in videos from configured library folders. Designed for festival DJ sets with named chapters.</description>
```

**Step 2: Commit**

```bash
git add service.chapternotify/addon.xml
git commit -m "fix: use en_GB language tag to match resource folder"
```

---

### Task 6: Rebuild zip and verify

**Step 1: Rebuild the installable zip**

```bash
rm -f service.chapternotify.zip
zip -r service.chapternotify.zip service.chapternotify/ -x '*.pyc' -x '*__pycache__*'
```

**Step 2: Verify zip contents**

```bash
unzip -l service.chapternotify.zip
```

Expected files:
```
service.chapternotify/addon.xml
service.chapternotify/service.py
service.chapternotify/resources/settings.xml
service.chapternotify/resources/language/resource.language.en_gb/strings.po
service.chapternotify/resources/lib/__init__.py
service.chapternotify/resources/lib/chapters.py
service.chapternotify/resources/lib/overlay.py
service.chapternotify/resources/lib/player.py
service.chapternotify/resources/skins/default/1080i/Includes.xml
service.chapternotify/resources/skins/default/1080i/chapternotify.xml
```

**Step 3: Validate all XML**

```bash
python3 -c "
import xml.etree.ElementTree as ET
for f in ['service.chapternotify/addon.xml',
          'service.chapternotify/resources/settings.xml',
          'service.chapternotify/resources/skins/default/1080i/Includes.xml',
          'service.chapternotify/resources/skins/default/1080i/chapternotify.xml']:
    ET.parse(f)
    print(f'{f}: OK')
"
```

**Step 4: Validate all Python syntax**

```bash
python3 -c "
import ast
for f in ['service.chapternotify/service.py',
          'service.chapternotify/resources/lib/chapters.py',
          'service.chapternotify/resources/lib/overlay.py',
          'service.chapternotify/resources/lib/player.py']:
    with open(f) as fh:
        ast.parse(fh.read())
    print(f'{f}: OK')
"
```

**Step 5: Test parser**

```bash
python3 -c "
import sys; sys.path.insert(0, 'service.chapternotify')
from resources.lib.chapters import parse_chapter_name

tests = [
    ('en:FISHER & AR/CO - Ocean [CATCH & RELEASE]', 'FISHER & AR/CO', 'Ocean', 'CATCH & RELEASE'),
    ('en:Gaddi - Desire', 'Gaddi', 'Desire', ''),
    ('en:ID - ID', 'ID', 'ID', ''),
    ('Some Random Name', '', '', ''),
]
for name, artist, track, label in tests:
    r = parse_chapter_name(name)
    assert r['artist'] == artist, f'Failed on {name}: {r}'
    assert r['track'] == track, f'Failed on {name}: {r}'
    assert r['label'] == label, f'Failed on {name}: {r}'

print('All tests passed')
"
```
