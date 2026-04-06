# service.chapternotify Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Kodi service addon that shows beautiful overlay notifications when chapters change in videos played from configured library folders.

**Architecture:** Service addon with `xbmc.Player` subclass. On playback start, checks file path against configured folders. If matched and video has chapters (fetched via JSON-RPC `Player.GetChapters`), polls `getTime()` every 1s. On chapter transition, parses `Artist - Track [Label]` and shows a custom `WindowXMLDialog` overlay.

**Tech Stack:** Python 3 (Kodi addon API), xbmc/xbmcgui/xbmcaddon modules, JSON-RPC via `xbmc.executeJSONRPC`, Kodi XML skinning for overlay window.

**Reference:** Design doc at `docs/plans/2026-04-06-chapternotify-design.md`. Kodi source at `/home/martijn/xbmc/`.

---

### Task 1: Addon Skeleton

**Files:**
- Create: `service.chapternotify/addon.xml`
- Create: `service.chapternotify/service.py`
- Create: `service.chapternotify/resources/lib/__init__.py`

**Step 1: Create addon.xml**

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="service.chapternotify" name="Chapter Notify" version="0.1.0" provider-name="martijn">
  <requires>
    <import addon="xbmc.python" version="3.0.0"/>
  </requires>
  <extension point="xbmc.service" library="service.py"/>
  <extension point="xbmc.addon.metadata">
    <summary lang="en">Show chapter notifications during video playback</summary>
    <description lang="en">Displays a styled overlay notification when a new chapter starts playing in videos from configured library folders. Designed for festival DJ sets with named chapters.</description>
    <platform>all</platform>
    <license>GPL-2.0-or-later</license>
  </extension>
</addon>
```

**Step 2: Create service.py**

```python
import xbmc
from resources.lib.player import ChapterPlayer

if __name__ == "__main__":
    monitor = xbmc.Monitor()
    player = ChapterPlayer()
    xbmc.log("service.chapternotify: started", xbmc.LOGINFO)

    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break

    player.cleanup()
    xbmc.log("service.chapternotify: stopped", xbmc.LOGINFO)
```

**Step 3: Create empty `__init__.py`**

Create `service.chapternotify/resources/lib/__init__.py` (empty file).

**Step 4: Commit**

```bash
git add service.chapternotify/addon.xml service.chapternotify/service.py service.chapternotify/resources/lib/__init__.py
git commit -m "feat: add addon skeleton for service.chapternotify"
```

---

### Task 2: Chapter Fetching and Parsing

**Files:**
- Create: `service.chapternotify/resources/lib/chapters.py`

**Step 1: Create chapters.py with JSON-RPC fetching and name parsing**

```python
import json
import re
import xbmc


def get_chapters():
    """Fetch chapters for the active video player via JSON-RPC.

    Returns a list of dicts: [{"index": int, "name": str, "time": float_seconds}, ...]
    Returns empty list if no chapters or no active player.
    """
    request = json.dumps({
        "jsonrpc": "2.0",
        "method": "Player.GetChapters",
        "params": {"playerid": 1},
        "id": 1
    })
    response = json.loads(xbmc.executeJSONRPC(request))
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

**Step 2: Commit**

```bash
git add service.chapternotify/resources/lib/chapters.py
git commit -m "feat: add chapter fetching via JSON-RPC and name parser"
```

---

### Task 3: Settings

**Files:**
- Create: `service.chapternotify/resources/settings.xml`

**Step 1: Create settings.xml**

