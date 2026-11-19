"""Verify the built bundle and run its extracted compositor without the source tree."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_release import build


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.archive, cls.checksum, _ = build(cls.folder / "dist")
        with zipfile.ZipFile(cls.archive) as bundle:
            bundle.extractall(cls.folder / "extracted")
        cls.skill = cls.folder / "extracted/best-layout"

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_archive_contains_only_runtime_and_licensed_fonts(self):
        with zipfile.ZipFile(self.archive) as bundle:
            self.assertIsNone(bundle.testzip())
            names = bundle.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(all(n.startswith("best-layout/") for n in names))
            self.assertFalse(any(any(part in n.lower() for part in
                                     ("oswald", "font-specimens", "__pycache__", "tests/", ".html", ".svg")) for n in names))
            for name in names:
                self.assertEqual(bundle.read(name), (ROOT / "skills" / name).read_bytes(), name)
            self.assertEqual(bundle.read("best-layout/LICENSE"), (ROOT / "LICENSE").read_bytes())
            fonts = json.loads(bundle.read("best-layout/assets/fonts/manifest.json"))["fonts"]
            self.assertEqual(len(fonts), 10)
            for font in fonts:
                for field, digest in (("path", "sha256"), ("license", "license_sha256")):
                    data = bundle.read("best-layout/assets/fonts/" + font[field])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), font[digest])
            for relative in ("SKILL.md", "THIRD_PARTY_NOTICES.md", "agents/openai.yaml",
                             "assets/examples/poster.json", "references/layout-patterns.json"):
                self.assertIn("best-layout/" + relative, names)
            patterns = json.loads(bundle.read("best-layout/references/layout-patterns.json"))
            self.assertEqual(patterns["schema_version"], 1)
            self.assertGreaterEqual(len(patterns["patterns"]), 24)
        expected = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.assertEqual(self.checksum.read_text(encoding="utf-8").split()[0], expected)

    def test_extracted_skill_runs_from_an_unrelated_directory(self):
        skill = self.skill
        cwd = self.folder / "different-cwd"
        cwd.mkdir(exist_ok=True)
        output, report = cwd / "final.png", cwd / "checks.json"
        command = [sys.executable, "-X", "utf8", str(skill / "scripts/compose.py"),
                   str(skill / "assets/examples/poster.json"), str(output), "--report", str(report)]
        if os.environ.get("BEST_LAYOUT_CHROMIUM"):
            command += ["--chromium", os.environ["BEST_LAYOUT_CHROMIUM"]]
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        data = json.loads(report.read_text(encoding="utf-8"))
        copy = json.loads((skill / "assets/examples/poster.json").read_text(encoding="utf-8"))["copy"]
        self.assertEqual({b["copy_id"]: b["text"] for b in data["blocks"]}, copy)
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), data["sha256"])
        with Image.open(io.BytesIO(output.read_bytes())) as im:
            im.load()
            self.assertEqual(im.size, (1080, 1440))

    def test_extracted_skill_preserves_groups_and_rejects_overflow(self):
        cwd = self.folder / "protected-groups-cwd"
        cwd.mkdir()
        source = ROOT / "tests/typesetting/wrapping-regressions.json"
        spec = json.loads(source.read_text(encoding="utf-8"))
        spec_path, output, report = cwd / "layout.json", cwd / "final.png", cwd / "checks.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        command = [sys.executable, "-X", "utf8", str(self.skill / "scripts/compose.py"),
                   str(spec_path), str(output), "--report", str(report)]
        if os.environ.get("BEST_LAYOUT_CHROMIUM"):
            command += ["--chromium", os.environ["BEST_LAYOUT_CHROMIUM"]]
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        data = json.loads(report.read_text(encoding="utf-8"))
        groups = {"quantity": ("10 万人", "10 万件"), "contraction": ("Don't", "Don’t"),
                  "nonbreaking": ("AI\u00a0LAB",), "narrow_nonbreaking": ("AI\u202fLAB",)}
        for block in data["blocks"]:
            lines = [line["text"] for line in block["lines"]]
            self.assertEqual("".join(lines), spec["copy"][block["copy_id"]].replace("\n", ""))
            self.assertEqual(block["size"], 40)
            for token in groups[block["copy_id"]]:
                self.assertTrue(any(token in line for line in lines), (token, lines))
        with Image.open(output) as im:
            im.load()
            self.assertEqual(im.size, (940, 460))
        # Even --force cannot replace a valid image/report with an invalid job.
        original, original_report = output.read_bytes(), report.read_bytes()
        spec["blocks"][0]["width"] = 120
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        failed = subprocess.run(command + ["--force"], cwd=cwd, capture_output=True,
                                text=True, encoding="utf-8", timeout=60)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("group exceeds width", failed.stderr)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(report.read_bytes(), original_report)

    def test_rebuild_requires_explicit_force_and_preserves_existing_bundle(self):
        before = self.archive.read_bytes()
        with self.assertRaises(FileExistsError):
            build(self.archive.parent)
        self.assertEqual(self.archive.read_bytes(), before)

    def test_extracted_font_proofs_are_self_contained(self):
        cwd = self.folder / "font-proof-cwd"
        cwd.mkdir()
        output = cwd / "proofs"
        command = [sys.executable, "-X", "utf8", str(self.skill / "scripts/proof_fonts.py"),
                   str(self.skill / "assets/examples/poster.json"), str(output),
                   "--copy-id", "title", "--fonts", "source-han-serif", "xiangcui"]
        if os.environ.get("BEST_LAYOUT_CHROMIUM"):
            command += ["--chromium", os.environ["BEST_LAYOUT_CHROMIUM"]]
        done = subprocess.run(command, cwd=cwd, capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", errors="replace"))
        report = json.loads((output / "proofs.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report["candidates"]), 2)
        for row in report["candidates"]:
            self.assertEqual(row["render"]["blocks"][0]["text"], "山川有光")
            self.assertTrue((output / row["image"]).is_file())

    def test_extracted_ink_cuts_use_verified_transparent_title(self):
        cwd = self.folder / "ink-cut-cwd"
        cwd.mkdir()
        spec = {"version": 1, "canvas": {"width": 500, "height": 180, "background": "transparent"},
                "copy": {"title": "山川有光"}, "graphics": [],
                "blocks": [{"copy_id": "title", "font": "source-han-sans", "x": 20, "y": 20,
                            "width": 450, "height": 140, "size": 72, "color": "#272823"}]}
        (cwd / "type.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        command = [sys.executable, "-X", "utf8", str(self.skill / "scripts/compose.py"),
                   str(cwd / "type.json"), str(cwd / "type.png"), "--report", str(cwd / "source.json")]
        browser = ["--chromium", os.environ["BEST_LAYOUT_CHROMIUM"]] if os.environ.get("BEST_LAYOUT_CHROMIUM") else []
        done = subprocess.run(command + browser, cwd=cwd, capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", errors="replace"))
        source = json.loads((cwd / "source.json").read_text(encoding="utf-8"))
        line = source["blocks"][0]["lines"][0]
        y = (line["top"] + line["bottom"]) / 2
        cut = {"layer": "type.png", "source_report": "source.json",
               "cuts": [[[0, y], [500, y], [500, y + 2], [0, y + 2]]]}
        (cwd / "cuts.json").write_text(json.dumps(cut), encoding="utf-8")
        styled = cwd / "styled.png"
        command = [sys.executable, "-X", "utf8", str(self.skill / "scripts/cut_ink.py"),
                   str(cwd / "cuts.json"), str(styled), "--report", str(cwd / "styled.json")]
        done = subprocess.run(command + browser, cwd=cwd, capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", errors="replace"))
        report = json.loads((cwd / "styled.json").read_text(encoding="utf-8"))
        self.assertEqual(report["source_sha256"], source["sha256"])
        self.assertEqual(report["blocks"][0]["text"], "山川有光")
        self.assertGreater(report["changed_alpha_pixels"], 0)
        with Image.open(styled) as image:
            self.assertEqual(image.size, (500, 180))
            self.assertIn(0, image.getchannel("A").getextrema())


if __name__ == "__main__":
    unittest.main(verbosity=2)
