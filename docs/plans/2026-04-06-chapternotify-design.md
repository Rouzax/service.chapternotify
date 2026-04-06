# service.chapternotify — Design Document

## Purpose

A Kodi service addon that monitors video playback and shows a styled overlay notification when a new chapter begins. Designed for festival DJ sets with named chapters (Artist - Track [Label] format). Only activates for videos in configured library folder paths.

## Architecture

Service addon with background polling. On playback start, checks if the file path matches configured library folders. If yes, fetches chapters via JSON-RPC and polls every 1 second for chapter transitions. On chapter change, parses the name and shows a custom overlay.

```
Playback starts -> Check file path against configured library folders
  -> No match -> Do nothing
  -> Match -> Fetch chapters via JSON-RPC -> Start polling loop (1s)
    -> Chapter changed -> Parse chapter name -> Show overlay
    -> Playback stops -> Stop polling
```

## Components

### 1. Service entry point (`service.py`)
Main loop using `xbmc.Monitor.waitForAbort()`.

### 2. Player monitor (`resources/lib/player.py`)
Subclass of `xbmc.Player`:
- `onAVStarted()`: get file path, match against configured folders, fetch chapters, start polling thread
- `onPlayBackStopped()` / `onPlayBackEnded()`: stop polling
- Polling thread: checks `getTime()` against chapter boundaries every 1 second

### 3. Chapter parser (`resources/lib/chapters.py`)
- Fetches chapters via JSON-RPC `Player.GetChapters`
- Parses chapter names from `Artist - Track [Label]` into structured fields
- Fallback: show raw chapter name if format doesn't match

### 4. Custom overlay window (`resources/lib/overlay.py` + XML)
- Kodi XML skinned dialog window
- Semi-transparent dark background (configurable opacity)
- Artist (main text, white), track name (secondary), label (dimmer/smaller)
- Animations: fade in/out or slide in/out (configurable)
- Dismissable on keypress OR auto-hides after timeout
- Position configurable: bottom center, bottom left, top right

### 5. Settings (`resources/settings.xml`)

| Setting | Type | Default | Options |
|---------|------|---------|---------|
| Library path 1 | folder browser | empty | -- |
| Library path 2 | folder browser | empty | -- |
| Library path 3 | folder browser | empty | -- |
| Display duration | slider | 5s | 3-15 seconds |
| Animation style | select | fade | fade / slide |
| Position | select | bottom center | bottom center / bottom left / top right |
| Background opacity | slider | 70% | 40-90% |
| Notification sound | boolean | false | -- |

## Data Flow

1. Kodi starts -> service starts -> Player monitor registered
2. User plays video -> `getPlayingFile()` -> check against configured paths
3. Match -> `Player.GetChapters` via JSON-RPC -> chapters loaded -> polling thread starts
4. Polling: `getTime()` every 1s -> crosses chapter boundary -> parse name -> show overlay
5. Overlay: animate in -> display for configured duration -> dismiss on key or timeout -> animate out
6. Playback stops -> polling thread stops -> overlay hidden

## Chapter Name Parsing

Input: `FISHER & AR/CO - Ocean [CATCH & RELEASE]`
- Artist: `FISHER & AR/CO`
- Track: `Ocean`
- Label: `CATCH & RELEASE`

Fallback: if no ` - ` separator found, display raw name as single line.

## Overlay Visual Design

- Semi-transparent dark background (default 70% opacity)
- Rounded corners
- White text for artist and track
- Dimmer/smaller text for label
- Positioned per setting (bottom center / bottom left / top right)

## File Structure

```
service.chapternotify/
  addon.xml
  service.py
  resources/
    settings.xml
    lib/
      player.py
      chapters.py
      overlay.py
    skins/
      default/
        1080i/
          chapternotify.xml
```

## Edge Cases

- No chapters in file: skip polling entirely
- Unparseable chapter name: show raw name as single line
- User seeks manually: polling picks up new position on next tick
- Multiple folder paths: match against all configured paths
- Overlay already showing when next chapter hits: dismiss current, show new
- Playback not from configured folder: zero overhead, no polling
