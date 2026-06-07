from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .errors import BinUnavailableError, ClipUnavailableError
from .models import AUDIO_EXTENSIONS, AudioClip


@dataclass
class BinRecord:
    name: str
    folder: Any
    clips: List[AudioClip] = field(default_factory=list)


class BinScanner:
    def __init__(self, resolve_api: Any) -> None:
        self.resolve_api = resolve_api
        self._bins_by_name: Dict[str, BinRecord] = {}

    def refresh(self) -> Dict[str, BinRecord]:
        root = self.resolve_api.media_pool().GetRootFolder()
        if not root:
            raise BinUnavailableError("Cannot access the Media Pool root folder.")
        records: Dict[str, BinRecord] = {}
        for folder in self._walk_folders(root):
            name = folder.GetName() or ""
            if not name:
                continue
            record = BinRecord(name=name, folder=folder, clips=self._scan_folder_clips(folder))
            records[self._key(name)] = record
        self._bins_by_name = records
        return records

    def bin_names(self) -> List[str]:
        if not self._bins_by_name:
            self.refresh()
        return sorted(record.name for record in self._bins_by_name.values())

    def clips_for_bin(self, bin_name: str) -> List[AudioClip]:
        if not self._bins_by_name:
            self.refresh()
        record = self._bins_by_name.get(self._key(bin_name))
        if not record:
            self.refresh()
            record = self._bins_by_name.get(self._key(bin_name))
        if not record:
            raise BinUnavailableError(f'Assigned bin "{bin_name}" no longer exists.')
        if not record.clips:
            raise ClipUnavailableError(f'Bin "{record.name}" has no valid online audio clips.')
        return list(record.clips)

    def clip_count(self, bin_name: str) -> int:
        record = self._bins_by_name.get(self._key(bin_name))
        return len(record.clips) if record else 0

    def _walk_folders(self, folder: Any) -> Iterable[Any]:
        yield folder
        for child in folder.GetSubFolderList() or []:
            yield from self._walk_folders(child)

    def _scan_folder_clips(self, folder: Any) -> List[AudioClip]:
        clips = []
        for item in folder.GetClipList() or []:
            clip = self._audio_clip_from_item(item)
            if clip:
                clips.append(clip)
        return clips

    def _audio_clip_from_item(self, item: Any) -> Optional[AudioClip]:
        props = item.GetClipProperty() or {}
        name = str(item.GetName() or props.get("Clip Name") or props.get("File Name") or "Unnamed")
        path = self._first_path(props)
        if not self._is_online(props):
            return None
        if not self._looks_audio(props, name, path):
            return None
        return AudioClip(
            id=self._clip_id(item, name, path),
            name=name,
            path=path,
            media_pool_item=item,
            start_frame=0,
            end_frame=None,
        )

    @staticmethod
    def _first_path(props: Dict[str, Any]) -> str:
        for key in (
            "File Path",
            "File Name",
            "Filename",
            "Path",
            "Source File",
            "Source Path",
            "Media Path",
        ):
            value = props.get(key)
            if value:
                if isinstance(value, (list, tuple)):
                    value = value[0] if value else ""
                text = str(value)
                return text.splitlines()[0].strip()
        return ""

    @staticmethod
    def _is_online(props: Dict[str, Any]) -> bool:
        offline = str(props.get("Offline", props.get("Media Offline", ""))).lower().strip()
        status = str(props.get("Status", props.get("Media Status", ""))).lower().strip()
        return offline not in {"1", "true", "yes"} and "offline" not in status

    @staticmethod
    def _looks_audio(props: Dict[str, Any], name: str, path: str) -> bool:
        clip_type = str(props.get("Type", props.get("Clip Type", ""))).lower()
        if "timeline" in clip_type or "fusion" in clip_type or "still" in clip_type:
            return False
        if "audio" in clip_type:
            return True
        for key in ("Audio Channels", "Channels", "Audio Tracks", "Audio Codec", "Audio Bit Depth"):
            value = str(props.get(key, "")).strip()
            if value and value not in {"0", "None", "none", "-"}:
                return True
        for candidate in (path, name, str(props.get("File Name", "")), str(props.get("Filename", ""))):
            if Path(candidate).suffix.lower() in AUDIO_EXTENSIONS:
                return True
        format_value = str(props.get("Format", props.get("Codec", ""))).lower()
        if any(ext.lstrip(".") in format_value for ext in AUDIO_EXTENSIONS):
            return True
        return False

    @staticmethod
    def _clip_id(item: Any, name: str, path: str) -> str:
        unique = ""
        for method in ("GetUniqueId", "GetMediaId"):
            func = getattr(item, method, None)
            if callable(func):
                try:
                    unique = str(func() or "")
                except Exception:
                    unique = ""
                if unique:
                    return unique
        raw = f"{name}|{path}|{os.path.getmtime(path) if path and os.path.exists(path) else ''}"
        return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()

    @staticmethod
    def _key(name: str) -> str:
        return name.casefold().strip()
