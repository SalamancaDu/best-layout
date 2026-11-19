"""Verify the text-only layout pattern catalog and repository example index."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PATTERN_PATH = ROOT / "skills/best-layout/references/layout-patterns.json"
EXAMPLE_PATH = ROOT / "examples/layout-catalog.json"
README_PATH = ROOT / "README.md"
SUPPORT_VALUES = {"native", "manual", "reference"}
REVIEW_VALUES = {"visual_checked", "technical_only"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"无法读取 JSON {path.relative_to(ROOT)}: {exc}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        fail(f"样例不是有效 PNG: {path.relative_to(ROOT)}")
    width, height = struct.unpack(">II", data[16:24])
    if width == 0 or height == 0:
        fail(f"样例 PNG 尺寸为空: {path.relative_to(ROOT)}")
    return width, height


def relative_file(relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        fail(f"{field} 必须是非空相对路径")
    path = Path(relative)
    if path.is_absolute() or "\\" in relative or ".." in path.parts:
        fail(f"{field} 不是安全的仓库相对路径: {relative}")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or not resolved.is_file():
        fail(f"{field} 不存在: {relative}")
    return resolved


def verify_patterns() -> tuple[set[str], dict[str, str]]:
    data = load_json(PATTERN_PATH)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        fail("版式目录 schema_version 必须为 1")
    categories = data.get("categories")
    patterns = data.get("patterns")
    if not isinstance(categories, list) or not categories:
        fail("版式目录缺少 categories")
    if not isinstance(patterns, list) or not patterns:
        fail("版式目录缺少 patterns")
    category_ids: set[str] = set()
    category_names: dict[str, str] = {}
    for category in categories:
        if not isinstance(category, dict):
            fail("版式 category 必须是对象")
        identifier = category.get("id")
        name = category.get("name")
        if not isinstance(identifier, str) or not identifier or identifier in category_ids:
            fail(f"版式 category ID 无效或重复: {identifier}")
        if not isinstance(name, str) or not name:
            fail(f"版式 category 缺少名称: {identifier}")
        category_ids.add(identifier)
        category_names[identifier] = name

    pattern_ids: set[str] = set()
    pattern_support: dict[str, str] = {}
    required_lists = ("use_for", "copy_density", "orientations", "typography_relations", "operations")
    for pattern in patterns:
        if not isinstance(pattern, dict):
            fail("版式 pattern 必须是对象")
        identifier = pattern.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in pattern_ids:
            fail(f"版式 pattern ID 无效或重复: {identifier}")
        if not isinstance(pattern.get("name"), str) or not pattern["name"]:
            fail(f"版式 pattern 缺少名称: {identifier}")
        category = pattern.get("category")
        if category not in category_ids:
            fail(f"版式 pattern 使用未知 category: {identifier} -> {category}")
        if not isinstance(pattern.get("subcategory"), str) or not pattern["subcategory"]:
            fail(f"版式 pattern 缺少 subcategory: {identifier}")
        support = pattern.get("support")
        if support not in SUPPORT_VALUES:
            fail(f"版式 pattern support 无效: {identifier} -> {support}")
        for field in required_lists:
            values = pattern.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
                fail(f"版式 pattern 的 {field} 无效: {identifier}")
        source_scope = pattern.get("source_scope")
        if not isinstance(source_scope, str) or not source_scope:
            fail(f"版式 pattern 缺少 source_scope: {identifier}")
        pattern_ids.add(identifier)
        pattern_support[identifier] = support

    if len(pattern_ids) < 24:
        fail(f"版式目录至少需要 24 个模式，实际为 {len(pattern_ids)}")
    return pattern_ids, pattern_support


def verify_readme_links() -> None:
    text = README_PATH.read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]*\]\(([^)]+)\)", text)
    for raw_link in links:
        target = raw_link.strip("<>")
        if target.startswith("#") or urlsplit(target).scheme:
            continue
        target_path = unquote(target.split("#", 1)[0])
        if not target_path:
            continue
        resolved = (README_PATH.parent / target_path).resolve()
        if not resolved.exists():
            fail(f"README 链接不存在: {target_path}")


def verify_examples(pattern_ids: set[str]) -> list[dict[str, object]]:
    data = load_json(EXAMPLE_PATH)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        fail("样例目录 schema_version 必须为 1")
    examples = data.get("examples")
    if not isinstance(examples, list) or not examples:
        fail("样例目录缺少 examples")
    example_ids: set[str] = set()
    verified: list[dict[str, object]] = []
    for example in examples:
        if not isinstance(example, dict):
            fail("样例记录必须是对象")
        identifier = example.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in example_ids:
            fail(f"样例 ID 无效或重复: {identifier}")
        pattern_list = example.get("pattern_ids")
        if not isinstance(pattern_list, list) or not pattern_list or not all(pattern in pattern_ids for pattern in pattern_list):
            fail(f"样例引用了未知版式模式: {identifier}")
        status = example.get("review_status")
        if status not in REVIEW_VALUES:
            fail(f"样例 review_status 无效: {identifier} -> {status}")
        image = relative_file(example.get("image"), f"{identifier}.image")
        config = relative_file(example.get("config"), f"{identifier}.config")
        report = relative_file(example.get("report"), f"{identifier}.report")
        if image.suffix.lower() != ".png":
            fail(f"样例 image 必须是 PNG: {identifier}")
        if config.suffix.lower() != ".json" or report.suffix.lower() != ".json":
            fail(f"样例 config/report 必须是 JSON: {identifier}")
        config_data = load_json(config)
        report_data = load_json(report)
        if not isinstance(config_data, dict) or not isinstance(config_data.get("copy"), dict):
            fail(f"样例配置缺少 copy: {identifier}")
        if not isinstance(report_data, dict) or not isinstance(report_data.get("blocks"), list):
            fail(f"样例报告缺少 blocks: {identifier}")
        reported: dict[str, str] = {}
        for block in report_data["blocks"]:
            if not isinstance(block, dict) or not isinstance(block.get("copy_id"), str) or not isinstance(block.get("text"), str):
                fail(f"样例报告文字块无效: {identifier}")
            copy_id = block["copy_id"]
            if copy_id in reported:
                fail(f"样例报告重复 copy_id: {identifier} -> {copy_id}")
            reported[copy_id] = block["text"]
        expected = config_data["copy"]
        if set(reported) != set(expected):
            fail(f"样例配置与报告的 copy_id 不一致: {identifier}")
        for copy_id, text in expected.items():
            if not isinstance(copy_id, str) or not isinstance(text, str) or reported[copy_id] != text:
                fail(f"样例正式文案与报告不一致: {identifier} -> {copy_id}")
        width, height = png_size(image)
        if report_data.get("width") != width or report_data.get("height") != height:
            fail(f"样例尺寸与报告不一致: {identifier}")
        digest = sha256(image)
        if report_data.get("sha256") != digest:
            fail(f"样例 PNG 与报告 SHA-256 不一致: {identifier}")
        verified.append({"id": identifier, "width": width, "height": height, "sha256": digest})
        example_ids.add(identifier)
    return verified


def main() -> None:
    pattern_ids, _ = verify_patterns()
    verify_readme_links()
    examples = verify_examples(pattern_ids)
    print(json.dumps({"patterns": len(pattern_ids), "examples": len(examples), "readme_links": "passed"}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"layout catalog: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
