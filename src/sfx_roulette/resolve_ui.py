from __future__ import annotations

from typing import Any, Optional

from .controller import SFXRouletteController
from .hotkey_listener import WindowsHotkeyListener
from .timeline_inserter import RECORD_FRAME_ABSOLUTE, RECORD_FRAME_RELATIVE


PLACEMENTS = [
    ("At playhead timecode", RECORD_FRAME_ABSOLUTE),
    ("Subtract timeline start", RECORD_FRAME_RELATIVE),
]


class ResolveUI:
    def __init__(self, resolve: Any, bmd: Any) -> None:
        self.resolve = resolve
        self.controller = SFXRouletteController(self.status, resolve=resolve)
        self.listener = WindowsHotkeyListener(self.on_hotkey)
        self.mapping_ids: list[str] = []
        self.loading = False
        self.controls_initialized = False

        fusion = resolve.Fusion()
        self.ui = fusion.UIManager
        self.dispatcher = bmd.UIDispatcher(self.ui)
        self.window = self._build_window()
        self.items = self.window.GetItems()
        self._wire_events()
        self.refresh_bins()
        self.refresh_mappings()

    def _build_window(self):
        ui = self.ui
        return self.dispatcher.AddWindow(
            {"ID": "SFXRoulette", "WindowTitle": "SFX Roulette", "Geometry": [120, 120, 720, 470]},
            [
                ui.VGroup(
                    {"Spacing": 8, "Weight": 1},
                    [
                        ui.Label({"Text": "Mappings"}),
                        ui.ComboBox({"ID": "Mappings"}),
                        ui.HGroup(
                            {"Spacing": 8},
                            [
                                ui.VGroup(
                                    [ui.Label({"Text": "Hotkey"}), ui.LineEdit({"ID": "Hotkey", "Text": "Ctrl+Alt+1"})]
                                ),
                                ui.VGroup(
                                    {"Weight": 2},
                                    [ui.Label({"Text": "Media Pool bin"}), ui.ComboBox({"ID": "Bin", "Editable": True})],
                                ),
                                ui.VGroup(
                                    [ui.Label({"Text": "Audio track"}), ui.ComboBox({"ID": "Track"})]
                                ),
                            ],
                        ),
                        ui.HGroup(
                            {"Spacing": 8},
                            [
                                ui.Label({"Text": "Playhead placement", "MinimumSize": [130, 24]}),
                                ui.ComboBox({"ID": "Placement", "Weight": 1}),
                            ],
                        ),
                        ui.HGroup(
                            {"Spacing": 8},
                            [
                                ui.Button({"ID": "Add", "Text": "Add Mapping"}),
                                ui.Button({"ID": "Save", "Text": "Save Mapping"}),
                                ui.Button({"ID": "Remove", "Text": "Remove"}),
                                ui.Button({"ID": "Refresh", "Text": "Refresh Bins"}),
                                ui.Button({"ID": "Test", "Text": "Test Insert"}),
                            ],
                        ),
                        ui.HGroup(
                            {"Spacing": 8},
                            [
                                ui.Button({"ID": "Start", "Text": "Start Hotkeys"}),
                                ui.Button({"ID": "Stop", "Text": "Stop Hotkeys"}),
                                ui.Button({"ID": "Close", "Text": "Close"}),
                            ],
                        ),
                        ui.TextEdit({"ID": "Status", "ReadOnly": True, "PlainText": "Ready.", "Weight": 1}),
                        ui.Button({"ID": "HotkeyBridge", "Hidden": True}),
                    ],
                )
            ],
        )

    def _wire_events(self) -> None:
        on = self.window.On
        on.SFXRoulette.Close = lambda _ev: self.close()
        on.Close.Clicked = lambda _ev: self.close()
        on.Mappings.CurrentIndexChanged = lambda _ev: self.load_selected()
        on.Add.Clicked = lambda _ev: self.add_mapping()
        on.Save.Clicked = lambda _ev: self.save_mapping()
        on.Remove.Clicked = lambda _ev: self.remove_mapping()
        on.Refresh.Clicked = lambda _ev: self.refresh_bins()
        on.Test.Clicked = lambda _ev: self.test_insert()
        on.Start.Clicked = lambda _ev: self.start_hotkeys()
        on.Stop.Clicked = lambda _ev: self.stop_hotkeys()
        on.HotkeyBridge.HotkeyTriggered = self.handle_hotkey_event
        on.Hotkey.EditingFinished = lambda _ev: self.autosave()
        on.Bin.CurrentIndexChanged = lambda _ev: self.autosave()
        on.Bin.EditingFinished = lambda _ev: self.autosave()
        on.Track.CurrentIndexChanged = lambda _ev: self.autosave()
        on.Placement.CurrentIndexChanged = lambda _ev: self.autosave()

    def run(self) -> None:
        self.window.Show()
        self.dispatcher.RunLoop()
        self.window.Hide()

    def status(self, message: str) -> None:
        try:
            self.items["Status"].PlainText = message
        except Exception:
            print(message)

    def refresh_bins(self) -> None:
        try:
            names = self.controller.refresh_bins()
            current = self.items["Bin"].CurrentText
            self.loading = True
            self.items["Bin"].Clear()
            for name in names:
                self.items["Bin"].AddItem(name)
            if current:
                self.items["Bin"].CurrentText = current
            self.status(f"Found {len(names)} Media Pool bins.")
        except Exception as exc:
            self.status(f"ERROR: {exc}")
        finally:
            self.loading = False

    def refresh_mappings(self, selected_id: Optional[str] = None) -> None:
        self.loading = True
        combo = self.items["Mappings"]
        combo.Clear()
        self.mapping_ids = []
        selected_index = 0
        for index, mapping in enumerate(self.controller.mappings):
            self.mapping_ids.append(mapping.id)
            combo.AddItem(f"{mapping.hotkey}  |  {mapping.bin_name}  |  {mapping.track_label}")
            if mapping.id == selected_id:
                selected_index = index
        if not self.controls_initialized:
            for label in ["Auto"] + [f"A{i}" for i in range(1, 33)]:
                self.items["Track"].AddItem(label)
            for label, _mode in PLACEMENTS:
                self.items["Placement"].AddItem(label)
            self.controls_initialized = True
        if self.mapping_ids:
            combo.CurrentIndex = selected_index
        placement_index = 1 if self.controller.record_frame_mode == RECORD_FRAME_RELATIVE else 0
        self.items["Placement"].CurrentIndex = placement_index
        self.loading = False
        self.load_selected()

    def selected_mapping(self):
        index = int(self.items["Mappings"].CurrentIndex)
        if index < 0 or index >= len(self.mapping_ids):
            return None
        mapping_id = self.mapping_ids[index]
        return next((item for item in self.controller.mappings if item.id == mapping_id), None)

    def load_selected(self) -> None:
        mapping = self.selected_mapping()
        if not mapping:
            return
        self.loading = True
        self.items["Hotkey"].Text = mapping.hotkey
        self.items["Bin"].CurrentText = mapping.bin_name
        self.items["Track"].CurrentIndex = 0 if mapping.target_audio_track is None else mapping.target_audio_track
        self.loading = False

    def form_values(self):
        track_text = self.items["Track"].CurrentText
        track = None if not track_text or track_text == "Auto" else int(track_text[1:])
        return self.items["Hotkey"].Text.strip(), self.items["Bin"].CurrentText.strip(), track

    def save_placement(self) -> None:
        index = max(0, int(self.items["Placement"].CurrentIndex))
        self.controller.set_record_frame_mode(PLACEMENTS[index][1])

    def add_mapping(self) -> None:
        try:
            hotkey, bin_name, track = self.form_values()
            mapping = self.controller.add_mapping(hotkey, bin_name, track)
            self.save_placement()
            self.controller.save()
            self.refresh_mappings(mapping.id)
            self.restart_hotkeys()
            self.status(f"Added {mapping.hotkey} -> {mapping.bin_name} -> {mapping.track_label}.")
        except Exception as exc:
            self.status(f"ERROR: {exc}")

    def save_mapping(self) -> None:
        mapping = self.selected_mapping()
        if not mapping:
            self.add_mapping()
            return
        try:
            hotkey, bin_name, track = self.form_values()
            mapping = self.controller.update_mapping(mapping.id, hotkey, bin_name, track)
            self.save_placement()
            self.controller.save()
            self.refresh_mappings(mapping.id)
            self.restart_hotkeys()
            self.status(f"Saved {mapping.hotkey} -> {mapping.bin_name} -> {mapping.track_label}.")
        except Exception as exc:
            self.status(f"ERROR: {exc}")

    def autosave(self) -> None:
        if not self.loading:
            self.save_mapping()

    def remove_mapping(self) -> None:
        mapping = self.selected_mapping()
        if not mapping:
            return
        self.controller.remove_mapping(mapping.id)
        self.controller.save()
        self.refresh_mappings()
        self.restart_hotkeys()
        self.status("Mapping removed.")

    def test_insert(self) -> None:
        mapping = self.selected_mapping()
        if not mapping:
            self.status("Select a mapping first.")
            return
        try:
            self.status(self.controller.insert_for_mapping(mapping))
        except Exception as exc:
            self.status(f"ERROR: {exc}")

    def on_hotkey(self, hotkey: str) -> None:
        self.ui.QueueEvent(self.items["HotkeyBridge"], "HotkeyTriggered", {"hotkey": hotkey})

    def handle_hotkey_event(self, event) -> None:
        hotkey = event.get("hotkey", "")
        try:
            self.status(self.controller.trigger_hotkey(hotkey))
        except Exception as exc:
            self.status(f"ERROR: {exc}")

    def start_hotkeys(self) -> None:
        hotkeys = self.controller.unique_hotkeys()
        if not hotkeys:
            self.status("Add a mapping first.")
            return
        registered = self.listener.start(hotkeys)
        errors = self.listener.registration_errors
        if not registered:
            detail = "; ".join(errors) or "Windows rejected the shortcuts."
            self.status(f"Hotkeys could not start: {detail}")
            return
        message = f"Hotkeys running: {', '.join(registered)}."
        if errors:
            message += " Not registered: " + "; ".join(errors) + "."
        self.status(message)

    def stop_hotkeys(self) -> None:
        self.listener.stop()
        self.status("Hotkeys stopped.")

    def restart_hotkeys(self) -> None:
        if self.listener.is_running:
            self.listener.start(self.controller.unique_hotkeys())

    def close(self) -> None:
        self.listener.stop()
        self.controller.save()
        self.dispatcher.ExitLoop()


def show_ui(resolve: Any, bmd: Any) -> None:
    ResolveUI(resolve, bmd).run()
