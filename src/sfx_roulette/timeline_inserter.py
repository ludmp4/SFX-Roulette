from __future__ import annotations

from typing import Any, Optional

from .errors import InsertError, TimelineUnavailableError
from .models import AudioClip
from .track_manager import TrackManager


RECORD_FRAME_ABSOLUTE = "absolute_timecode"
RECORD_FRAME_RELATIVE = "relative_to_timeline_start"


class TimelineInserter:
    def __init__(self, resolve_api: Any, record_frame_mode: str = RECORD_FRAME_ABSOLUTE) -> None:
        self.resolve_api = resolve_api
        self.record_frame_mode = record_frame_mode

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
        fps = self._timeline_fps()
        absolute_frame = self._timecode_to_frame(str(timecode), fps)
        if self.record_frame_mode == RECORD_FRAME_RELATIVE:
            return max(0, absolute_frame - self._timeline_start_frame(timeline, fps))
        return absolute_frame

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
        elapsed_seconds = (hours * 60 + minutes) * 60 + seconds
        return round((elapsed_seconds * fps) + frames)

    @classmethod
    def _timeline_start_frame(cls, timeline: Any, fps: float) -> int:
        get_start_frame = getattr(timeline, "GetStartFrame", None)
        if callable(get_start_frame):
            try:
                value = get_start_frame()
                if value not in (None, ""):
                    return int(value)
            except Exception:
                pass

        get_start_timecode = getattr(timeline, "GetStartTimecode", None)
        if callable(get_start_timecode):
            try:
                value = get_start_timecode()
                if value:
                    return cls._timecode_to_frame(str(value), fps)
            except Exception:
                pass

        return 0
