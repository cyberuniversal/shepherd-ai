import sys
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_vision_evaluation import (  # noqa: E402
    class_iou_summary,
    select_mission_records,
    select_mission_records_lazily,
)


class Week8VisionEvaluationTests(unittest.TestCase):
    def test_selection_is_disjoint_positive_and_excludes_development_ids(self) -> None:
        records = [
            {"id": "dev", "split": "validation", "positive_classes": ["water"]},
            {"id": "water-a", "split": "validation", "positive_classes": ["water"]},
            {"id": "crop-a", "split": "validation", "positive_classes": ["drydown"]},
            {"id": "crop-b", "split": "validation", "positive_classes": ["endrow"]},
            {"id": "train", "split": "train", "positive_classes": ["waterway"]},
        ]

        selected = select_mission_records(
            records,
            excluded_ids={"dev"},
            max_per_clause=2,
            seed=29,
        )

        irrigation_ids = {row["id"] for row in selected["clause_002"]}
        crop_ids = {row["id"] for row in selected["clause_001"]}
        self.assertEqual(irrigation_ids, {"water-a"})
        self.assertEqual(crop_ids, {"crop-a", "crop-b"})
        self.assertFalse(irrigation_ids.intersection(crop_ids))
        self.assertNotIn("dev", irrigation_ids)

    def test_selection_rejects_missing_positive_clause_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "clause_002"):
            select_mission_records(
                [{"id": "crop", "split": "validation", "positive_classes": ["drydown"]}],
                excluded_ids=set(),
                max_per_clause=1,
                seed=29,
            )

    def test_lazy_selection_matches_eager_selection_and_stops_early(self) -> None:
        records = [
            {"id": "irrelevant", "split": "validation", "positive_classes": []},
            {"id": "water", "split": "validation", "positive_classes": ["water"]},
            {"id": "crop", "split": "validation", "positive_classes": ["drydown"]},
            {"id": "later-2", "split": "validation", "positive_classes": ["waterway"]},
        ]
        eager = select_mission_records(
            records,
            excluded_ids=set(),
            max_per_clause=1,
            seed=29,
        )
        reads: list[str] = []

        def positives(row: dict[str, object]) -> list[str]:
            reads.append(str(row["id"]))
            return list(row["positive_classes"])  # type: ignore[arg-type]

        lazy = select_mission_records_lazily(
            records,
            excluded_ids=set(),
            max_per_clause=1,
            seed=29,
            positive_classes_for=positives,
        )

        self.assertEqual(
            {clause: [row["id"] for row in rows] for clause, rows in lazy.items()},
            {clause: [row["id"] for row in rows] for clause, rows in eager.items()},
        )
        self.assertLess(len(reads), len(records))

    def test_class_iou_summary_uses_declared_classes_only(self) -> None:
        confusion = np.array([[8, 1, 0], [1, 4, 0], [0, 1, 5]])

        result = class_iou_summary(
            confusion,
            class_names=("background", "water", "waterway"),
            selected_classes=("water", "waterway"),
        )

        self.assertAlmostEqual(result["per_class_iou"]["water"], 4 / 7)
        self.assertAlmostEqual(result["per_class_iou"]["waterway"], 5 / 6)
        self.assertEqual(result["evaluated_class_count"], 2)


if __name__ == "__main__":
    unittest.main()
