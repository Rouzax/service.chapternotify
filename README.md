# Chapter Notify

**See what's playing. Every chapter.**

Chapter Notify displays a styled overlay notification when a new chapter starts during video playback. Designed for concert recordings and festival DJ sets with named chapters - know the artist, track, and label without checking your phone.

The perfect companion to [CrateDigger](https://github.com/Rouzax/CrateDigger), which embeds chapter markers from 1001Tracklists.

Built for Kodi 21+ (Omega and newer).

![Chapter Notify overlay during playback](docs/assets/screenshot-overlay.png)

---

## How It Works

Point Chapter Notify at your concert library folders. When you play a video with named chapters (e.g. `Artist - Track [Label]`), an overlay appears on screen with:

- **Track** name (large)
- **Artist** name (medium)
- **Label** name (small, dimmed)

The overlay appears for a configurable duration, then slides or fades away. Any button press dismisses it instantly.

---

## Key Features

- **Chapter Parsing** - Automatically splits `Artist - Track [Label]` format into separate fields
- **4 Color Themes** - Golden Hour, Ultraviolet, Ember, and Nightfall with accent border and separator
- **6 Positions** - Top/bottom × left/center/right
- **Configurable Background** - Rounded panel with adjustable opacity (0-100%), or disable for floating text
- **Fade & Slide Animations** - Smooth transitions with instant dismiss on button press
- **Scrolling Text** - Long track/artist names scroll horizontally while prefixes stay fixed
- **Multiple Library Paths** - Monitor up to 3 folders

---

## Requirements

- **Kodi 21 (Omega)** or later
- Video files with named chapters (MKV, MP4, etc.)
- [CrateDigger](https://github.com/Rouzax/CrateDigger) for automatic chapter embedding (recommended)

---

## Installation

1. Download the latest zip from [Releases](https://github.com/Rouzax/service.chapternotify/releases)
2. In Kodi: **Settings → Add-ons → Install from zip file**
3. Configure your library paths in addon settings

---

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Library paths (1-3) | - | Folders to monitor for chapter notifications |
| Trigger mode | Auto | Auto, Manual, or Both (see below) |
| Trigger key | f1 | Kodi keyboard tag the remote sends to summon the overlay (Manual/Both only) |
| Display duration | 10 seconds | How long the overlay stays on screen |
| Animation style | Slide | Fade or slide transitions |
| Position | Top left | Where the overlay appears |
| Background opacity | 70% | Transparency of the dark panel (0-100%) |
| Theme | Ultraviolet | Color theme for accent border and separator |
| Show background | On | Toggle the panel background on/off |

---

## Trigger Modes

You can choose how the chapter overlay is summoned in **Settings > General > Trigger**:

- **Auto** (default) - The overlay appears automatically when a chapter changes during playback from a configured library path. This is the original v0.5.1 behavior, preserved on upgrade.
- **Manual** - The overlay appears only when you press the configured trigger key. Auto chapter detection is disabled. The library path filter is bypassed, so you can summon chapter info on any media that has chapters.
- **Both** - The overlay appears automatically on chapter changes AND can be summoned on demand with the trigger key.

### How the trigger key behaves

- **Press to show** - the overlay appears with its open animation.
- **Press again** - the existing overlay is instantly replaced with a fresh one (you see the open animation again as confirmation that your press was received).
- **Dismiss with any other button** - the overlay's `onAction` handler closes the dialog instantly when you press any other key.
- **Outside playback** - pressing the key does nothing. The handler is a silent no-op when there is no active playback or no chapter info available.

### Configuring the trigger key

The **Trigger key** setting takes a Kodi keyboard tag (e.g. `f1`, `yellow`, `p`, `browser_back`, `e`). The default is `f1`, which is reliably free in Kodi 21 and works on any keyboard. For programmable remotes (Logitech Harmony, Flirc, etc.) you can pick any key your remote can send, then configure your remote to send that key.

**Common options:**
- `f1`, `f2`, `f3`, `f4`, `f5`, `f6`, `f7`, `f12` - F-keys with no default Kodi bindings (always safe)
- `yellow`, `red`, `green`, `blue` - color buttons; only fire on remotes that send those codes via CEC or MCE (many remotes including Logitech Harmony do not)
- Any letter key - works fine because the addon binds globally and silently does nothing outside playback. Picking a letter that has a Kodi default action (like `e=TVGuide` or `p=Play`) overrides that default everywhere while the addon is enabled - if you also use that default action, pick a different key.

**Keys to avoid:**
- `f8` (Mute), `f9` (Volume Down), `f10` (Volume Up), `f11` (HDR Toggle) - you would lose the volume / HDR shortcut.
- Any key already bound by your skin or other addons in `userdata/keymaps/`.

**To find what your remote actually sends:**
1. In Kodi: **Settings > System > Logging > Enable debug logging**
2. Press the button on your remote you want to use
3. Look in `~/.kodi/temp/kodi.log` for `Keyboard:` lines - the `sym` or character logged is the key name to use

### Keymap file

When you select Manual or Both, the addon writes `userdata/keymaps/service.chapternotify.xml` with bindings in BOTH the `<FullscreenVideo>` and `<global>` sections. The global binding is needed because while the chapter overlay (a modal dialog) is on screen, the active window context is the dialog itself - so without a global binding the keymap lookup would fall through to Kodi's default action for that key.

The addon manages this file completely: it is rewritten whenever you change the trigger settings, removed when you switch back to Auto-only mode, and the **Remove keymap binding** button in settings deletes it on demand. The addon never reads, modifies, or interferes with any other keymap file in `userdata/keymaps/`.

**Before downgrading** to v0.5.1 or uninstalling the addon, click **Remove keymap binding** to avoid leaving an orphaned binding behind. (v0.5.1's `default.py` does not understand the `show` action, so an orphaned binding would silently do nothing - annoying but not destructive.)

---

## License

[GPL-3.0-only](LICENSE)
