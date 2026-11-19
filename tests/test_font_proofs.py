"""Verify real candidate PNGs preserve copy, assets and non-title pixels."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/best-layout/scripts"
sys.path.insert(0, str(SCRIPTS))
from proof_fonts import candidates, proof


def layout():
    return {"version": 1, "canvas": {"width": 800, "height": 440, "background": "#F4F0E8"},
            "copy": {"title": "古巴经济", "body": "原文 20 ℃；2026.10.18"},
            "graphics": [{"type": "image", "path": "art.png", "x": 500, "y": 250,
                          "width": 120, "height": 120}],
            "blocks": [{"copy_id": "title", "font": "source-han-serif", "size": 100,
                        "x": 24, "y": 24, "width": 700, "height": 160, "color": "#293A32"},
                       {"copy_id": "body", "font": "source-han-sans", "size": 24,
                        "x": 24, "y": 390, "width": 750, "height": 45, "color": "#293A32"}]}


class FontProofTests(unittest.TestCase):
    def test_selection_rejects_unknown_or_repeated_inputs(self):
        for ids, fonts in ((["absent"], ["wdxl"]), (["title", "title"], ["wdxl"]),
                           (["title"], ["absent"]), (["title"], ["wdxl", "wdxl"])):
            with self.subTest(ids=ids, fonts=fonts), self.assertRaises(ValueError):
                candidates(layout(), ids, fonts)

    def test_cli_preserves_copy_assets_and_body_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "source"
            source.mkdir()
            Image.new("RGB", (32, 32), (35, 98, 71)).save(source / "art.png")
            spec = source / "layout.json"
            original = json.dumps(layout(), ensure_ascii=False).encode("utf-8")
            spec.write_bytes(original)
            out = folder / "proofs"
            command = [sys.executable, "-X", "utf8", str(SCRIPTS / "proof_fonts.py"),
                       str(spec), str(out), "--copy-id", "title", "--fonts", "source-han-serif", "wdxl"]
            if os.environ.get("BEST_LAYOUT_CHROMIUM"):
                command += ["--chromium", os.environ["BEST_LAYOUT_CHROMIUM"]]
            done = subprocess.run(command, cwd=folder, capture_output=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", errors="replace"))
            data = json.loads((out / "proofs.json").read_text(encoding="utf-8"))
            self.assertIn("pending", data["visual_review"])
            for row in data["candidates"]:
                self.assertEqual({b["copy_id"]: b["text"] for b in row["render"]["blocks"]}, layout()["copy"])
                self.assertEqual(row["render"]["blocks"][0]["size"], 100)
                self.assertEqual(row["render"]["images"][0]["original"], [32, 32])
            with Image.open(out / "source-han-serif.png") as a, Image.open(out / "wdxl.png") as b:
                self.assertEqual(a.size, (800, 440))
                self.assertIsNotNone(ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox())
                self.assertEqual(a.crop((0, 200, 800, 440)).tobytes(), b.crop((0, 200, 800, 440)).tobytes())
            self.assertEqual(spec.read_bytes(), original)
            png = (out / "wdxl.png").read_bytes()
            again = subprocess.run(command, cwd=folder, capture_output=True, timeout=60)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual((out / "wdxl.png").read_bytes(), png)

    def test_overflow_is_not_fitted_or_marked_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            spec = layout()
            spec["graphics"] = []
            spec["blocks"][0]["width"] = 30
            path = folder / "layout.json"
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            out = folder / "failed"
            with self.assertRaisesRegex(RuntimeError, "Font proof failed.*source-han-serif"):
                proof(path, out, ["title"], ["source-han-serif"], os.environ.get("BEST_LAYOUT_CHROMIUM"))
            self.assertFalse((out / "proofs.json").exists())
            self.assertFalse((out / "source-han-serif.png").exists())

    def test_missing_glyph_fails_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            spec = layout()
            spec["graphics"] = []
            spec["copy"]["title"] = "古巴，2026"
            path = folder / "layout.json"
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing glyphs"):
                proof(path, folder / "failed", ["title"], ["qiji"])
            self.assertFalse((folder / "failed").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
