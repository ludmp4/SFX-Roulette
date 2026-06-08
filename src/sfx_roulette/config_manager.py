from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Mapping
from .timeline_inserter import RECORD_FRAME_ABSOLUTE, RECORD_FRAME_RELATIVE


APP_DIR = Path.home() / "Documents" / "SFX Roulette"
DEFAULT_CONFIG_PATH = APP_DIR / "sfx_roulette_config.json"


class ConfigManager:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DEFAULT_CONFIG_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> List[Mapping]:
        data = self._load_data()
        mappings = []
        for item in data.get("mappings", []):
            mappings.append(
                Mapping(
                    hotkey=str(item.get("hotkey", "")).strip(),
                    bin_name=str(item.get("bin_name", "")).strip(),
                    target_audio_track=self._parse_track(item.get("target_audio_track")),
                    last_used_clip_id=item.get("last_used_clip_id"),
                )
            )
        return [mapping for mapping in mappings if mapping.hotkey and mapping.bin_name]

    def load_record_frame_mode(self) -> str:
        data = self._load_data()
        mode = str(data.get("record_frame_mode", RECORD_FRAME_ABSOLUTE))
        if mode not in {RECORD_FRAME_ABSOLUTE, RECORD_FRAME_RELATIVE}:
            return RECORD_FRAME_ABSOLUTE
        return mode

    def save(self, mappings: Iterable[Mapping], record_frame_mode: str = RECORD_FRAME_ABSOLUTE) -> None:
        if record_frame_mode not in {RECORD_FRAME_ABSOLUTE, RECORD_FRAME_RELATIVE}:
            record_frame_mode = RECORD_FRAME_ABSOLUTE
        payload = {
            "record_frame_mode": record_frame_mode,
            "mappings": [
                {
                    "hotkey": mapping.hotkey,
                    "bin_name": mapping.bin_name,
                    "target_audio_track": mapping.target_audio_track,
                    "last_used_clip_id": mapping.last_used_clip_id,
                }
                for mapping in mappings
            ]
        }
        tmp_path = self.path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        tmp_path.replace(self.path)

    def _load_data(self) -> dict:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _parse_track(value: object) -> Optional[int]:
        if value in (None, "", "Auto", "auto"):
            return None
        number = int(value)
        if number < 1:
            raise ValueError("Audio track number must be 1 or greater.")
        return number
