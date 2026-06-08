from __future__ import annotations

from typing import Callable, List, Optional

from .bin_scanner import BinScanner
from .config_manager import ConfigManager
from .errors import SFXRouletteError
from .models import Mapping
from .random_picker import RandomPicker
from .resolve_api import ResolveAPI
from .timeline_inserter import RECORD_FRAME_ABSOLUTE, RECORD_FRAME_RELATIVE, TimelineInserter


class SFXRouletteController:
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None) -> None:
        self.status_callback = status_callback or (lambda message: None)
        self.config = ConfigManager()
        self.mappings: List[Mapping] = self.config.load()
        self.record_frame_mode = self.config.load_record_frame_mode()
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
        self.config.save(self.mappings, self.record_frame_mode)

    def set_record_frame_mode(self, mode: str) -> None:
        if mode not in {RECORD_FRAME_ABSOLUTE, RECORD_FRAME_RELATIVE}:
            mode = RECORD_FRAME_ABSOLUTE
        self.record_frame_mode = mode
        self.save()

    def add_mapping(self, hotkey: str, bin_name: str, target_audio_track: Optional[int]) -> Mapping:
        hotkey = hotkey.strip()
        mapping = Mapping(hotkey=hotkey, bin_name=bin_name.strip(), target_audio_track=target_audio_track)
        self.mappings.append(mapping)
        return mapping

    def update_mapping(
        self,
        mapping_id: str,
        hotkey: str,
        bin_name: str,
        target_audio_track: Optional[int],
    ) -> Mapping:
        hotkey = hotkey.strip()
        bin_name = bin_name.strip()
        for mapping in self.mappings:
            if mapping.id == mapping_id:
                mapping.hotkey = hotkey
                mapping.bin_name = bin_name
                mapping.target_audio_track = target_audio_track
                return mapping
        return self.add_mapping(hotkey, bin_name, target_audio_track)

    def upsert_mapping(
        self,
        hotkey: str,
        bin_name: str,
        target_audio_track: Optional[int],
        mapping_id: Optional[str] = None,
    ) -> Mapping:
        if mapping_id:
            return self.update_mapping(mapping_id, hotkey, bin_name, target_audio_track)
        return self.add_mapping(hotkey, bin_name, target_audio_track)

    def remove_mapping(self, mapping_id: str) -> None:
        self.mappings = [mapping for mapping in self.mappings if mapping.id != mapping_id]

    def unique_hotkeys(self) -> list[str]:
        return sorted({mapping.hotkey for mapping in self.mappings if mapping.hotkey})

    def trigger_hotkey(self, hotkey: str) -> str:
        mappings = [item for item in self.mappings if item.hotkey.casefold() == hotkey.casefold()]
        if not mappings:
            raise SFXRouletteError(f"No SFX Roulette mapping is assigned to {hotkey}.")
        messages = [self.insert_for_mapping(mapping) for mapping in mappings]
        if len(messages) == 1:
            return messages[0]
        return f"Inserted {len(messages)} SFX mappings for {hotkey}."

    def insert_for_mapping(self, mapping: Mapping) -> str:
        self.ensure_connected()
        assert self.resolve_api is not None
        assert self.bin_scanner is not None
        clips = self.bin_scanner.clips_for_bin(mapping.bin_name)
        clip = self.picker.choose(clips, mapping.last_used_clip_id)
        TimelineInserter(self.resolve_api, self.record_frame_mode).insert(clip, mapping.target_audio_track)
        mapping.last_used_clip_id = clip.id
        self.save()
        project, timeline = self.resolve_api.current_context_label()
        message = f'Inserted "{clip.name}" from "{mapping.bin_name}" on {mapping.track_label} in {project} / {timeline}.'
        self.status_callback(message)
        return message
