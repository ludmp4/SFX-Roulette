from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from .controller import SFXRouletteController
from .errors import SFXRouletteError
from .hotkey_listener import WindowsHotkeyListener
from .timeline_inserter import RECORD_FRAME_ABSOLUTE, RECORD_FRAME_RELATIVE


PLACEMENT_LABELS = {
    "Absolute Timecode": RECORD_FRAME_ABSOLUTE,
    "Subtract Timeline Start": RECORD_FRAME_RELATIVE,
}
PLACEMENT_VALUES = {value: key for key, value in PLACEMENT_LABELS.items()}


class SFXRouletteUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("SFX Roulette")
        self.root.geometry("880x560")
        self.status_queue: queue.Queue[str] = queue.Queue()
        self.controller = SFXRouletteController(status_callback=self.post_status)
        self.hotkey_listener = WindowsHotkeyListener(self._on_hotkey)
        self.bin_names: list[str] = []
        self._autosave_after_id: Optional[str] = None
        self._populating_selection = False
        self._selected_mapping_id: Optional[str] = None
        self._build()
        self._load_initial_state()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(150, self._drain_status_queue)

    def run(self) -> None:
        self.root.mainloop()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        self.mapping_table = ttk.Treeview(
            frame,
            columns=("hotkey", "bin", "track", "count"),
            show="headings",
            height=12,
        )
        for key, label, width in (
            ("hotkey", "Hotkey", 160),
            ("bin", "Assigned Bin", 330),
            ("track", "Assigned Audio Track", 150),
            ("count", "Clip Count", 100),
        ):
            self.mapping_table.heading(key, text=label)
            self.mapping_table.column(key, width=width, anchor=tk.W)
        self.mapping_table.pack(fill=tk.BOTH, expand=True)
        self.mapping_table.bind("<<TreeviewSelect>>", lambda _event: self._populate_from_selection())

        form = ttk.Frame(frame)
        form.pack(fill=tk.X, pady=(12, 6))
        ttk.Label(form, text="Hotkey").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(form, text="Assigned Bin").grid(row=0, column=1, sticky=tk.W, padx=(8, 0))
        ttk.Label(form, text="Track").grid(row=0, column=2, sticky=tk.W, padx=(8, 0))
        ttk.Label(form, text="Placement").grid(row=0, column=3, sticky=tk.W, padx=(8, 0))

        self.hotkey_var = tk.StringVar(value="Ctrl+Alt+1")
        self.bin_var = tk.StringVar()
        self.track_var = tk.StringVar(value="Auto")
        self.placement_var = tk.StringVar(value=PLACEMENT_VALUES.get(self.controller.record_frame_mode, "Absolute Timecode"))
        ttk.Entry(form, textvariable=self.hotkey_var, width=22).grid(row=1, column=0, sticky=tk.EW)
        self.bin_combo = ttk.Combobox(form, textvariable=self.bin_var, values=self.bin_names, width=44)
        self.bin_combo.grid(row=1, column=1, sticky=tk.EW, padx=(8, 0))
        self.track_combo = ttk.Combobox(
            form,
            textvariable=self.track_var,
            values=["Auto", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"],
            width=18,
        )
        self.track_combo.grid(row=1, column=2, sticky=tk.EW, padx=(8, 0))
        self.placement_combo = ttk.Combobox(
            form,
            textvariable=self.placement_var,
            values=list(PLACEMENT_LABELS.keys()),
            width=24,
            state="readonly",
        )
        self.placement_combo.grid(row=1, column=3, sticky=tk.EW, padx=(8, 0))
        form.columnconfigure(1, weight=1)
        for variable in (self.hotkey_var, self.bin_var, self.track_var, self.placement_var):
            variable.trace_add("write", lambda *_args: self._schedule_autosave())
        self.bin_combo.bind("<<ComboboxSelected>>", lambda _event: self._schedule_autosave(delay_ms=50))
        self.track_combo.bind("<<ComboboxSelected>>", lambda _event: self._schedule_autosave(delay_ms=50))
        self.placement_combo.bind("<<ComboboxSelected>>", lambda _event: self._schedule_autosave(delay_ms=50))
        self.bin_combo.bind("<FocusOut>", lambda _event: self._schedule_autosave(delay_ms=50))
        self.track_combo.bind("<FocusOut>", lambda _event: self._schedule_autosave(delay_ms=50))

        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, pady=8)
        for label, command in (
            ("Add Mapping", self._add_mapping),
            ("Assign Mapping", self._assign_mapping),
            ("Remove Mapping", self._remove_mapping),
            ("Refresh Bins", self._refresh_bins),
            ("Test Insert", self._test_insert),
            ("Save Settings", self._save_settings),
            ("Start Hotkeys", self._start_hotkeys),
            ("Stop Hotkeys", self._stop_hotkeys),
        ):
            ttk.Button(controls, text=label, command=command).pack(side=tk.LEFT, padx=(0, 8))

        self.status_text = tk.Text(frame, height=9, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
        self.status_text.configure(state=tk.DISABLED)

    def _load_initial_state(self) -> None:
        self._refresh_table()
        try:
            self._refresh_bins()
            self.post_status("Ready. Resolve connection established.")
        except Exception as exc:
            self.post_status(f"Resolve connection pending: {exc}")

    def post_status(self, message: str) -> None:
        self.status_queue.put(message)

    def _drain_status_queue(self) -> None:
        while not self.status_queue.empty():
            self._append_status(self.status_queue.get())
        self.root.after(150, self._drain_status_queue)

    def _append_status(self, message: str) -> None:
        self.status_text.configure(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state=tk.DISABLED)

    def _refresh_bins(self) -> None:
        try:
            self.bin_names = self.controller.refresh_bins()
            self.bin_combo.configure(values=self.bin_names)
            self._refresh_table()
            self.post_status(f"Refreshed {len(self.bin_names)} Media Pool bins.")
        except Exception as exc:
            self._show_error(exc)

    def _refresh_table(self) -> None:
        for item in self.mapping_table.get_children():
            self.mapping_table.delete(item)
        for mapping in self.controller.mappings:
            count = ""
            if self.controller.bin_scanner:
                count = str(self.controller.bin_scanner.clip_count(mapping.bin_name))
            item_id = self.mapping_table.insert(
                "",
                tk.END,
                iid=mapping.id,
                values=(mapping.hotkey, mapping.bin_name, mapping.track_label, count),
            )
            if mapping.id == self._selected_mapping_id:
                self.mapping_table.selection_set(item_id)
                self.mapping_table.focus(item_id)

    def _populate_from_selection(self) -> None:
        selected = self.mapping_table.selection()
        if not selected:
            return
        hotkey, bin_name, track, _count = self.mapping_table.item(selected[0], "values")
        self._populating_selection = True
        try:
            self._selected_mapping_id = selected[0]
            self.hotkey_var.set(hotkey)
            self.bin_var.set(bin_name)
            self.track_var.set(track)
        finally:
            self._populating_selection = False

    def _add_mapping(self) -> None:
        try:
            track = self._parse_track(self.track_var.get())
            mapping = self.controller.add_mapping(self.hotkey_var.get(), self.bin_var.get(), track)
            self.controller.set_record_frame_mode(self._placement_mode())
            self.controller.save()
            self._selected_mapping_id = mapping.id
            self._refresh_table()
            self._restart_hotkeys_if_running()
            self.post_status(f"Added mapping {mapping.hotkey} -> {mapping.bin_name} -> {mapping.track_label}.")
        except Exception as exc:
            self._show_error(exc)

    def _assign_mapping(self) -> None:
        try:
            track = self._parse_track(self.track_var.get())
            mapping = self.controller.upsert_mapping(
                self.hotkey_var.get(),
                self.bin_var.get(),
                track,
                self._selected_mapping_id,
            )
            self.controller.set_record_frame_mode(self._placement_mode())
            self.controller.save()
            self._selected_mapping_id = mapping.id
            self._refresh_table()
            self._restart_hotkeys_if_running()
            self.post_status(f"Saved mapping {mapping.hotkey} -> {mapping.bin_name} -> {mapping.track_label}.")
        except Exception as exc:
            self._show_error(exc)

    def _remove_mapping(self) -> None:
        mapping_id = self._selected_mapping_id
        if not mapping_id:
            selected = self.mapping_table.selection()
            mapping_id = selected[0] if selected else ""
        if not mapping_id:
            messagebox.showinfo("SFX Roulette", "Select a mapping first.")
            return
        self.controller.remove_mapping(mapping_id)
        self.controller.save()
        self._selected_mapping_id = None
        self._refresh_table()
        self._restart_hotkeys_if_running()
        self.post_status("Removed selected mapping.")

    def _test_insert(self) -> None:
        selected = self.mapping_table.selection()
        if not selected:
            messagebox.showinfo("SFX Roulette", "Select a mapping first.")
            return
        hotkey = self.mapping_table.item(selected[0], "values")[0]
        try:
            self.post_status(self.controller.trigger_hotkey(hotkey))
            self._refresh_table()
        except Exception as exc:
            self._show_error(exc)

    def _save_settings(self) -> None:
        self.controller.set_record_frame_mode(self._placement_mode())
        self.controller.save()
        self.post_status("Settings saved.")

    def _schedule_autosave(self, delay_ms: int = 650) -> None:
        if self._populating_selection:
            return
        if self._autosave_after_id:
            self.root.after_cancel(self._autosave_after_id)
        self._autosave_after_id = self.root.after(delay_ms, self._autosave_current_mapping)

    def _autosave_current_mapping(self) -> None:
        self._autosave_after_id = None
        hotkey = self.hotkey_var.get().strip()
        bin_name = self.bin_var.get().strip()
        if not hotkey or not bin_name:
            return
        try:
            track = self._parse_track(self.track_var.get())
            mapping = self.controller.upsert_mapping(hotkey, bin_name, track, self._selected_mapping_id)
            self.controller.set_record_frame_mode(self._placement_mode())
            self.controller.save()
            self._selected_mapping_id = mapping.id
            self._refresh_table()
            self._restart_hotkeys_if_running()
            self.post_status(f"Auto-saved mapping {mapping.hotkey} -> {mapping.bin_name} -> {mapping.track_label}.")
        except Exception as exc:
            self._show_error(exc)

    def _placement_mode(self) -> str:
        return PLACEMENT_LABELS.get(self.placement_var.get(), RECORD_FRAME_ABSOLUTE)

    def _start_hotkeys(self) -> None:
        hotkeys = self.controller.unique_hotkeys()
        if not hotkeys:
            messagebox.showinfo("SFX Roulette", "Add at least one mapping before starting hotkeys.")
            return
        self.hotkey_listener.start(hotkeys)
        self.post_status("Hotkey listener running. Shortcuts fire only while Resolve is focused.")

    def _stop_hotkeys(self) -> None:
        self.hotkey_listener.stop()
        self.post_status("Hotkey listener stopped.")

    def _on_hotkey(self, hotkey: str) -> None:
        try:
            self.post_status(self.controller.trigger_hotkey(hotkey))
        except Exception as exc:
            self.post_status(f"Error: {exc}")

    def _restart_hotkeys_if_running(self) -> None:
        if self.hotkey_listener.is_running:
            self.hotkey_listener.start(self.controller.unique_hotkeys())

    def _show_error(self, exc: Exception) -> None:
        prefix = "Error" if isinstance(exc, SFXRouletteError) else "Unexpected error"
        self.post_status(f"{prefix}: {exc}")
        messagebox.showerror("SFX Roulette", str(exc))

    def _on_close(self) -> None:
        self.hotkey_listener.stop()
        self.controller.save()
        self.root.destroy()

    @staticmethod
    def _parse_track(value: str) -> Optional[int]:
        value = value.strip()
        if not value or value.casefold() == "auto":
            return None
        if value.upper().startswith("A"):
            value = value[1:]
        number = int(value)
        if number < 1:
            raise ValueError("Track number must be 1 or greater.")
        return number
