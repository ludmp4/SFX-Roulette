# SFX Roulette

SFX Roulette is a Windows-first DaVinci Resolve Studio utility script for inserting a random sound effect from a mapped Media Pool bin at the current playhead position.

Project page: <https://github.com/ludmp4/SFX-Roulette>

## Folder Structure

```text
Install SFX Roulette.bat
install.ps1
main.py
src/sfx_roulette/
  bin_scanner.py
  config_manager.py
  controller.py
  errors.py
  hotkey_listener.py
  media_pool_manager.py
  models.py
  random_picker.py
  resolve_api.py
  timeline_inserter.py
  track_manager.py
  ui.py
config/example_config.json
scripts/install_windows.ps1
scripts/Install SFX Roulette.bat
docs/testing_checklist.md
docs/resolve_api_limitations.md
```

## Easiest Install

1. Download the repository ZIP from <https://github.com/ludmp4/SFX-Roulette>.
2. Extract it.
3. Double-click `Install SFX Roulette.bat`.
4. Open Resolve and choose `Workspace > Scripts > Utility > SFX Roulette`.

To update from an extracted copy, double-click the same `.bat` file again.

The `.bat` installer always checks GitHub and installs the newest `main` version, even if the extracted ZIP is old. It clearly reports whether it installed a new version, updated from one commit to another, or found that you are already on the newest version. When an update is available, it prints a tiny “What’s new” summary from the latest commit.

GitHub auto-update requires the repository archive to be accessible to the tester. If the repo is private or the tester has no GitHub access, the `.bat` falls back to installing the files bundled in the extracted ZIP and says so in the installer output.

You do not need to install Python separately. The installer uses Windows PowerShell to copy files, and SFX Roulette runs through DaVinci Resolve Studio's bundled scripting environment.

## One-Line Install Or Update

Run PowerShell as your normal Windows user and paste:

```powershell
irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1 | iex
```

The same command updates SFX Roulette later. User mappings and `last_used_clip_id` values are preserved in your settings file.

## Local Install

1. Close and reopen DaVinci Resolve after installing or updating scripts.
2. Double-click `Install SFX Roulette.bat`, or from PowerShell in this folder run:

```powershell
.\install.ps1
```

For a local source install that does not fetch GitHub, run `.\install.ps1` directly. The double-click `.bat` is intended for testers and always prefers GitHub updates.

3. Open Resolve Studio.
4. Open `Workspace > Scripts > Utility > SFX Roulette`.

The installer downloads or copies the app into:

```text
%LOCALAPPDATA%\SFX Roulette
```

It creates a Resolve launcher script in:

```text
%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\SFX Roulette.py
```

Settings are saved to:

```text
%USERPROFILE%\Documents\SFX Roulette\sfx_roulette_config.json
```

## Updating

Run the same installer command again:

```powershell
irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1 | iex
```

The update replaces installed app files from `ludmp4/SFX-Roulette` and keeps the existing settings in `%USERPROFILE%\Documents\SFX Roulette`.

Installer output examples:

```text
SFX Roulette | Updated SFX Roulette: ea839df -> 5c0a2ec
SFX Roulette | What's new: Detect Resolve audio clips by filename
```

```text
SFX Roulette | Already on the newest version (5c0a2ec).
```

## Uninstalling

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1))) -Uninstall
```

Or, from a local clone:

```powershell
.\install.ps1 -Uninstall
```

Uninstall removes the Resolve launcher and installed app files. It keeps user settings in Documents so they can be reused after reinstalling.

## Resolve Setup

1. Enable external scripting in Resolve Studio if your installation requires it.
2. Create Media Pool bins such as `Whooshes`, `Hits`, and `Glitches`.
3. Put online audio clips directly inside each bin. Version 1 intentionally does not scan subfolders.
4. Open a project and timeline.
5. Launch SFX Roulette.
6. Click `Refresh Bins`.
7. Add mappings like `Ctrl+Alt+1 -> Whooshes -> A3`.
8. Click `Test Insert`.
9. Click `Start Hotkeys`.

## Behavior

- Uses WAV, MP3, AIFF, FLAC, M4A, AAC, OGG, WMA, CAF, BWF, and items Resolve reports as audio.
- Ignores offline items, timelines, stills, Fusion comps, and obvious non-audio media.
- Maintains `last_used_clip_id` per mapping.
- If a bin has two or more clips, the previous clip is excluded from the next random choice.
- Inserts audio with `AppendToTimeline` using `recordFrame`, audio-only `mediaType`, and explicit `trackIndex` when a track is assigned.
- Does not move the playhead intentionally.

## Hotkeys

Resolve does not expose a documented public API for registering arbitrary live script hotkeys. SFX Roulette therefore uses a lightweight Windows `RegisterHotKey` listener in the utility panel. It only fires when the foreground window title contains `DaVinci Resolve`.

## Notes

Resolve scripting behavior varies slightly by version. If exact insertion fails, see `docs/resolve_api_limitations.md` for the likely causes and mitigation steps.
