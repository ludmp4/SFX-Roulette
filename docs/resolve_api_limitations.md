# Resolve API Limitations

SFX Roulette uses DaVinci Resolve's scripting API through the bundled `DaVinciResolveScript` module.

## Hotkeys

Resolve has keyboard customization for built-in commands and scripts, but there is no documented public scripting API for registering arbitrary dynamic hotkeys from Python. Version 1 uses a Windows companion listener based on `RegisterHotKey`.

## Timeline Insert Position

The implementation uses `MediaPool.AppendToTimeline` with a clip-info dictionary containing:

- `mediaPoolItem`
- `startFrame`
- `endFrame` when Resolve exposes a usable clip duration
- `mediaType: 2` for audio-only insertion
- `trackIndex` for assigned audio tracks
- `recordFrame` derived from the current playhead timecode

This is the most direct documented route for placing a Media Pool item at an explicit timeline frame. Some Resolve builds may reject `recordFrame` or `trackIndex` for certain clip types.

SFX Roulette defaults to `Absolute Timecode` because many Resolve builds expect `recordFrame` to use the timeline's displayed frame count. The conversion uses the actual Resolve timeline frame rate, including fractional rates such as 23.976 and 29.97, to avoid drift on hour-starting timelines. Some setups may instead need timeline-start-relative frames; those users can set `Placement` to `Subtract Timeline Start` in the utility panel.

## Timecode Conversion

Resolve exposes the current playhead as timecode. SFX Roulette converts that to frames using the current project's timeline frame rate. Drop-frame timecode is normalized to a best-effort frame count. For frame-critical broadcast workflows, test with your exact project frame rate before production use.

## Track Creation

If an assigned audio track does not exist, SFX Roulette calls `Timeline.AddTrack("audio")` when available. If the API denies track creation, insertion is stopped with a clear error instead of silently placing the clip on the wrong track.

## Clip Filtering

Media Pool clip metadata is not perfectly consistent across media types and Resolve versions. SFX Roulette accepts clips reported as audio, clips with audio-channel metadata, or clips with known audio file extensions. Offline media and obvious non-audio objects are ignored.
