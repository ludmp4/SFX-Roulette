# Testing Checklist

## Basic Resolve Connection

- Start DaVinci Resolve Studio.
- Open a project.
- Open a timeline.
- Launch `Workspace > Scripts > Utility > SFX Roulette`.
- Confirm the status area shows the current project and timeline after refreshing bins.

## Bin Scanning

- Create a bin named `Whooshes`.
- Add three online WAV files directly inside it.
- Click `Refresh Bins`.
- Confirm the mapping table shows the correct clip count.
- Rename the bin and refresh.
- Confirm mappings to the old name report a missing-bin warning.

## Randomization

- Map `Ctrl+Alt+1` to `Whooshes`.
- Click `Test Insert` several times.
- Confirm the same clip is not selected twice in a row when the bin has two or more valid clips.
- Test a one-clip bin and confirm that single clip is always used.

## Timeline Insertion

- Move the playhead to a visible empty section.
- Assign `A3`.
- Keep `Placement` set to `Absolute Timecode` for normal Resolve timelines.
- Click `Test Insert`.
- Confirm the audio starts at the playhead frame and preserves clip length.
- Confirm the playhead does not move.
- If clips land far ahead of the playhead, switch `Placement` to `Subtract Timeline Start` and test again.
- Assign a missing track, such as `A8`.
- Confirm the script creates tracks when Resolve allows it or shows a clear error.

## Hotkeys

- Add mappings for `Ctrl+Alt+1`, `Ctrl+Alt+2`, and `Ctrl+Shift+1`.
- Click `Start Hotkeys`.
- Focus Resolve.
- Press each hotkey and confirm the corresponding bin and track are used.
- Focus another app and press the same hotkeys.
- Confirm SFX Roulette does not fire while Resolve is not focused.

## Error Cases

- Close the active project and try refreshing bins.
- Remove all audio from a mapped bin and run `Test Insert`.
- Add offline media to a bin and confirm it is ignored.
- Stop the hotkey listener and confirm the status area reflects the state.