```xml
<?xml version="1.0" ?>
<settings version="1">
    <section id="service.chapternotify">
        <category id="general" label="General">
            <group id="1" label="Library Paths">
                <setting id="path1" type="string" label="Library path 1" help="Folder path to monitor for chapter notifications">
                    <level>0</level>
                    <default></default>
                    <control type="edit" format="string"/>
                </setting>
                <setting id="path2" type="string" label="Library path 2" help="Additional folder path (optional)">
                    <level>0</level>
                    <default></default>
                    <control type="edit" format="string"/>
                </setting>
                <setting id="path3" type="string" label="Library path 3" help="Additional folder path (optional)">
                    <level>0</level>
                    <default></default>
                    <control type="edit" format="string"/>
                </setting>
            </group>
        </category>
        <category id="display" label="Display">
            <group id="1" label="Overlay">
                <setting id="duration" type="integer" label="Display duration (seconds)" help="How long the notification stays on screen">
                    <level>0</level>
                    <default>5</default>
                    <constraints>
                        <minimum>3</minimum>
                        <step>1</step>
                        <maximum>15</maximum>
                    </constraints>
                    <control type="slider" format="integer"/>
                </setting>
                <setting id="animation" type="integer" label="Animation style" help="How the notification appears and disappears">
                    <level>0</level>
                    <default>0</default>
                    <constraints>
                        <options>
                            <option label="Fade">0</option>
                            <option label="Slide">1</option>
                        </options>
                    </constraints>
                    <control type="spinner" format="string"/>
                </setting>
                <setting id="position" type="integer" label="Position" help="Where the notification appears on screen">
                    <level>0</level>
                    <default>0</default>
                    <constraints>
                        <options>
                            <option label="Bottom center">0</option>
                            <option label="Bottom left">1</option>
                            <option label="Top right">2</option>
                        </options>
                    </constraints>
                    <control type="spinner" format="string"/>
                </setting>
                <setting id="opacity" type="integer" label="Background opacity (%)" help="Transparency of the notification background">
                    <level>0</level>
                    <default>70</default>
                    <constraints>
                        <minimum>40</minimum>
                        <step>5</step>
                        <maximum>90</maximum>
                    </constraints>
                    <control type="slider" format="integer"/>
                </setting>
                <setting id="sound" type="boolean" label="Play sound" help="Play a sound when a new chapter starts">
                    <level>0</level>
                    <default>false</default>
                    <control type="toggle"/>
                </setting>
            </group>
        </category>
    </section>
</settings>
```

**Step 2: Commit**

```bash
git add service.chapternotify/resources/settings.xml
git commit -m "feat: add addon settings for paths, display, and animation"
```

---

### Task 4: Overlay XML Window

**Files:**
- Create: `service.chapternotify/resources/skins/default/1080i/chapternotify.xml`

The XML defines 3 position variants (bottom-center, bottom-left, top-right) controlled by window properties set from Python. Uses `<visible>` conditions on `Window.Property(position)`.

**Step 1: Create chapternotify.xml**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<window type="dialog">
    <zorder>3</zorder>
    <controls>
        <!-- Bottom Center -->
        <control type="group">
            <visible>String.IsEqual(Window.Property(position),bottom_center)</visible>
            <centerleft>50%</centerleft>
            <bottom>120</bottom>
            <width>700</width>
            <height>140</height>
            <include content="ChapterNotifyContent" />
        </control>

        <!-- Bottom Left -->
        <control type="group">
            <visible>String.IsEqual(Window.Property(position),bottom_left)</visible>
            <left>60</left>
            <bottom>120</bottom>
            <width>700</width>
            <height>140</height>
            <include content="ChapterNotifyContent" />
        </control>

        <!-- Top Right -->
        <control type="group">
            <visible>String.IsEqual(Window.Property(position),top_right)</visible>
            <right>60</right>
            <top>60</top>
            <width>700</width>
            <height>140</height>
            <include content="ChapterNotifyContent" />
        </control>

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
    </controls>
</window>
```

**Step 2: Commit**

```bash
git add service.chapternotify/resources/skins/default/1080i/chapternotify.xml
git commit -m "feat: add overlay XML window with positional variants"
```

---

### Task 5: Overlay Python Class

**Files:**
- Create: `service.chapternotify/resources/lib/overlay.py`

**Step 1: Create overlay.py**

```python
import threading
import xbmc
import xbmcaddon
import xbmcgui


class ChapterOverlay(xbmcgui.WindowXMLDialog):
    """Overlay window that displays chapter info and auto-dismisses."""

    def __init__(self, *args, **kwargs):
        self._close_timer = None

    def onInit(self):
        pass

    def onAction(self, action):
        # Any key/remote press dismisses the overlay
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92
        ACTION_MOVE_LEFT = 1
        ACTION_MOVE_RIGHT = 2
        ACTION_MOVE_UP = 3
        ACTION_MOVE_DOWN = 4
        ACTION_SELECT_ITEM = 7
        # Dismiss on any meaningful action
        self.cancel_timer()
        self.close()


