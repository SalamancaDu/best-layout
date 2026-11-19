"""Cut deliberate local gaps in a verified transparent title layer; never redraw text."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys

from compose import FONT_ROOT, browser_page, color, image_data, keys, number, read_json


CUT = r"""async ({image, cuts, background}) => {
  const img = new Image(); img.src = image; await img.decode();
  const canvas = document.createElement('canvas');
  canvas.width = img.width; canvas.height = img.height;
  const ctx = canvas.getContext('2d'); ctx.drawImage(img, 0, 0);
  const before = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let originalAlpha = 0, transparent = false;
  for (let i = 3; i < before.length; i += 4) {
    originalAlpha += before[i]; if (before[i] === 0) transparent = true;
  }
  if (!transparent || originalAlpha === 0) throw new Error('Use a nonempty transparent typeset layer, not an opaque poster');
  ctx.globalCompositeOperation = 'destination-out';
  for (const polygon of cuts) {
    ctx.beginPath(); ctx.moveTo(...polygon[0]);
    for (const point of polygon.slice(1)) ctx.lineTo(...point);
    ctx.closePath(); ctx.fill();
  }
  ctx.globalCompositeOperation = 'source-over';
  const after = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let remainingAlpha = 0, changed = 0;
  for (let i = 3; i < after.length; i += 4) {
    remainingAlpha += after[i]; if (before[i] !== after[i]) changed++;
  }
  if (!changed || !remainingAlpha) throw new Error('Cuts must touch ink and retain visible text; review the polygons');
  if (background !== 'transparent') {
    ctx.globalCompositeOperation = 'destination-over'; ctx.fillStyle = background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  return {data: canvas.toDataURL('image/png').split(',')[1], width: canvas.width,
          height: canvas.height, changed_alpha_pixels: changed,
          retained_alpha_fraction: remainingAlpha / originalAlpha};
}"""


def cut_ink(spec_path, output, report=None, chromium=None, channel=None):
    spec_path = Path(spec_path).resolve(strict=True)
    spec = read_json(spec_path)
    keys(spec, {"layer", "source_report", "cuts", "background"}, {"layer", "source_report", "cuts"}, "ink cuts")
    layer = (spec_path.parent / spec["layer"]).resolve(strict=True)
    source_report = (spec_path.parent / spec["source_report"]).resolve(strict=True)
    raw = layer.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n" or len(raw) < 24:
        raise ValueError("Title layer must be the original typeset PNG")
    width, height = struct.unpack_from(">II", raw, 16)
    if not width or not height or width * height > 36_000_000:
        raise ValueError("Title layer dimensions are unsupported")
    source = read_json(source_report)
    if source.get("sha256") != hashlib.sha256(raw).hexdigest() or not source.get("blocks"):
        raise ValueError("Source report does not match the typeset PNG; render the exact copy first")
    background = spec.get("background", "transparent")
    color(background, "background", transparent=True)
    cuts = spec["cuts"]
    if not isinstance(cuts, list) or not 1 <= len(cuts) <= 32:
        raise ValueError("cuts: use 1 to 32 deliberate polygons")
    for polygon in cuts:
        if not isinstance(polygon, list) or not 3 <= len(polygon) <= 64:
            raise ValueError("Each cut needs 3 to 64 points")
        for point in polygon:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("Cut points must be [x, y]")
            number(point[0], "cut.x", 0, width)
            number(point[1], "cut.y", 0, height)
    destinations = [Path(output).resolve()] + ([Path(report).resolve()] if report else [])
    protected = {spec_path, layer, source_report}
    if len(set(destinations)) != len(destinations):
        raise ValueError("Output image and report need different paths")
    for path in destinations:
        if path.exists() or path in protected or path.is_relative_to(FONT_ROOT.resolve()):
            raise ValueError(f"Refusing to overwrite input, font or existing output: {path}")
    if destinations[0].suffix.lower() != ".png" or (report and destinations[1].suffix.lower() != ".json"):
        raise ValueError("Output must be PNG; optional report must be JSON")
    with browser_page(chromium, channel) as page:
        result = page.evaluate(CUT, {"image": image_data(layer), "cuts": cuts, "background": background})
    data = base64.b64decode(result.pop("data"), validate=True)
    if data[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack_from(">II", data, 16) != (width, height):
        raise ValueError("Ink processor returned invalid PNG dimensions")
    result.update(source_sha256=source["sha256"], sha256=hashlib.sha256(data).hexdigest(),
                  blocks=source["blocks"], cuts=cuts, background=background,
                  visual_review="pending; source copy is recorded, altered glyphs need visual inspection")
    destinations[0].parent.mkdir(parents=True, exist_ok=True)
    destinations[0].write_bytes(data)
    if report:
        destinations[1].parent.mkdir(parents=True, exist_ok=True)
        destinations[1].write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--chromium", type=Path)
    browser.add_argument("--channel", choices=("chrome", "msedge"))
    args = parser.parse_args()
    cut_ink(args.spec, args.output, args.report, args.chromium, args.channel)
    print(args.output.resolve())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"best-layout ink cuts: {exc}", file=sys.stderr)
        sys.exit(1)
