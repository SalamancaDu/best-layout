"""Real-browser regressions for font accuracy, copy integrity and composition.

Run with BEST_LAYOUT_CHROMIUM set if Playwright has no default browser.
Uses the project's existing Pillow only to verify decoded output pixels.
"""
import copy
import base64
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/best-layout/scripts"
sys.path.insert(0, str(SCRIPTS))
from compose import asset_path, browser_page, manifest, prepare, read_json, render, verified_font
from make_typesetting_cases import font_sheet


def simple(text="山川有光", font="source-han-sans", width=600, height=240):
    return {"version": 1, "canvas": {"width": width, "height": height, "background": "#FFFFFF"},
            "copy": {"title": text}, "graphics": [],
            "blocks": [{"copy_id": "title", "font": font, "x": 20, "y": 20,
                        "width": width - 40, "height": height - 40, "size": 48, "color": "#222222"}]}


class SpecTests(unittest.TestCase):
    def test_missing_glyph_is_error_not_fallback(self):
        with self.assertRaisesRegex(ValueError, "qiji has missing glyphs"):
            prepare(simple("山川，2026", "qiji"), ROOT)

    def test_copy_cannot_be_lost_duplicated_or_added_outside_list(self):
        a = simple()
        a["copy"]["forgotten"] = "日期"
        with self.assertRaisesRegex(ValueError, "Unrendered"):
            prepare(a, ROOT)
        b = simple()
        b["blocks"].append(copy.deepcopy(b["blocks"][0]))
        with self.assertRaisesRegex(ValueError, "twice"):
            prepare(b, ROOT)
        c = simple()
        c["blocks"][0]["text"] = "制作说明"
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            prepare(c, ROOT)

    def test_reflow_does_not_change_copy(self):
        a = simple("山川，有光。")
        a["blocks"][0]["lines"] = ["山川", "有光"]
        with self.assertRaisesRegex(ValueError, "preserve every character"):
            prepare(a, ROOT)
        a["blocks"][0]["lines"] = ["山川，", "有光。"]
        prepare(a, ROOT)

    def test_bad_geometry_controls_and_bidi_rejected(self):
        for change in (lambda d: d["blocks"][0].update(size=-1),
                       lambda d: d["blocks"][0].update(x=590),
                       lambda d: d["copy"].update(title="山\t川"),
                       lambda d: d["copy"].update(title="שלום")):
            with self.subTest(change=change):
                a = simple()
                change(a)
                with self.assertRaises(ValueError):
                    prepare(a, ROOT)

    def test_duplicate_json_keys_are_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.json"
            path.write_text('{"copy":{},"copy":{}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                read_json(path)

    def test_transform_rejects_invalid_numbers_and_unknown_operations(self):
        for transform in ({"scale_x": 0}, {"scale_y": -1}, {"scale_x": True},
                          {"scale_y": float("nan")}, {"skew_x": 90}, {"rotate": 12}, None):
            with self.subTest(transform=transform), self.assertRaises(ValueError):
                a = simple()
                a["blocks"][0]["transform"] = transform
                prepare(a, ROOT)

    def test_original_weights_and_licenses(self):
        entries = manifest()
        self.assertEqual(len(entries), 10)
        self.assertNotIn("oswald-stencil", entries)
        for entry in entries.values():
            verified_font(entry)
        for font_id, expected in [("source-han-sans", 700), ("source-han-serif", 900)]:
            data = verified_font(entries[font_id])
            count = struct.unpack_from(">H", data, 4)[0]
            tables = [struct.unpack_from(">4sIII", data, 12 + i * 16) for i in range(count)]
            offset = next(t[2] for t in tables if t[0] == b"OS/2")
            self.assertEqual(struct.unpack_from(">H", data, offset + 4)[0], expected)


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.browser = browser_page(os.environ.get("BEST_LAYOUT_CHROMIUM"))
        self.page = self.browser.__enter__()

    def tearDown(self):
        self.browser.__exit__(None, None, None)

    def run_spec(self, spec, folder=ROOT):
        return render(self.page, prepare(spec, folder))

    def test_all_bundled_fonts_load_and_render_original_glyphs(self):
        data = font_sheet()
        png, report = self.run_spec(data)
        self.assertEqual(len(report["blocks"]), 2 * len(manifest()))
        with Image.open(io.BytesIO(png)) as im:
            im.load()
            self.assertEqual(im.size, (data["canvas"]["width"], data["canvas"]["height"]))

    def test_wrap_preserves_quantity_spaces_and_punctuation(self):
        a = simple("每人限带 2 件；请提前清洁。日期 2026.12.12。", width=340, height=600)
        a["blocks"][0]["size"] = 36
        _, report = self.run_spec(a)
        lines = [line["text"] for line in report["blocks"][0]["lines"]]
        self.assertEqual("".join(lines), a["copy"]["title"])
        self.assertTrue(any("2 件" in line for line in lines))
        self.assertTrue(any("2026.12.12" in line for line in lines))
        self.assertTrue(all(not line.startswith(("，", "。", "；")) for line in lines))

    def test_ellipsis_and_dash_pairs_are_not_split(self):
        for mark in ("……", "——"):
            for width in (180, 220, 240):
                with self.subTest(mark=mark, width=width):
                    a = simple(f"观察日常{mark}重新看见生活。", width=500, height=800)
                    a["blocks"][0].update(size=40, width=width)
                    _, report = self.run_spec(a)
                    lines = [line["text"] for line in report["blocks"][0]["lines"]]
                    self.assertEqual("".join(lines), a["copy"]["title"])
                    self.assertTrue(any(mark in line for line in lines), lines)
            # Repeated pairs may break between pairs, rather than becoming one
            # overlong token. No character is replaced or removed.
            a = simple(mark * 2, width=500, height=400)
            a["blocks"][0].update(size=40, width=81)
            _, report = self.run_spec(a)
            self.assertEqual([r["text"] for r in report["blocks"][0]["lines"]], [mark, mark])

    def test_numeric_prefixes_and_suffixes_preserve_exact_spaces(self):
        for token in ("20 ℃", "68 ℉", "20 °C", "50 %", "50 ‰", "30°", "+ 20", "- 20",
                      "± 3", "￥ 128", "$ -20", "128 ₫", "2 千克", "1.5 kg", "20 km/h", "２０％", "20\u00a0℃"):
            with self.subTest(token=token):
                a = simple(f"温度 {token}，继续观察。", width=500, height=800)
                a["blocks"][0].update(size=40, width=220 if token == "20 km/h" else 180)
                _, report = self.run_spec(a)
                lines = [line["text"] for line in report["blocks"][0]["lines"]]
                self.assertEqual("".join(lines), a["copy"]["title"])
                self.assertTrue(any(token in line for line in lines), lines)
                self.assertTrue(all(not line.startswith(("，", "。")) for line in lines))

    def test_protected_group_wider_than_box_fails_without_shrinking(self):
        cases = [(text, 60) for text in ("……", "——", "20 ℃", "￥ 128")]
        cases += [("10 万人", 120), ("10 万件", 120), ("Don't go.", 80),
                  ("Don’t go.", 120), ("AI\u00a0LAB", 90), ("AI\u202fLAB", 90)]
        for text, width in cases:
            with self.subTest(text=text, width=width):
                font = "wdxl" if "\u202f" in text else "source-han-sans"
                a = simple(text, font=font, width=300, height=400)
                a["blocks"][0].update(size=40, width=width)
                with self.assertRaisesRegex(Exception, "group exceeds width"):
                    self.run_spec(a)

    def test_compound_chinese_quantities_wrap_as_complete_groups(self):
        cases = [("共 10 万人参加。", "10 万人", 150),
                 ("共 10 万件展品。", "10 万件", 150),
                 ("共 10 亿人参加。", "10 亿人", 150),
                 ("共 10 万 人参加。", "10 万 人", 160),
                 ("总额 10 万元整。", "10 万元", 150),
                 ("总额 1 万亿元整。", "1 万亿元", 170),
                 ("限重 2 千克，继续。", "2 千克", 180),
                 ("路程 2 千米，继续。", "2 千米", 180)]
        for text, token, width in cases:
            with self.subTest(token=token):
                a = simple(text, width=500, height=800)
                a["blocks"][0].update(size=40, width=width)
                _, report = self.run_spec(a)
                lines = [line["text"] for line in report["blocks"][0]["lines"]]
                self.assertEqual("".join(lines), text)
                self.assertGreater(len(lines), 1)
                self.assertTrue(any(token in line for line in lines), lines)

    def test_apostrophes_inside_words_do_not_create_breaks(self):
        for token, width in (("Don't", 180), ("Don’t", 180), ("O'Reilly", 180), ("O’Reilly", 200)):
            with self.subTest(token=token):
                a = simple(f"请说 {token} go.", width=500, height=800)
                a["blocks"][0].update(size=40, width=width)
                _, report = self.run_spec(a)
                lines = [line["text"] for line in report["blocks"][0]["lines"]]
                self.assertEqual("".join(lines), a["copy"]["title"])
                self.assertGreater(len(lines), 1)
                self.assertTrue(any(token in line for line in lines), lines)
        # Quotation marks around separate words must not join those words.
        a = simple("‘Go’ ‘Go’", width=500, height=400)
        a["blocks"][0].update(size=40, width=160)
        _, report = self.run_spec(a)
        self.assertEqual([r["text"] for r in report["blocks"][0]["lines"]], ["‘Go’ ", "‘Go’"])

    def test_nonbreaking_spaces_protect_text_beyond_quantities(self):
        for token in ("AI\u00a0LAB", "AI\u202fLAB", "A\u00a0B\u00a0C", "山\u00a0川"):
            with self.subTest(token=token):
                # Source Han Sans lacks U+202F; WD-XL covers the exact copy.
                font = "wdxl" if "\u202f" in token else "source-han-sans"
                a = simple(f"请用 {token} 排版。", font=font, width=500, height=800)
                a["blocks"][0].update(size=40, width=160)
                _, report = self.run_spec(a)
                lines = [line["text"] for line in report["blocks"][0]["lines"]]
                self.assertEqual("".join(lines), a["copy"]["title"])
                self.assertGreater(len(lines), 1)
                self.assertTrue(any(token in line for line in lines), lines)
        # Ordinary spaces retain their existing wrapping behavior.
        a = simple("AI LAB", width=500, height=400)
        a["blocks"][0].update(size=40, width=90)
        _, report = self.run_spec(a)
        self.assertEqual([r["text"] for r in report["blocks"][0]["lines"]], ["AI ", "LAB"])

    def test_long_token_and_vertical_overflow_fail_without_shrinking(self):
        for a in [simple("2026.12.12", width=160), simple("文字" * 35, width=320, height=200)]:
            with self.subTest(text=a["copy"]["title"]), self.assertRaisesRegex(Exception, "exceeds"):
                self.run_spec(a)

    def test_text_overlap_is_rejected(self):
        a = simple()
        a["copy"]["other"] = "日月有序"
        a["blocks"].append({**a["blocks"][0], "copy_id": "other"})
        with self.assertRaisesRegex(Exception, "overlaps"):
            self.run_spec(a)

    def test_transform_changes_real_pixels_with_accurate_final_bounds(self):
        a = simple(width=1000, height=500)
        a["blocks"][0].update(size=80)
        original, _ = self.run_spec(a)

        def bounds(png):
            with Image.open(io.BytesIO(png)).convert("RGB") as im:
                return ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()

        before = bounds(original)
        for transform in ({"scale_x": 1.5, "scale_y": 0.75},
                          {"scale_x": 0.8, "scale_y": 1.6}, {"skew_x": 16}, {"skew_x": -16}):
            with self.subTest(transform=transform):
                a["blocks"][0]["transform"] = transform
                png, report = self.run_spec(a)
                after = bounds(png)
                self.assertNotEqual(png, original)
                self.assertEqual(report["blocks"][0]["text"], a["copy"]["title"])
                r = report["blocks"][0]["lines"][0]
                self.assertGreaterEqual(after[0], r["left"] - 2)
                self.assertGreaterEqual(after[1], r["top"] - 2)
                self.assertLessEqual(after[2], r["right"] + 2)
                self.assertLessEqual(after[3], r["bottom"] + 2)
                if "skew_x" not in transform:
                    self.assertAlmostEqual(after[2] - after[0], (before[2] - before[0]) * transform["scale_x"], delta=3)
                    self.assertAlmostEqual(after[3] - after[1], (before[3] - before[1]) * transform["scale_y"], delta=3)

    def test_transformed_alignment_wrapping_and_protected_body(self):
        a = simple("山川有光日月有序", width=480, height=480)
        a["blocks"][0].update(size=64, align="right")
        a["copy"]["body"] = "2026.10.16"
        a["blocks"].append({"copy_id": "body", "font": "source-han-sans", "x": 20, "y": 400,
                            "width": 440, "height": 70, "size": 40, "color": "#222222"})
        plain_png, plain_report = self.run_spec(a)
        a["blocks"][0]["transform"] = {"scale_x": 1.9, "scale_y": 1.05, "skew_x": -12}
        png, report = self.run_spec(a)
        lines = report["blocks"][0]["lines"]
        self.assertGreater(len(lines), len(plain_report["blocks"][0]["lines"]))
        self.assertEqual("".join(line["text"] for line in lines), a["copy"]["title"])
        for line in lines:
            self.assertGreaterEqual(line["left"], 20)
            self.assertLessEqual(line["right"], 460.01)
            # Alignment includes the font's sidebearings and advance, not just
            # black pixels; glyph ink can end a few pixels before the box edge.
            self.assertAlmostEqual(line["layout_right"], 460, delta=0.01)
        self.assertEqual(report["blocks"][1]["transform"], {"scale_x": 1, "scale_y": 1, "skew_x": 0})
        with Image.open(io.BytesIO(plain_png)) as before, Image.open(io.BytesIO(png)) as after:
            self.assertEqual(before.crop((0, 390, 480, 480)).tobytes(), after.crop((0, 390, 480, 480)).tobytes())

    def test_transformed_overflow_and_overlap_are_rejected(self):
        a = simple(width=600, height=240)
        a["blocks"][0].update(lines=["山川有光"], transform={"scale_x": 4})
        with self.assertRaisesRegex(Exception, "too wide"):
            self.run_spec(a)
        a["blocks"][0]["transform"] = {"scale_y": 5}
        with self.assertRaisesRegex(Exception, "exceeds"):
            self.run_spec(a)
        b = simple(width=800, height=300)
        b["copy"]["body"] = "日月有序"
        b["blocks"].append({**b["blocks"][0], "copy_id": "body", "y": 110, "height": 150})
        self.run_spec(b)
        b["blocks"][0]["transform"] = {"scale_y": 2.5}
        with self.assertRaisesRegex(Exception, "overlaps"):
            self.run_spec(b)

    def test_untransformed_text_matches_direct_rasterization(self):
        a = simple("字体 Aa 2026")
        a["blocks"][0].update(size=47.5, x=20.25, y=20.5)
        png, _ = self.run_spec(a)
        # Compare with direct fillText in this browser, not a platform-specific
        # PNG snapshot. Fractional positions expose hinting changes caused by
        # routing ordinary text through an unnecessary matrix transform.
        encoded = self.page.evaluate("""s => {
            const c = document.createElement('canvas');
            c.width = s.canvas.width; c.height = s.canvas.height;
            const ctx = c.getContext('2d'), b = s.blocks[0], text = s.copy.title;
            ctx.fillStyle = s.canvas.background; ctx.fillRect(0, 0, c.width, c.height);
            ctx.font = `${b.size}px "${b.font}"`;
            ctx.fontKerning = 'normal'; ctx.letterSpacing = '0px';
            ctx.textBaseline = 'alphabetic'; ctx.direction = 'ltr';
            ctx.fillStyle = b.color;
            const left = Math.min(0, -ctx.measureText(text).actualBoundingBoxLeft);
            ctx.fillText(text, b.x - left, b.y + b.size);
            return c.toDataURL('image/png').split(',')[1];
        }""", a)
        self.assertEqual(png, base64.b64decode(encoded))
        a["blocks"][0]["transform"] = {"scale_x": 1, "scale_y": 1, "skew_x": 0}
        identity, _ = self.run_spec(a)
        self.assertEqual(png, identity)

    def test_raster_and_transparent_background(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            Image.new("RGB", (16, 16), (212, 70, 30)).save(root / "source.png")
            a = simple(width=600, height=300)
            a["canvas"]["background"] = "transparent"
            a["graphics"] = [{"type": "image", "path": "source.png", "x": 430, "y": 100,
                              "width": 100, "height": 100, "fit": "contain"}]
            png, _ = self.run_spec(a, root)
            with Image.open(io.BytesIO(png)) as im:
                im.load()
                self.assertEqual(im.getpixel((580, 280))[3], 0)
                self.assertEqual(im.getpixel((480, 150)), (212, 70, 30, 255))

    def test_cli_is_cwd_independent_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            spec, output = root / "layout.json", root / "final.png"
            spec.write_text(json.dumps(simple(), ensure_ascii=False), encoding="utf-8")
            command = [sys.executable, "-X", "utf8", str(SCRIPTS / "compose.py"), str(spec), str(output)]
            if os.environ.get("BEST_LAYOUT_CHROMIUM"):
                command += ["--chromium", os.environ["BEST_LAYOUT_CHROMIUM"]]
            done = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
            original = output.read_bytes()
            again = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            spec.write_text(json.dumps(simple("2026", "qiji")), encoding="utf-8")
            failed = subprocess.run(command + ["--force"], cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
