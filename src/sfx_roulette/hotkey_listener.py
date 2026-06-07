from __future__ import annotations

import ctypes
import ctypes.wintypes
import threading
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional


MODIFIERS = {
    "ALT": 0x0001,
    "CTRL": 0x0002,
    "CONTROL": 0x0002,
    "SHIFT": 0x0004,
    "WIN": 0x0008,
}

VK_KEYS = {str(i): 0x30 + i for i in range(10)}
VK_KEYS.update({chr(code): code for code in range(ord("A"), ord("Z") + 1)})
VK_KEYS.update({f"F{i}": 0x6F + i for i in range(1, 25)})


@dataclass(frozen=True)
class ParsedHotkey:
    modifiers: int
    vk: int


class WindowsHotkeyListener:
    def __init__(self, callback: Callable[[str], None], focus_title: str = "DaVinci Resolve") -> None:
        self.callback = callback
        self.focus_title = focus_title
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._hotkeys: Dict[int, str] = {}
        self._next_id = 1000

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, hotkeys: Iterable[str]) -> None:
        if self.is_running:
            self.stop()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, args=(list(hotkeys),), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        if self._thread:
            self._thread.join(timeout=1.5)

    def _run(self, hotkeys: list[str]) -> None:
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self._hotkeys.clear()
        try:
            for hotkey in hotkeys:
                parsed = parse_hotkey(hotkey)
                hotkey_id = self._next_id
                self._next_id += 1
                if user32.RegisterHotKey(None, hotkey_id, parsed.modifiers, parsed.vk):
                    self._hotkeys[hotkey_id] = hotkey
            msg = ctypes.wintypes.MSG()
            while not self._stop_event.is_set() and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312 and self._resolve_is_focused():
                    hotkey = self._hotkeys.get(int(msg.wParam))
                    if hotkey:
                        self.callback(hotkey)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            for hotkey_id in list(self._hotkeys):
                user32.UnregisterHotKey(None, hotkey_id)
            self._hotkeys.clear()
            self._thread_id = None

    def _resolve_is_focused(self) -> bool:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return self.focus_title.lower() in buffer.value.lower()


def parse_hotkey(hotkey: str) -> ParsedHotkey:
    parts = [part.strip().upper() for part in hotkey.replace("+", " + ").split("+") if part.strip()]
    if not parts:
        raise ValueError("Hotkey cannot be empty.")
    modifiers = 0
    key = parts[-1]
    for part in parts[:-1]:
        if part not in MODIFIERS:
            raise ValueError(f"Unsupported hotkey modifier: {part}")
        modifiers |= MODIFIERS[part]
    if key not in VK_KEYS:
        raise ValueError(f"Unsupported hotkey key: {key}")
    return ParsedHotkey(modifiers=modifiers, vk=VK_KEYS[key])
