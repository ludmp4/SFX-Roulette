from __future__ import annotations

from typing import Any, Optional

from .errors import TrackUnavailableError


class TrackManager:
    def __init__(self, timeline: Any) -> None:
        self.timeline = timeline

    def resolve_audio_track(self, requested: Optional[int]) -> Optional[int]:
        if requested is None:
            return None
        existing = self._audio_track_count()
        if requested <= existing:
            return requested
        if self._try_create_until(requested):
            return requested
        raise TrackUnavailableError(
            f"Assigned audio track A{requested} does not exist, and Resolve did not allow this script to create it."
        )

    def _audio_track_count(self) -> int:
        getter = getattr(self.timeline, "GetTrackCount", None)
        if not callable(getter):
            raise TrackUnavailableError("Resolve API does not expose timeline track counts here.")
        return int(getter("audio") or 0)

    def _try_create_until(self, requested: int) -> bool:
        add_track = getattr(self.timeline, "AddTrack", None)
        if not callable(add_track):
            return False
        while self._audio_track_count() < requested:
            before = self._audio_track_count()
            ok = bool(add_track("audio"))
            if not ok or self._audio_track_count() <= before:
                return False
        return True
