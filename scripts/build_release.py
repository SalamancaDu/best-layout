"""Build a local, self-contained skill ZIP; never upload, install or publish.

Only reviewed runtime files and the v0.1 font allowlist enter the archive.
Uses the Python standard library; no network or additional build dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/best-layout"
APPROVED_FONT_IDS = frozenset({"source-han-sans", "source-han-serif", "wenkai-gb", "unbounded",
                             "xiangcui", "qiji", "smiley", "wdxl", "marker", "fusion-pixel"})
RUNTIME_FILES = (
    "SKILL.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "agents/openai.yaml",
    "references/composition.md", "references/typography.md", "references/image-production.md",
    "references/local-typesetting.md", "references/sources.md", "scripts/compose.py",
    "scripts/render_canvas.js", "scripts/font_coverage.py", "scripts/requirements.txt",
    "assets/fonts/manifest.json", "assets/examples/poster.json",
)


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def checked_path(relative):
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or "\\" in relative:
        raise ValueError(f"Invalid release path: {relative}")
    path = SKILL / relative
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(SKILL.resolve()) or path.is_symlink() or not path.is_file():
        raise ValueError(f"Release input is not a regular skill file: {relative}")
    return path


def check_links(files):
    """Check relative Markdown file/directory links against the actual bundle."""
    included = {p.resolve() for p in files.values()}
    for name, path in files.items():
        if path.suffix != ".md":
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip("<>")
            if target.startswith("#") or urlsplit(target).scheme:
                continue
            relative = unquote(target.split("#", 1)[0])
            dest = (path.parent / relative).resolve()
            if dest not in included and not any(p.is_relative_to(dest) for p in included):
                raise ValueError(f"Unbundled Markdown reference in {name}: {target}")


def release_files():
    files = {name: checked_path(name) for name in RUNTIME_FILES}
    if (ROOT / "LICENSE").read_bytes() != files["LICENSE"].read_bytes():
        raise ValueError("Project and standalone skill licenses differ")
    frontmatter = files["SKILL.md"].read_text(encoding="utf-8").split("---", 2)[1]
    match = re.search(r'^  version: "(\d+\.\d+\.\d+)"$', frontmatter, re.M)
    if not match:
        raise ValueError("SKILL.md needs an explicit metadata.version")
    fonts = json.loads(files["assets/fonts/manifest.json"].read_text(encoding="utf-8"))["fonts"]
    if len(fonts) != len(APPROVED_FONT_IDS) or {f["id"] for f in fonts} != APPROVED_FONT_IDS:
        raise ValueError("Font selection differs from the reviewed v0.1 release allowlist")
    for font in fonts:
        if font["license_id"] != "OFL-1.1":
            raise ValueError(f"Unreviewed font license: {font['id']}")
        for field, hash_field in (("path", "sha256"), ("license", "license_sha256")):
            relative = "assets/fonts/" + font[field]
            path = checked_path(relative)
            if sha256(path) != font[hash_field]:
                raise ValueError(f"Release integrity mismatch: {relative}")
            files[relative] = path
        if files["assets/fonts/" + font["path"]].stat().st_size != font["bytes"]:
            raise ValueError(f"Font byte count changed: {font['id']}")
        if b"SIL OPEN FONT LICENSE" not in files["assets/fonts/" + font["license"]].read_bytes().upper():
            raise ValueError(f"Missing OFL text: {font['id']}")
        if font.get("notice"):
            relative = "assets/fonts/" + font["notice"]
            files[relative] = checked_path(relative)
    font_files = {p.resolve() for p in (SKILL / "assets/fonts").rglob("*") if p.is_file()}
    expected = {p.resolve() for name, p in files.items() if name.startswith("assets/fonts/")}
    if font_files != expected:
        raise ValueError("Font directory contains unlisted files; review before packaging")
    check_links(files)
    return match[1], files


def build(output_dir, force=False):
    version, files = release_files()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"best-layout-v{version}.zip"
    checksum = archive.with_suffix(".zip.sha256")
    temporary = archive.with_suffix(".zip.tmp")
    if not force and (archive.exists() or checksum.exists()):
        raise FileExistsError(f"Release already exists: {archive}; use --force to rebuild")
    # A fixed timestamp and stable order avoid embedding machine paths or mtimes.
    # Write a complete temporary archive before replacing the previous bundle.
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo("best-layout/" + name, date_time=(2026, 10, 16, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(temporary) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("Release ZIP failed its CRC check")
    temporary.replace(archive)
    checksum.write_text(f"{sha256(archive)}  {archive.name}\n", encoding="utf-8")
    return archive, checksum, len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    archive, checksum, count = build(args.output_dir, args.force)
    print(json.dumps({"archive": str(archive), "sha256_file": str(checksum), "files": count,
                      "fonts": len(APPROVED_FONT_IDS), "bytes": archive.stat().st_size,
                      "published": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
