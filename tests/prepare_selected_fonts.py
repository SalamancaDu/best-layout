"""Package the user's selected, unmodified fonts and their upstream licenses.

Reuses the local research archive (excluded from Git and release packages).
Only the two selected Adobe weights download if missing.
Run from any working directory; this is a maintainer helper, not skill startup.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "tests/font-specimens"
DEST = ROOT / "skills/best-layout/assets/fonts"
SELECTED = ["source-han-sans", "source-han-serif", "wenkai-gb", "unbounded",
            "xiangcui", "qiji", "smiley", "wdxl", "marker",
            "fusion-pixel"]
WEIGHTS = {"source-han-sans": ("Bold", 700), "source-han-serif": ("Heavy", 900)}
NOTES = {
    "source-han-sans": "原生 Bold；不伪造细字重。适合标题、导语及对比明确的信息。",
    "source-han-serif": "原生 Heavy；优先用于展示标题，不作为密集正文默认字体。",
    "wenkai-gb": "Regular；适合人文类正文。罕见字仍须逐字核对。",
    "unbounded": "展示标题；可按设计需要整组处理比例。",
    "xiangcui": "等粗宋体；标题与短段落按实际阅读尺寸检查。",
    "qiji": "历史刻本字形，部分码位显示异体；缺少很多标点、英文与数字。缺字报错，不自动简繁转换或替换文案。",
    "smiley": "原生倾斜形态；额外斜切时评估叠加效果。适合短标题。",
    "wdxl": "SC 简体变体；窄体展示文字。",
    "marker": "手写感展示字；长正文另选可连续阅读的字体。",
    "fusion-pixel": "12px、proportional、zh_hans 变体；原尺寸建议使用 12 的整数倍字号。",
}


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "best-layout-font-pack"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if not (SAMPLES / "manifest.json").is_file():
        raise SystemExit("Local specimen research archive is unavailable; this optional maintainer helper is not skill startup. Use the verified bundled assets/fonts/manifest.json for release packaging.")
    specimens = {f["id"]: f for f in json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))}
    previous = {}
    if (DEST / "manifest.json").exists():
        previous = {f["id"]: f for f in json.loads((DEST / "manifest.json").read_text(encoding="utf-8"))["fonts"]}
    records = []
    for font_id in SELECTED:
        src = specimens[font_id]
        folder = DEST / font_id
        folder.mkdir(parents=True, exist_ok=True)
        if font_id in WEIGHTS:
            weight, number = WEIGHTS[font_id]
            filename = Path(src["font_path"].replace("\\", "/")).name.replace("Regular", weight)
            target = folder / filename
            if font_id in previous and target.exists() and digest(target.read_bytes()) == previous[font_id]["sha256"]:
                records.append(previous[font_id])
                continue
            repo = src["repo"]
            commit = json.loads(fetch(f"https://api.github.com/repos/{repo}/commits/release"))["sha"]
            url = f"https://raw.githubusercontent.com/{repo}/{commit}/SubsetOTF/CN/{filename}"
            license_url = f"https://raw.githubusercontent.com/{repo}/{commit}/LICENSE.txt"
            font_bytes, license_bytes = fetch(url), fetch(license_url)
            target.write_bytes(font_bytes)
            (folder / "OFL.txt").write_bytes(license_bytes)
            source = {"repo": repo, "commit": commit, "font_url": url, "license_url": license_url}
            label = ("思源黑体" if font_id.endswith("sans") else "思源宋体") + " · " + weight
        else:
            font_path = SAMPLES / src["font_path"].replace("\\", "/")
            license_path = SAMPLES / src["license_path"].replace("\\", "/")
            font_bytes, license_bytes = font_path.read_bytes(), license_path.read_bytes()
            if digest(font_bytes) != src["sha256"] or digest(license_bytes) != src["license_sha256"]:
                raise ValueError(f"Specimen integrity mismatch: {font_id}")
            filename = font_path.name
            shutil.copyfile(font_path, folder / filename)
            shutil.copyfile(license_path, folder / "OFL.txt")
            source = {key: src[key] for key in ("repo", "commit", "release", "font_url", "license_url", "source", "archive_member") if key in src}
            label, number = src["label"], None
        if b"SIL OPEN FONT LICENSE" not in license_bytes.upper():
            raise ValueError(f"Missing OFL text for {font_id}")
        record = {"id": font_id, "label": label, "path": f"{font_id}/{filename}",
                  "license": f"{font_id}/OFL.txt", "license_id": "OFL-1.1",
                  "bytes": len(font_bytes), "sha256": digest(font_bytes),
                  "license_sha256": digest(license_bytes), "source": source,
                  "notes": NOTES[font_id]}
        if number:
            record["weight"] = number
        records.append(record)
        print(f"{font_id}: {filename} ({len(font_bytes):,} bytes)", flush=True)
    (DEST / "manifest.json").write_text(json.dumps({"version": 1, "fonts": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {len(records)} fonts; {sum(f['bytes'] for f in records) / 1048576:.1f} MiB")


if __name__ == "__main__":
    main()
