"""Inspect PNG files and capture their browser display at a target width.

Uses the existing local Pillow, Playwright and Chromium installations. Does not
install dependencies, modify source images, or decide whether a design passes.
"""

import argparse
import json
import math
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chromium", type=Path)
    args = parser.parse_args()
    if args.width <= 0:
        parser.error("--width must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        launch_options = {"headless": True}
        if args.chromium:
            launch_options["executable_path"] = str(args.chromium.resolve())
        browser = playwright.chromium.launch(**launch_options)
        try:
            for image_path in args.images:
                image_path = image_path.resolve(strict=True)
                with Image.open(image_path) as source:
                    source.load()
                    if source.format != "PNG":
                        raise ValueError(f"Expected PNG: {image_path}")
                    source_width, source_height = source.size
                    mode = source.mode
                height = math.ceil(source_height * args.width / source_width)
                screenshot_path = (
                    args.output_dir / f"{image_path.stem}-{args.width}.png"
                ).resolve()
                if screenshot_path == image_path:
                    raise ValueError(f"Screenshot would replace source: {image_path}")
                page = browser.new_page(
                    viewport={"width": args.width, "height": height},
                    device_scale_factor=1,
                )
                try:
                    page.goto(image_path.as_uri(), wait_until="load")
                    picture = page.locator("img")
                    picture.evaluate(
                        """(img, width) => {
                            document.documentElement.style.cssText =
                                'margin:0;padding:0;overflow:hidden';
                            document.body.style.cssText =
                                'margin:0;padding:0;background:white';
                            img.style.cssText =
                                `display:block;width:${width}px;height:auto;` +
                                'max-width:none;max-height:none;margin:0;padding:0';
                        }""",
                        args.width,
                    )
                    page.screenshot(path=str(screenshot_path), full_page=True)
                    print(json.dumps({
                        "source": str(image_path),
                        "pixels": [source_width, source_height],
                        "mode": mode,
                        "display_width": args.width,
                        "screenshot": str(screenshot_path),
                        "visual_acceptance": "requires actual image inspection",
                    }, ensure_ascii=False))
                finally:
                    page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
