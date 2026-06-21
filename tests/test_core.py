import random
import sys
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sfx_roulette.config_manager import ConfigManager
from sfx_roulette.bin_scanner import BinScanner
from sfx_roulette.controller import SFXRouletteController
from sfx_roulette.hotkey_listener import WindowsHotkeyListener, parse_hotkey
from sfx_roulette.models import AudioClip, Mapping
from sfx_roulette.random_picker import RandomPicker
from sfx_roulette.resolve_api import ResolveAPI
from sfx_roulette.timeline_inserter import RECORD_FRAME_RELATIVE, TimelineInserter


class FakeTimeline:
    def __init__(self, current_timecode: str, start_timecode: str | None = None, start_frame: int | None = None) -> None:
        self.current_timecode = current_timecode
        self.start_timecode = start_timecode
        self.start_frame = start_frame

    def GetCurrentTimecode(self) -> str:
        return self.current_timecode

    def GetStartTimecode(self) -> str | None:
        return self.start_timecode

    def GetStartFrame(self) -> int | None:
        return self.start_frame


class FakeProject:
    def __init__(self, fps: str = "24") -> None:
        self.fps = fps

    def GetSetting(self, key: str) -> str:
        if key == "timelineFrameRate":
            return self.fps
        return ""


class FakeResolveAPI:
    def __init__(self, fps: str = "24") -> None:
        self.fps = fps

    def project(self) -> FakeProject:
        return FakeProject(self.fps)


class CoreTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows hotkey API test")
    def test_windows_hotkey_listener_dispatches_registered_message(self) -> None:
        fired = threading.Event()
        listener = WindowsHotkeyListener(lambda _hotkey: fired.set(), focus_title="")
        listener._resolve_is_focused = lambda: True
        try:
            registered = listener.start(["Ctrl+Shift+F24"])
            self.assertEqual(registered, ["Ctrl+Shift+F24"])
            hotkey_id = next(iter(listener._hotkeys))
            import ctypes

            ctypes.windll.user32.PostThreadMessageW(listener._thread_id, 0x0312, hotkey_id, 0)
            self.assertTrue(fired.wait(1.0))
        finally:
            listener.stop()

    def test_hotkey_capture_builds_chord_from_pressed_keys(self) -> None:
        class FakeUser32:
            @staticmethod
            def GetAsyncKeyState(vk: int) -> int:
                return 0x8000 if vk in {0x11, 0x12, 0x31} else 0

        fake_windll = type("FakeWindll", (), {"user32": FakeUser32()})()
        captured: list[str] = []
        listener = WindowsHotkeyListener(lambda _hotkey: None)
        with mock.patch("sfx_roulette.hotkey_listener.ctypes.windll", fake_windll):
            listener.capture_next(captured.append)
            listener._capture_thread.join(timeout=1.0)
        self.assertEqual(captured, ["Ctrl+Alt+1"])

    def test_resolve_api_uses_injected_resolve_context(self) -> None:
        resolve = object()
        self.assertIs(ResolveAPI(resolve).resolve, resolve)

    def test_picker_avoids_last_clip_when_possible(self) -> None:
        clips = [
            AudioClip(id="a", name="A", path="", media_pool_item=object()),
            AudioClip(id="b", name="B", path="", media_pool_item=object()),
        ]
        picker = RandomPicker(random.Random(1))
        chosen = picker.choose(clips, last_used_clip_id="a")
        self.assertEqual(chosen.id, "b")

    def test_picker_uses_single_clip(self) -> None:
        clip = AudioClip(id="a", name="A", path="", media_pool_item=object())
        self.assertEqual(RandomPicker().choose([clip], last_used_clip_id="a"), clip)

    def test_config_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            manager = ConfigManager(path)
            manager.save([Mapping("Ctrl+Alt+1", "Whooshes", 3, "clip-1")])
            [mapping] = manager.load()
            self.assertEqual(mapping.hotkey, "Ctrl+Alt+1")
            self.assertEqual(mapping.bin_name, "Whooshes")
            self.assertEqual(mapping.target_audio_track, 3)
            self.assertEqual(mapping.last_used_clip_id, "clip-1")

    def test_config_records_frame_mode_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            manager = ConfigManager(path)
            manager.save([Mapping("Ctrl+Alt+1", "Whooshes", 3)], RECORD_FRAME_RELATIVE)
            self.assertEqual(manager.load_record_frame_mode(), RECORD_FRAME_RELATIVE)

    def test_config_preserves_duplicate_hotkey_mappings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            manager = ConfigManager(path)
            manager.save(
                [
                    Mapping("Ctrl+Alt+1", "Whooshes", 3),
                    Mapping("Ctrl+Alt+1", "Hits", 4),
                ]
            )
            mappings = manager.load()
            self.assertEqual([mapping.bin_name for mapping in mappings], ["Whooshes", "Hits"])
            self.assertEqual(len({mapping.id for mapping in mappings}), 2)

    def test_trigger_hotkey_runs_all_matching_mappings(self) -> None:
        controller = SFXRouletteController.__new__(SFXRouletteController)
        controller.mappings = [
            Mapping("Ctrl+Alt+1", "Whooshes", 3),
            Mapping("Ctrl+Alt+1", "Hits", 4),
            Mapping("Ctrl+Alt+2", "Glitches", 5),
        ]
        inserted = []

        def fake_insert(mapping: Mapping) -> str:
            inserted.append((mapping.bin_name, mapping.target_audio_track))
            return mapping.bin_name

        controller.insert_for_mapping = fake_insert
        self.assertEqual(controller.trigger_hotkey("Ctrl+Alt+1"), "Inserted 2 SFX mappings for Ctrl+Alt+1.")
        self.assertEqual(inserted, [("Whooshes", 3), ("Hits", 4)])
        self.assertEqual(controller.unique_hotkeys(), ["Ctrl+Alt+1", "Ctrl+Alt+2"])

    def test_hotkey_parser(self) -> None:
        parsed = parse_hotkey("Ctrl+Alt+1")
        self.assertEqual(parsed.modifiers, 0x0002 | 0x0001)
        self.assertEqual(parsed.vk, 0x31)

    def test_audio_detection_accepts_file_extensions_from_name(self) -> None:
        self.assertTrue(BinScanner._looks_audio({}, "whoosh_01.mp3", ""))
        self.assertTrue(BinScanner._looks_audio({}, "hit_01.wav", ""))

    def test_audio_detection_accepts_resolve_file_name_metadata(self) -> None:
        self.assertTrue(BinScanner._looks_audio({"File Name": "glitch.wav"}, "glitch", ""))

    def test_current_frame_defaults_to_absolute_timecode(self) -> None:
        timeline = FakeTimeline(current_timecode="01:00:10:00", start_timecode="01:00:00:00")
        self.assertEqual(TimelineInserter(FakeResolveAPI())._current_frame(timeline), 86640)

    def test_current_frame_can_subtract_timeline_start_timecode(self) -> None:
        timeline = FakeTimeline(current_timecode="01:00:10:00", start_timecode="01:00:00:00")
        self.assertEqual(TimelineInserter(FakeResolveAPI(), RECORD_FRAME_RELATIVE)._current_frame(timeline), 240)

    def test_current_frame_can_use_start_frame_when_available(self) -> None:
        timeline = FakeTimeline(current_timecode="01:00:10:00", start_timecode="00:00:00:00", start_frame=86400)
        self.assertEqual(TimelineInserter(FakeResolveAPI(), RECORD_FRAME_RELATIVE)._current_frame(timeline), 240)

    def test_current_frame_uses_exact_fractional_timeline_fps(self) -> None:
        timeline = FakeTimeline(current_timecode="01:00:10:00", start_timecode="01:00:00:00")
        self.assertEqual(TimelineInserter(FakeResolveAPI("23.976"))._current_frame(timeline), 86553)


if __name__ == "__main__":
    unittest.main()
