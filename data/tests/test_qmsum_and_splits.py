"""Unit tests for QMSum downloader and M1 split generation."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestQMSumAndSplits(unittest.TestCase):
    def test_qmsum_stats_exists(self) -> None:
        stats_file = REPO_ROOT / "data" / "qmsum" / "STATS.md"
        self.assertTrue(stats_file.exists(), "data/qmsum/STATS.md must exist after download")
        content = stats_file.read_text(encoding="utf-8")
        self.assertIn("Total Meetings: 232", content)
        self.assertIn("train.jsonl", content)
        self.assertIn("val.jsonl", content)
        self.assertIn("test.jsonl", content)

    def test_m1_splits_exist_and_conform(self) -> None:
        splits_dir = REPO_ROOT / "data" / "splits" / "m1_v1"
        manifest_path = splits_dir / "MANIFEST.json"
        self.assertTrue(manifest_path.exists(), "MANIFEST.json must exist in data/splits/m1_v1/")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["task"], "m1_catchup")
        self.assertEqual(manifest["contract"], "CatchupExample")

        for split in ("train", "val", "test"):
            split_file = splits_dir / f"{split}.jsonl"
            self.assertTrue(split_file.exists(), f"{split}.jsonl must exist")
            self.assertGreater(split_file.stat().st_size, 0)

            # Read first example and verify schema
            with split_file.open("r", encoding="utf-8") as f:
                first_line = f.readline()
                example = json.loads(first_line)
                self.assertIn("id", example)
                self.assertIn("query", example)
                self.assertIn("context_spans", example)
                self.assertIn("reference_summary", example)
                self.assertIsInstance(example["context_spans"], list)
                self.assertGreater(len(example["context_spans"]), 0)
                self.assertIsInstance(example["query"], str)
                self.assertGreater(len(example["query"]), 0)
                self.assertIsInstance(example["reference_summary"], str)
                self.assertGreater(len(example["reference_summary"]), 0)


if __name__ == "__main__":
    unittest.main()
