from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


AUDIO_EXTENSIONS = {
    ".wav",
    ".wave",
    ".mp3",
    ".aif",
    ".aiff",
    ".flac",
    ".m4a",
    ".aac",
    ".ogg",
    ".wma",
    ".caf",
    ".bwf",
}


@dataclass(frozen=True)
class AudioClip:
    id: str
    name: str
    path: str
    media_pool_item: object
    start_frame: int = 0
    end_frame: Optional[int] = None


@dataclass
class Mapping:
    hotkey: str
    bin_name: str
    target_audio_track: Optional[int] = None
    last_used_clip_id: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex

    @property
    def track_label(self) -> str:
        if self.target_audio_track is None:
            return "Auto"
        return f"A{self.target_audio_track}"
