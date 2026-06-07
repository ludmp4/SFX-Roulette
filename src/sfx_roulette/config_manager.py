from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Mapping


APP_DIR = Path.home() / "Documents" / "SFX Roulette"
DEFAULT_CONFIG_PATH = APP_DIR / "sfx_roulette_config.json"


class ConfigManager:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DEFAULT_CONFIG_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> List[Mapping]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
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

    def save(self, mappings: Iterable[Mapping]) -> None:
        payload = {
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

    @staticmethod
    def _parse_track(value: object) -> Optional[int]:
        if value in (None, "", "Auto", "auto"):
            return None
        number = int(value)
        if number < 1:
            raise ValueError("Audio track number must be 1 or greater.")
        return number
