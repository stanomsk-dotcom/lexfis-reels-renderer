import tempfile
import unittest
from pathlib import Path
from render import make_subtitles
from scenes import _art_kind, _svg, _theme


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

    def test_scene_text_does_not_overlap_subtitles_and_prompt_changes_art(self):
        tax = _theme("Налоговый вычет", "Документы для ФНС")
        housing = _theme("Спор об аренде квартиры", "Жилищный вопрос")
        tax_svg = _svg(2, 5, tax, 0)
        housing_svg = _svg(2, 5, housing, 3)
        self.assertNotEqual(tax[:3], housing[:3])
        self.assertNotIn("вычет", tax_svg.lower())
        self.assertNotIn("подготовить документы", tax_svg.lower())
        self.assertEqual(tax_svg.count("<text"), 4)
        self.assertNotIn('y="850"', tax_svg)
        self.assertEqual(_art_kind("телефон с открытым экраном", 0), 1)
        self.assertEqual(_art_kind("папка с документами", 0), 3)


if __name__ == "__main__":
    unittest.main()
