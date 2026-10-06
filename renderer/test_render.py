import tempfile
import unittest
from pathlib import Path
from render import make_subtitles

class SubtitleTests(unittest.TestCase):
    def test_full_script_remains_in_timed_subtitles(self):
        script = "Первое предложение. Второе предложение завершается полностью."
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "captions.srt"
            make_subtitles(script, 37.25, target)
            content = target.read_text(encoding="utf-8")
        visible = " ".join(line for line in content.splitlines() if line and not line.isdigit() and "-->" not in line)
        self.assertEqual(" ".join(visible.split()), script)
        self.assertIn("00:00:37,250", content)

    def test_long_audio_is_not_capped_at_forty_seconds(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "captions.srt"
            make_subtitles("слова " * 100, 61.0, target)
            content = target.read_text(encoding="utf-8")
        self.assertIn("00:01:01,000", content)

if __name__ == "__main__":
    unittest.main()
