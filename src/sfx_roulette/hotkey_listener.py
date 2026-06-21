from __future__ import annotations

import ctypes
import ctypes.wintypes
import threading
import time
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
        self._ready_event = threading.Event()
        self._hotkeys: Dict[int, str] = {}
        self._registration_errors: list[str] = []
        self._next_id = 1000
        self._capture_thread: Optional[threading.Thread] = None
        self._capture_stop = threading.Event()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def registered_hotkeys(self) -> list[str]:
        return list(self._hotkeys.values())

    @property
    def registration_errors(self) -> list[str]:
        return list(self._registration_errors)

    def start(self, hotkeys: Iterable[str]) -> list[str]:
        if self.is_running:
            self.stop()
        self._stop_event.clear()
        self._ready_event.clear()
        self._thread = threading.Thread(target=self._run, args=(list(hotkeys),), daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=1.5)
        return self.registered_hotkeys

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        if self._thread:
            self._thread.join(timeout=1.5)

    def capture_next(self, callback: Callable[[str], None]) -> None:
        self.cancel_capture()
        self._capture_stop.clear()
        self._capture_thread = threading.Thread(target=self._capture_run, args=(callback,), daemon=True)
        self._capture_thread.start()

    def cancel_capture(self) -> None:
        self._capture_stop.set()
        if self._capture_thread and self._capture_thread is not threading.current_thread():
            self._capture_thread.join(timeout=0.5)
        self._capture_thread = None

    def _capture_run(self, callback: Callable[[str], None]) -> None:
        user32 = ctypes.windll.user32
        key_names = {value: key for key, value in VK_KEYS.items()}
        escape = 0x1B
        while not self._capture_stop.is_set():
            if user32.GetAsyncKeyState(escape) & 0x8000:
                callback("")
                return
            for vk, key_name in key_names.items():
                if not (user32.GetAsyncKeyState(vk) & 0x8000):
                    continue
                modifiers = []
                if user32.GetAsyncKeyState(0x11) & 0x8000:
                    modifiers.append("Ctrl")
                if user32.GetAsyncKeyState(0x12) & 0x8000:
                    modifiers.append("Alt")
                if user32.GetAsyncKeyState(0x10) & 0x8000:
                    modifiers.append("Shift")
                if (user32.GetAsyncKeyState(0x5B) | user32.GetAsyncKeyState(0x5C)) & 0x8000:
                    modifiers.append("Win")
                if not modifiers and not key_name.startswith("F"):
                    continue
                callback("+".join(modifiers + [key_name]))
                return
            time.sleep(0.02)

    def _run(self, hotkeys: list[str]) -> None:
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self._hotkeys.clear()
        self._registration_errors.clear()
        try:
            for hotkey in hotkeys:
                try:
                    parsed = parse_hotkey(hotkey)
                    hotkey_id = self._next_id
                    self._next_id += 1
                    if user32.RegisterHotKey(None, hotkey_id, parsed.modifiers, parsed.vk):
                        self._hotkeys[hotkey_id] = hotkey
                    else:
                        self._registration_errors.append(f"{hotkey} is already used by Windows or another app")
                except Exception as exc:
                    self._registration_errors.append(f"{hotkey}: {exc}")
            self._ready_event.set()
            if not self._hotkeys:
                return
            msg = ctypes.wintypes.MSG()
            while not self._stop_event.is_set() and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312 and self._resolve_is_focused():
                    hotkey = self._hotkeys.get(int(msg.wParam))
                    if hotkey:
                        self.callback(hotkey)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._ready_event.set()
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
        title = buffer.value.lower()
        return self.focus_title.lower() in title or "sfx roulette" in title


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