def _get_position_key(setting_value):
    positions = {0: "bottom_center", 1: "bottom_left", 2: "top_right"}
    return positions.get(setting_value, "bottom_center")


def _get_opacity_hex(percent):
    """Convert opacity percentage (40-90) to hex alpha value."""
    alpha = int(percent * 255 / 100)
    return "{:02X}000000".format(alpha)


def show_chapter_overlay(parsed_name, on_close=None):
    """Show the chapter overlay with the given parsed chapter info.

    Args:
        parsed_name: dict with keys "artist", "track", "label", "raw"
        on_close: optional callback when overlay closes
    """
    addon = xbmcaddon.Addon("service.chapternotify")
    addon_path = addon.getAddonInfo("path")

    duration = int(addon.getSetting("duration") or "5")
    position = int(addon.getSetting("position") or "0")
    opacity = int(addon.getSetting("opacity") or "70")
    animation = int(addon.getSetting("animation") or "0")

    overlay = ChapterOverlay(
        "chapternotify.xml",
        addon_path,
        "default",
        "1080i",
    )

    # Set window properties before showing
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

    def _show_and_close():
        overlay.show()
        # Auto-dismiss after duration
        timer = threading.Timer(duration, _safe_close, args=[overlay])
        overlay._close_timer = timer
        timer.start()

    def _safe_close(ovl):
        try:
            ovl.close()
        except RuntimeError:
            pass

    # Must run on main thread context — use show() not doModal() so we don't block
    _show_and_close()
    return overlay
```

**Step 2: Commit**

```bash
git add service.chapternotify/resources/lib/overlay.py
git commit -m "feat: add overlay Python class with auto-dismiss and settings"
```

---

### Task 6: Player Monitor with Polling

**Files:**
- Create: `service.chapternotify/resources/lib/player.py`

**Step 1: Create player.py**

```python
import threading
import xbmc
import xbmcaddon
from resources.lib.chapters import get_chapters, parse_chapter_name
from resources.lib.overlay import show_chapter_overlay


class ChapterPlayer(xbmc.Player):
    """Monitors playback and shows chapter notifications for configured paths."""

    def __init__(self):
        super().__init__()
        self._polling = False
        self._poll_thread = None
        self._chapters = []
        self._current_chapter_index = -1
        self._current_overlay = None

    def onAVStarted(self):
        try:
            filepath = self.getPlayingFile()
        except RuntimeError:
            return

        if not self._matches_configured_path(filepath):
            return

        chapters = get_chapters()
        if not chapters:
            return

        self._chapters = chapters
        self._current_chapter_index = -1
        self._start_polling()

    def onPlayBackStopped(self):
        self._stop_polling()

    def onPlayBackEnded(self):
        self._stop_polling()

    def cleanup(self):
        self._stop_polling()

    def _matches_configured_path(self, filepath):
        addon = xbmcaddon.Addon("service.chapternotify")
        for key in ("path1", "path2", "path3"):
            path = addon.getSetting(key)
            if path and filepath.startswith(path):
                return True
        return False

    def _start_polling(self):
        self._stop_polling()
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _stop_polling(self):
        self._polling = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=2)
            self._poll_thread = None
        self._chapters = []
        self._current_chapter_index = -1
        self._dismiss_overlay()

    def _dismiss_overlay(self):
        if self._current_overlay is not None:
            try:
                self._current_overlay.cancel_timer()
                self._current_overlay.close()
            except RuntimeError:
                pass
            self._current_overlay = None

    def _poll_loop(self):
        monitor = xbmc.Monitor()
        while self._polling and not monitor.abortRequested():
            try:
                current_time = self.getTime()
            except RuntimeError:
                break

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
                self._current_overlay = show_chapter_overlay(parsed)

            if monitor.waitForAbort(1):
                break

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

**Step 2: Commit**

```bash
git add service.chapternotify/resources/lib/player.py
git commit -m "feat: add player monitor with chapter polling and path matching"
```

---

### Task 7: Add Animations to Overlay XML

The initial XML in Task 4 doesn't include animations. Now add fade and slide animations controlled by the `animation` window property.

