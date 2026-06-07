from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

from .errors import ProjectUnavailableError, ResolveUnavailableError, TimelineUnavailableError


SCRIPT_MODULE_DIR = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / (
    r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
)


class ResolveAPI:
    def __init__(self) -> None:
        self.resolve = self._connect()

    @staticmethod
    def _connect() -> Any:
        if str(SCRIPT_MODULE_DIR) not in sys.path and SCRIPT_MODULE_DIR.exists():
            sys.path.append(str(SCRIPT_MODULE_DIR))
        try:
            module = importlib.import_module("DaVinciResolveScript")
        except ImportError as exc:
            raise ResolveUnavailableError(
                "Cannot import DaVinciResolveScript. Run this from a Resolve scripting environment "
                "or install the bundled Resolve scripting module path."
            ) from exc
        resolve = module.scriptapp("Resolve")
        if not resolve:
            raise ResolveUnavailableError("DaVinci Resolve is not running or scripting is not available.")
        return resolve

    def project_manager(self) -> Any:
        manager = self.resolve.GetProjectManager()
        if not manager:
            raise ProjectUnavailableError("Cannot access Resolve Project Manager.")
        return manager

    def project(self) -> Any:
        project = self.project_manager().GetCurrentProject()
        if not project:
            raise ProjectUnavailableError("No active Resolve project.")
        return project

    def media_pool(self) -> Any:
        media_pool = self.project().GetMediaPool()
        if not media_pool:
            raise ProjectUnavailableError("Cannot access the Media Pool for the active project.")
        return media_pool

    def timeline(self) -> Any:
        timeline = self.project().GetCurrentTimeline()
        if not timeline:
            raise TimelineUnavailableError("No active timeline is selected.")
        return timeline

    def current_context_label(self) -> tuple[str, str]:
        project = self.project()
        timeline = self.timeline()
        return project.GetName() or "Untitled Project", timeline.GetName() or "Untitled Timeline"
