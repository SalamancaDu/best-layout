"""Render font candidates in an existing layout for internal visual comparison.

Only the selected blocks' font IDs change. No fitting, ranking or artwork labels.
Uses the same verified fonts and raster compositor as compose.py.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys

from compose import FONT_ROOT, browser_page, manifest, prepare, read_json, render


def candidates(spec, copy_ids, fonts):
    """Validate selections and yield independent layouts, without editing input."""
    if not copy_ids or len(copy_ids) != len(set(copy_ids)):
        raise ValueError("Choose distinct copy IDs for the title blocks")
    if not fonts or len(fonts) != len(set(fonts)):
        raise ValueError("Choose distinct bundled font IDs")
    blocks = spec.get("blocks", [])
    available = {b.get("copy_id") for b in blocks if isinstance(b, dict)}
    if set(copy_ids) - available:
        raise ValueError(f"Unknown title copy IDs: {sorted(set(copy_ids) - available)}")
    known = manifest()
    if any(f not in known or not re.fullmatch(r"[a-z0-9-]+", f) for f in fonts):
        raise ValueError("Unknown bundled font ID; use compose.py --list-fonts")
    result = []
    for font in fonts:
        variant = copy.deepcopy(spec)
        for block in variant["blocks"]:
            if block["copy_id"] in copy_ids:
                block["font"] = font
        result.append((font, variant))
    return result


def proof(spec_path, output_dir, copy_ids, fonts, chromium=None, channel=None):
    spec_path = Path(spec_path).resolve(strict=True)
    output_dir = Path(output_dir).resolve()
    if output_dir.is_relative_to(FONT_ROOT.resolve()):
        raise ValueError("Proof output must not be inside bundled fonts")
    if output_dir.exists():
        raise FileExistsError(f"Use a new proof directory; refusing to overwrite: {output_dir}")
    variants = candidates(read_json(spec_path), copy_ids, fonts)
    # Validate every variant before producing any output. Nothing is auto-fitted.
    for _, spec in variants:
        prepare(spec, spec_path.parent)
    output_dir.mkdir(parents=True)
    reports = []
    with browser_page(chromium, channel) as page:
        for font, spec in variants:
            try:
                data, report = render(page, prepare(spec, spec_path.parent))
            except Exception as exc:
                raise RuntimeError(f"Font proof failed for {font}: {exc}. "
                                   "Reflow deliberately; earlier PNGs may exist but no complete index was written") from exc
            image = output_dir / f"{font}.png"
            image.write_bytes(data)
            reports.append({"font": font, "image": image.name, "render": report})
    index = {"purpose": "internal font comparison; not a final artwork selection",
             "copy_ids": copy_ids, "candidates": reports,
             "visual_review": "pending; inspect full layout and target viewing size"}
    (output_dir / "proofs.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--copy-id", nargs="+", required=True, help="Existing title block IDs")
    parser.add_argument("--fonts", nargs="+", required=True, help="Bundled font IDs to compare")
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--chromium", type=Path)
    browser.add_argument("--channel", choices=("chrome", "msedge"))
    args = parser.parse_args()
    print(proof(args.spec, args.output_dir, args.copy_id, args.fonts, args.chromium, args.channel))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"best-layout font proof: {exc}", file=sys.stderr)
        sys.exit(1)
