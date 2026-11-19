"""Actual alpha cuts preserve source copy evidence and unaffected glyph pixels."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image
from playwright.sync_api import Error as PlaywrightError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/best-layout/scripts"))
from compose import browser_page, prepare, render
from cut_ink import cut_ink


class InkCutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        spec = {"version": 1, "canvas": {"width": 500, "height": 280, "background": "transparent"},
                "copy": {"title": "崩溃"}, "graphics": [],
                "blocks": [{"copy_id": "title", "font": "source-han-sans", "x": 20, "y": 20,
                            "width": 450, "height": 240, "size": 180, "color": "#272823"}]}
        with browser_page(os.environ.get("BEST_LAYOUT_CHROMIUM")) as page:
            raw, report = render(page, prepare(spec, cls.folder))
        (cls.folder / "type.png").write_bytes(raw)
        (cls.folder / "source.json").write_text(json.dumps(report), encoding="utf-8")
        with Image.open(cls.folder / "type.png") as im:
            alpha = im.getchannel("A")
            cls.row = max(range(25, 230), key=lambda y: sum(alpha.crop((0, y, 500, y + 1)).getdata()))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def spec(self, name, changes=None):
        y = self.row
        data = {"layer": "type.png", "source_report": "source.json",
                "cuts": [[[0, y], [500, y], [500, y + 2], [0, y + 2]]]}
        data.update(changes or {})
        path = self.folder / (name + ".json")
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_alpha_changes_only_in_deliberate_cut_and_copy_evidence_survives(self):
        out = self.folder / "cut.png"
        result = cut_ink(self.spec("cut"), out, self.folder / "cut-report.json",
                         os.environ.get("BEST_LAYOUT_CHROMIUM"))
        self.assertEqual([b["text"] for b in result["blocks"]], ["崩溃"])
        self.assertGreater(result["changed_alpha_pixels"], 0)
        self.assertGreater(result["retained_alpha_fraction"], 0.95)
        self.assertIn("pending", result["visual_review"])
        with Image.open(self.folder / "type.png") as source, Image.open(out) as styled:
            a, b = source.getchannel("A"), styled.getchannel("A")
            self.assertEqual(a.crop((0, 0, 500, self.row - 1)).tobytes(), b.crop((0, 0, 500, self.row - 1)).tobytes())
            self.assertEqual(a.crop((0, self.row + 3, 500, 280)).tobytes(), b.crop((0, self.row + 3, 500, 280)).tobytes())
        before = out.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            cut_ink(self.spec("existing"), out)
        self.assertEqual(out.read_bytes(), before)

    def test_changed_source_is_rejected_before_writing(self):
        source = json.loads((self.folder / "source.json").read_text(encoding="utf-8"))
        source["sha256"] = "0" * 64
        (self.folder / "mismatch.json").write_text(json.dumps(source), encoding="utf-8")
        out = self.folder / "mismatch.png"
        with self.assertRaisesRegex(ValueError, "does not match"):
            cut_ink(self.spec("bad-source", {"source_report": "mismatch.json"}), out)
        self.assertFalse(out.exists())

    def test_empty_malformed_and_ineffective_cuts_fail_without_output(self):
        for index, cuts in enumerate(([], [[[0, 0], [2, 1]]],
                                      [[[0, 0], [5, 0], [5, 3], [0, 3]]])):
            out = self.folder / f"invalid-{index}.png"
            with self.subTest(cuts=cuts), self.assertRaises((ValueError, PlaywrightError)):
                cut_ink(self.spec(f"invalid-{index}", {"cuts": cuts}), out,
                        chromium=os.environ.get("BEST_LAYOUT_CHROMIUM"))
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
