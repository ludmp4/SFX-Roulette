from __future__ import annotations

from typing import Any, Optional

from .errors import InsertError, TimelineUnavailableError
from .models import AudioClip
from .track_manager import TrackManager


class TimelineInserter:
    def __init__(self, resolve_api: Any) -> None:
        self.resolve_api = resolve_api

    def insert(self, clip: AudioClip, target_audio_track: Optional[int]) -> Any:
        timeline = self.resolve_api.timeline()
        media_pool = self.resolve_api.media_pool()
        record_frame = self._current_frame(timeline)
        track_index = TrackManager(timeline).resolve_audio_track(target_audio_track)
        clip_info = {
            "mediaPoolItem": clip.media_pool_item,
            "startFrame": clip.start_frame,
            "mediaType": 2,
            "recordFrame": record_frame,
        }
        if clip.end_frame is not None:
            clip_info["endFrame"] = clip.end_frame
        if track_index is not None:
            clip_info["trackIndex"] = track_index
        result = media_pool.AppendToTimeline([clip_info])
        if not result:
            raise InsertError("Resolve rejected the audio insert request.")
        return result[0] if isinstance(result, list) else result

    def _current_frame(self, timeline: Any) -> int:
        getter = getattr(timeline, "GetCurrentTimecode", None)
        if not callable(getter):
            raise TimelineUnavailableError("Cannot read the current playhead timecode.")
        timecode = getter()
        if not timecode:
            raise TimelineUnavailableError("Cannot read the current playhead position.")
        return self._timecode_to_frame(str(timecode), self._timeline_fps())

    def _timeline_fps(self) -> float:
        project = self.resolve_api.project()
        for key in ("timelineFrameRate", "timelinePlaybackFrameRate"):
            value = project.GetSetting(key)
            if value:
                return float(str(value).replace(",", "."))
        return 24.0

    @staticmethod
    def _timecode_to_frame(timecode: str, fps: float) -> int:
        clean = timecode.replace(";", ":").replace(".", ":")
        parts = clean.split(":")
        if len(parts) != 4:
            raise TimelineUnavailableError(f"Unexpected playhead timecode format: {timecode}")
        hours, minutes, seconds, frames = [int(part) for part in parts]
        rounded_fps = round(fps)
        return (((hours * 60 + minutes) * 60 + seconds) * rounded_fps) + frames
