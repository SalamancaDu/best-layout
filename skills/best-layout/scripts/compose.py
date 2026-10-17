"""Compose exact copy with bundled fonts into PNG. No network or font fallback.

Python 3.10+ and the project's existing Playwright runtime are required.
The browser stays internal; no HTML or SVG file is generated.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import unicodedata

from font_coverage import FontCoverage

SKILL = Path(__file__).resolve().parents[1]
FONT_ROOT = SKILL / "assets/fonts"


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)


def keys(value, allowed, required, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected an object")
    missing, extra = set(required) - value.keys(), value.keys() - set(allowed)
    if missing or extra:
        raise ValueError(f"{label}: missing fields {sorted(missing)}, unsupported fields {sorted(extra)}")


def number(value, label, minimum=0, maximum=8192):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{label}: expected a finite number in [{minimum}, {maximum}]")
    return value


def color(value, label, transparent=False):
    if transparent and value == "transparent":
        return value
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ValueError(f"{label}: use an opaque #RRGGBB color")
    return value


def box(value, canvas, label):
    for name in ("x", "y"):
        number(value[name], f"{label}.{name}")
    for name in ("width", "height"):
        number(value[name], f"{label}.{name}", 1)
    if value["x"] + value["width"] > canvas["width"] or value["y"] + value["height"] > canvas["height"]:
        raise ValueError(f"{label}: box extends beyond the canvas")


def asset_path(relative):
    path = (FONT_ROOT / relative).resolve(strict=True)
    if not path.is_relative_to(FONT_ROOT.resolve()):
        raise ValueError(f"Font asset escapes its directory: {relative}")
    return path


def manifest():
    data = read_json(FONT_ROOT / "manifest.json")
    entries = {f["id"]: f for f in data["fonts"]}
    if len(entries) != len(data["fonts"]):
        raise ValueError("Duplicate font IDs in manifest")
    return entries


def verified_font(entry):
    data = asset_path(entry["path"]).read_bytes()
    license_bytes = asset_path(entry["license"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"Font checksum mismatch: {entry['id']}; restore the original file")
    if hashlib.sha256(license_bytes).hexdigest() != entry["license_sha256"]:
        raise ValueError(f"License checksum mismatch: {entry['id']}; restore the original license")
    if entry.get("notice"):
        asset_path(entry["notice"])
    return data


def image_data(path):
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError(f"Expected a local PNG/JPEG/WebP raster, not SVG/HTML: {path}")
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def prepare(spec, base_dir):
    keys(spec, {"version", "canvas", "copy", "blocks", "graphics"}, {"version", "canvas", "copy", "blocks"}, "spec")
    if type(spec["version"]) is not int or spec["version"] != 1:
        raise ValueError("Unsupported spec version")
    canvas = dict(spec["canvas"])
    keys(canvas, {"width", "height", "background"}, {"width", "height", "background"}, "canvas")
    for name in ("width", "height"):
        if type(canvas[name]) is not int:
            raise ValueError(f"canvas.{name}: expected integer pixels")
        number(canvas[name], "canvas." + name, 1)
    if canvas["width"] * canvas["height"] > 36_000_000:
        raise ValueError("Canvas exceeds 36 million pixels")
    color(canvas["background"], "canvas.background", transparent=True)
    copy = spec["copy"]
    if not isinstance(copy, dict) or not copy:
        raise ValueError("copy: expected a nonempty map of IDs to exact approved text")
    for copy_id, text in copy.items():
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", copy_id):
            raise ValueError(f"Invalid copy ID: {copy_id}")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{copy_id}: expected nonempty text")
        unsupported = [c for c in text if c != "\n" and (unicodedata.category(c).startswith("C") or c in "\ufe0e\ufe0f" or 0xE0100 <= ord(c) <= 0xE01EF)]
        if unsupported:
            raise ValueError(f"{copy_id}: unsupported control/variation characters; do not strip them silently: {unsupported!r}")
        if any(unicodedata.bidirectional(c) in ("R", "AL", "AN") for c in text):
            raise ValueError(f"{copy_id}: bidirectional text is not supported by this compositor")
    if not isinstance(spec["blocks"], list):
        raise ValueError("blocks: expected a list")
    entries, used, blocks, referenced = manifest(), {}, [], []
    for index, original in enumerate(spec["blocks"]):
        label = f"blocks[{index}]"
        keys(original, {"copy_id", "font", "x", "y", "width", "height", "size", "line_height", "letter_spacing", "color", "align", "lines", "transform"},
             {"copy_id", "font", "x", "y", "width", "height", "size", "color"}, label)
        b = dict(original)
        copy_id = b["copy_id"]
        if not isinstance(copy_id, str) or copy_id not in copy:
            raise ValueError(f"{label}: unknown copy_id {copy_id!r}")
        if copy_id in referenced:
            raise ValueError(f"{label}: copy item rendered twice: {copy_id}")
        referenced.append(copy_id)
        box(b, canvas, label)
        number(b["size"], label + ".size", 1, 2048)
        b.setdefault("line_height", b["size"] * 1.4)
        b.setdefault("letter_spacing", 0)
        b.setdefault("align", "left")
        transform = b.get("transform", {})
        keys(transform, {"scale_x", "scale_y", "skew_x"}, set(), label + ".transform")
        transform = {"scale_x": 1, "scale_y": 1, "skew_x": 0, **transform}
        for axis in ("scale_x", "scale_y"):
            number(transform[axis], label + ".transform." + axis, 0.05, 20)
        number(transform["skew_x"], label + ".transform.skew_x", -85, 85)
        b["transform"] = transform
        number(b["line_height"], label + ".line_height", b["size"], 4096)
        number(b["letter_spacing"], label + ".letter_spacing", -b["size"] * 0.1, b["size"])
        color(b["color"], label + ".color")
        if b["align"] not in ("left", "center", "right"):
            raise ValueError(f"{label}: unsupported alignment")
        if "lines" in b:
            if not isinstance(b["lines"], list) or not b["lines"] or any(not isinstance(line, str) or "\n" in line for line in b["lines"]):
                raise ValueError(f"{label}: lines must be a nonempty list of strings without newlines")
            if "\n" in copy[copy_id] or "".join(b["lines"]) != copy[copy_id]:
                raise ValueError(f"{copy_id}: explicit lines must preserve every character and space; use automatic wrapping for copy with newlines")
        font_id = b["font"]
        if not isinstance(font_id, str) or font_id not in entries:
            raise ValueError(f"{label}: unknown bundled font {font_id!r}")
        if font_id not in used:
            data = verified_font(entries[font_id])
            used[font_id] = {"data": data, "coverage": FontCoverage(data)}
        missing = used[font_id]["coverage"].missing(copy[copy_id])
        if missing:
            detail = ", ".join(f"{c!r} U+{ord(c):04X}" for c in missing)
            raise ValueError(f"{copy_id}: {font_id} has missing glyphs: {detail}; choose a covering font for this block; copy has not been changed")
        blocks.append(b)
    if set(referenced) != copy.keys():
        raise ValueError(f"Unrendered copy IDs: {sorted(copy.keys() - set(referenced))}")
    graphics, images = [], {}
    if not isinstance(spec.get("graphics", []), list):
        raise ValueError("graphics: expected a list")
    for index, original in enumerate(spec.get("graphics", [])):
        label = f"graphics[{index}]"
        if not isinstance(original, dict) or original.get("type") not in ("rect", "ellipse", "image"):
            raise ValueError(f"{label}: use rect, ellipse or image")
        g = dict(original)
        common = {"type", "x", "y", "width", "height"}
        if g["type"] == "image":
            keys(g, common | {"path", "fit", "position"}, common | {"path"}, label)
            if not isinstance(g["path"], str):
                raise ValueError(f"{label}: path must name a local raster")
            g.setdefault("fit", "contain")
            g.setdefault("position", [0.5, 0.5])
            if g["fit"] not in ("cover", "contain") or not isinstance(g["position"], list) or len(g["position"]) != 2:
                raise ValueError(f"{label}: invalid fit or position")
            for value in g["position"]:
                number(value, label + ".position", 0, 1)
            path = (base_dir / g["path"]).resolve(strict=True)
            images[g["path"]] = image_data(path)
        else:
            keys(g, common | {"color"}, common | {"color"}, label)
            color(g["color"], label + ".color")
        box(g, canvas, label)
        graphics.append(g)
    return {"spec": {"canvas": canvas, "copy": copy, "blocks": blocks, "graphics": graphics},
            "fonts": [{"id": font_id, "data": base64.b64encode(item["data"]).decode("ascii")} for font_id, item in used.items()],
            "images": images}


@contextmanager
def browser_page(chromium=None, channel=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Missing Python Playwright. See references/local-typesetting.md; nothing was installed automatically") from exc
    with sync_playwright() as p:
        options = {"headless": True}
        if chromium:
            options["executable_path"] = str(Path(chromium).resolve(strict=True))
        if channel:
            options["channel"] = channel
        try:
            browser = p.chromium.launch(**options)
        except Exception as exc:
            raise RuntimeError("Cannot start Chromium. Use --chromium PATH or --channel chrome/msedge for an existing browser; no automatic download. " + str(exc)) from exc
        try:
            page = browser.new_page()
            page.route("**/*", lambda route: route.abort())
            yield page
        finally:
            browser.close()


def render(page, payload):
    # Sending a whole CJK family bundle in one CDP message can close Chromium.
    # Transfer one original face at a time and never retain prior jobs' faces.
    page.evaluate("() => document.fonts.clear()")
    for font in payload["fonts"]:
        page.evaluate("""async ({id, data}) => {
            const raw = atob(data);
            const bytes = new Uint8Array(raw.length);
            for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
            const face = new FontFace(id, bytes.buffer);
            try { await face.load(); }
            catch (e) { throw new Error(`Font load failed for ${id}: ${e.message}`); }
            document.fonts.add(face);
        }""", font)
    result = page.evaluate((SKILL / "scripts/render_canvas.js").read_text(encoding="utf-8"),
                           {"spec": payload["spec"], "images": payload["images"]})
    data = base64.b64decode(result.pop("data"), validate=True)
    if data[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack_from(">II", data, 16) != (result["width"], result["height"]):
        raise ValueError("Renderer returned an invalid PNG or dimensions")
    result["sha256"] = hashlib.sha256(data).hexdigest()
    result["visual_review"] = "pending; inspect actual PNG at original and viewing sizes"
    return data, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--chromium", type=Path)
    browser.add_argument("--channel", choices=("chrome", "msedge"))
    parser.add_argument("--check-env", action="store_true")
    parser.add_argument("--list-fonts", action="store_true")
    parser.add_argument("--report", type=Path, help="Optional internal JSON checks, not artwork")
    parser.add_argument("--force", action="store_true", help="Replace an existing output intentionally")
    args = parser.parse_args()
    if args.list_fonts:
        print(json.dumps([{k: f[k] for k in ("id", "label", "notes")} for f in manifest().values()], ensure_ascii=False, indent=2))
        return
    if args.check_env:
        with browser_page(args.chromium, args.channel) as page:
            available = page.evaluate("() => 'letterSpacing' in document.createElement('canvas').getContext('2d')")
            if not available:
                raise RuntimeError("Chromium lacks native Canvas letterSpacing")
            print("Ready: Python, Playwright, Chromium Canvas; fonts will load only when selected")
        return
    if args.spec is None or args.output is None:
        parser.error("Provide SPEC.json OUTPUT.png or use --check-env / --list-fonts")
    spec_path, output = args.spec.resolve(strict=True), args.output.resolve()
    spec = read_json(spec_path)
    protected = {spec_path}
    for g in spec.get("graphics", []):
        if isinstance(g, dict) and g.get("type") == "image" and isinstance(g.get("path"), str):
            protected.add((spec_path.parent / g["path"]).resolve())
    destinations = [output] + ([args.report.resolve()] if args.report else [])
    for path in destinations:
        if path in protected or path.is_relative_to(FONT_ROOT.resolve()) or (path.exists() and not args.force):
            raise ValueError(f"Refusing to overwrite input/font/existing output: {path}")
    if output.suffix.lower() != ".png" or (args.report and args.report.suffix.lower() != ".json"):
        raise ValueError("Output must be .png; optional report must be .json")
    payload = prepare(spec, spec_path.parent)
    with browser_page(args.chromium, args.channel) as page:
        data, report = render(page, payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)  # All glyph, copy and geometry checks passed before writing.
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"best-layout: {exc}", file=sys.stderr)
        sys.exit(1)