**Files:**
- Modify: `service.chapternotify/resources/skins/default/1080i/chapternotify.xml`

**Step 1: Update chapternotify.xml to add window-level animations**

Add these animation elements inside the `<window>` tag, before `<controls>`:

```xml
    <!-- Fade animations -->
    <animation effect="fade" start="0" end="100" time="500" condition="String.IsEqual(Window.Property(animation),fade)">WindowOpen</animation>
    <animation effect="fade" start="100" end="0" time="500" condition="String.IsEqual(Window.Property(animation),fade)">WindowClose</animation>

    <!-- Slide animations — slide up from below for bottom positions, slide in from right for top-right -->
    <animation effect="slide" start="0,80" end="0,0" time="400" tween="sine" easing="out" condition="String.IsEqual(Window.Property(animation),slide)">WindowOpen</animation>
    <animation effect="slide" start="0,0" end="0,80" time="400" tween="sine" easing="in" condition="String.IsEqual(Window.Property(animation),slide)">WindowClose</animation>
```

**Step 2: Commit**

```bash
git add service.chapternotify/resources/skins/default/1080i/chapternotify.xml
git commit -m "feat: add fade and slide animations to overlay"
```

---

### Task 8: Integration Test — Manual Verification

**Step 1: Verify file structure is complete**

```bash
find service.chapternotify/ -type f | sort
```

Expected:
```
service.chapternotify/addon.xml
service.chapternotify/resources/lib/__init__.py
service.chapternotify/resources/lib/chapters.py
service.chapternotify/resources/lib/overlay.py
service.chapternotify/resources/lib/player.py
service.chapternotify/resources/settings.xml
service.chapternotify/resources/skins/default/1080i/chapternotify.xml
service.chapternotify/service.py
```

**Step 2: Syntax check all Python files**

```bash
python3 -m py_compile service.chapternotify/service.py
python3 -m py_compile service.chapternotify/resources/lib/chapters.py
python3 -m py_compile service.chapternotify/resources/lib/overlay.py
python3 -m py_compile service.chapternotify/resources/lib/player.py
```

Expected: no output (clean compile).

**Step 3: Validate XML is well-formed**

```bash
python3 -c "import xml.etree.ElementTree as ET; ET.parse('service.chapternotify/addon.xml'); print('addon.xml OK')"
python3 -c "import xml.etree.ElementTree as ET; ET.parse('service.chapternotify/resources/settings.xml'); print('settings.xml OK')"
python3 -c "import xml.etree.ElementTree as ET; ET.parse('service.chapternotify/resources/skins/default/1080i/chapternotify.xml'); print('chapternotify.xml OK')"
```

Expected: all OK.

**Step 4: Test chapter name parser standalone**

```bash
python3 -c "
import sys; sys.path.insert(0, 'service.chapternotify')
from resources.lib.chapters import parse_chapter_name

# Normal format
r = parse_chapter_name('en:FISHER & AR/CO - Ocean [CATCH & RELEASE]')
assert r['artist'] == 'FISHER & AR/CO', r
assert r['track'] == 'Ocean', r
assert r['label'] == 'CATCH & RELEASE', r

# No label
r = parse_chapter_name('en:Gaddi - Desire')
assert r['artist'] == 'Gaddi', r
assert r['track'] == 'Desire', r
assert r['label'] == '', r

# Unparseable
r = parse_chapter_name('en:ID - ID')
assert r['artist'] == 'ID', r
assert r['track'] == 'ID', r

# Totally raw
r = parse_chapter_name('Some Random Name')
assert r['raw'] == 'Some Random Name', r
assert r['artist'] == '', r

print('All parser tests passed')
"
```

Expected: `All parser tests passed`

**Step 5: Commit final state**

```bash
git add -A
git commit -m "chore: verify addon structure and parser correctness"
```

---

### Task 9: Installation Instructions

**Step 1: Add install note to design doc or README**

To install the addon in Kodi:
1. Copy or symlink `service.chapternotify/` to `~/.kodi/addons/service.chapternotify/`
2. Restart Kodi (or enable the addon via Settings > Add-ons > My add-ons > Services)
3. Configure library paths in addon settings
4. Play a video from one of the configured paths — chapter notifications should appear

No commit needed — this is documentation only.
