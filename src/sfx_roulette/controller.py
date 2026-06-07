from __future__ import annotations

from typing import Callable, List, Optional

from .bin_scanner import BinScanner
from .config_manager import ConfigManager
from .errors import SFXRouletteError
from .models import Mapping
from .random_picker import RandomPicker
from .resolve_api import ResolveAPI
from .timeline_inserter import TimelineInserter


class SFXRouletteController:
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None) -> None:
        self.status_callback = status_callback or (lambda message: None)
        self.config = ConfigManager()
        self.mappings: List[Mapping] = self.config.load()
        self.resolve_api: Optional[ResolveAPI] = None
        self.bin_scanner: Optional[BinScanner] = None
        self.picker = RandomPicker()

    def connect(self) -> None:
        self.resolve_api = ResolveAPI()
        self.bin_scanner = BinScanner(self.resolve_api)

    def ensure_connected(self) -> None:
        if self.resolve_api is None or self.bin_scanner is None:
            self.connect()

    def refresh_bins(self) -> list[str]:
        self.ensure_connected()
        assert self.bin_scanner is not None
        self.bin_scanner.refresh()
        return self.bin_scanner.bin_names()

    def save(self) -> None:
        self.config.save(self.mappings)

    def upsert_mapping(self, hotkey: str, bin_name: str, target_audio_track: Optional[int]) -> None:
        hotkey = hotkey.strip()
        for mapping in self.mappings:
            if mapping.hotkey.casefold() == hotkey.casefold():
                mapping.bin_name = bin_name
                mapping.target_audio_track = target_audio_track
                return
        self.mappings.append(Mapping(hotkey=hotkey, bin_name=bin_name, target_audio_track=target_audio_track))

    def remove_mapping(self, hotkey: str) -> None:
        self.mappings = [mapping for mapping in self.mappings if mapping.hotkey != hotkey]

    def trigger_hotkey(self, hotkey: str) -> str:
        mapping = next((item for item in self.mappings if item.hotkey.casefold() == hotkey.casefold()), None)
        if not mapping:
            raise SFXRouletteError(f"No SFX Roulette mapping is assigned to {hotkey}.")
        return self.insert_for_mapping(mapping)

    def insert_for_mapping(self, mapping: Mapping) -> str:
        self.ensure_connected()
        assert self.resolve_api is not None
        assert self.bin_scanner is not None
        clips = self.bin_scanner.clips_for_bin(mapping.bin_name)
        clip = self.picker.choose(clips, mapping.last_used_clip_id)
        TimelineInserter(self.resolve_api).insert(clip, mapping.target_audio_track)
        mapping.last_used_clip_id = clip.id
        self.save()
        project, timeline = self.resolve_api.current_context_label()
        message = f'Inserted "{clip.name}" from "{mapping.bin_name}" on {mapping.track_label} in {project} / {timeline}.'
        self.status_callback(message)
        return message
