from __future__ import annotations

import random
from typing import Sequence

from .errors import ClipUnavailableError
from .models import AudioClip


class RandomPicker:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def choose(self, clips: Sequence[AudioClip], last_used_clip_id: str | None = None) -> AudioClip:
        if not clips:
            raise ClipUnavailableError("No valid audio clips were found in the assigned bin.")
        if len(clips) == 1:
            return clips[0]
        candidates = [clip for clip in clips if clip.id != last_used_clip_id]
        return self.rng.choice(candidates or list(clips))
