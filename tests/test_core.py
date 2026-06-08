import random
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sfx_roulette.config_manager import ConfigManager
from sfx_roulette.bin_scanner import BinScanner
from sfx_roulette.hotkey_listener import parse_hotkey
from sfx_roulette.models import AudioClip, Mapping
from sfx_roulette.random_picker import RandomPicker
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
    def GetSetting(self, key: str) -> str:
        if key == "timelineFrameRate":
            return "24"
        return ""


class FakeResolveAPI:
    def project(self) -> FakeProject:
        return FakeProject()


class CoreTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
