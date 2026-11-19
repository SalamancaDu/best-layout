"""Verify the repository layout catalog and its sample evidence."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_layout_catalog as catalog


class LayoutCatalogTests(unittest.TestCase):
    def test_catalog_and_examples_are_current(self):
        pattern_ids, supports = catalog.verify_patterns()
        examples = catalog.verify_examples(pattern_ids)
        catalog.verify_readme_links()
        self.assertGreaterEqual(len(pattern_ids), 24)
        self.assertEqual(len(examples), 8)
        self.assertEqual(set(supports.values()), {"native", "manual", "reference"})

    def test_pattern_catalog_is_text_only(self):
        data = catalog.load_json(catalog.PATTERN_PATH)
        self.assertIsInstance(data, dict)
        for pattern in data["patterns"]:
            self.assertNotIn("image", pattern)
            self.assertNotIn("thumbnail", pattern)
            self.assertEqual(pattern["source_scope"], "project-method")

    def test_examples_record_review_scope(self):
        data = catalog.load_json(catalog.EXAMPLE_PATH)
        for example in data["examples"]:
            self.assertIn(example["review_status"], catalog.REVIEW_VALUES)
            self.assertIsInstance(example.get("review_scope"), str)
            self.assertTrue(example["review_scope"])

    def test_relative_paths_reject_escape(self):
        with self.assertRaises(ValueError):
            catalog.relative_file("../outside.json", "sample.config")
        with self.assertRaises(ValueError):
            catalog.relative_file("C:/outside.json", "sample.config")


if __name__ == "__main__":
    unittest.main(verbosity=2)
