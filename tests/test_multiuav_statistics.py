import unittest


from shepherd_ai.multiuav_statistics import paired_cluster_bootstrap


def _rows(
    differences: dict[str, float],
    *,
    variants: int = 5,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for cluster_id, difference in differences.items():
        for variant_index in range(variants):
            variant = f"v{variant_index}"
            rows.extend(
                [
                    {
                        "cluster_id": cluster_id,
                        "case_variant": variant,
                        "method_id": "M1",
                        "metric_value": 0.0,
                    },
                    {
                        "cluster_id": cluster_id,
                        "case_variant": variant,
                        "method_id": "M3",
                        "metric_value": difference,
                    },
                ]
            )
    return rows


class PairedClusterBootstrapTests(unittest.TestCase):
    def test_uses_cluster_means_and_returns_reproducible_interval(self) -> None:
        rows = _rows({"cluster-a": 1.0, "cluster-b": -1.0, "cluster-c": 0.5})

        first = paired_cluster_bootstrap(
            rows,
            method_a="M3",
            method_b="M1",
            draws=2_000,
            seed="test-seed",
        )
        second = paired_cluster_bootstrap(
            list(reversed(rows)),
            method_a="M3",
            method_b="M1",
            draws=2_000,
            seed="test-seed",
        )

        self.assertEqual(first, second)
        analysis = first["analysis"]
        self.assertAlmostEqual(analysis["point_estimate"], 1.0 / 6.0)
        self.assertEqual(analysis["cluster_count"], 3)
        self.assertEqual(analysis["cases_per_method_per_cluster"], 5)
        self.assertEqual(analysis["resampling_unit"], "source_task_cluster")
        self.assertEqual(len(first["raw_bootstrap_draws"]), 2_000)
        self.assertLessEqual(
            analysis["confidence_interval"]["lower"],
            analysis["point_estimate"],
        )
        self.assertGreaterEqual(
            analysis["confidence_interval"]["upper"],
            analysis["point_estimate"],
        )

    def test_rejects_incomplete_five_case_cluster(self) -> None:
        rows = _rows({"cluster-a": 1.0})
        rows.pop()

        with self.assertRaisesRegex(ValueError, "complete paired variant set"):
            paired_cluster_bootstrap(
                rows,
                method_a="M3",
                method_b="M1",
                draws=100,
            )

    def test_rejects_duplicate_method_variant_row(self) -> None:
        rows = _rows({"cluster-a": 1.0})
        rows.append(dict(rows[0]))

        with self.assertRaisesRegex(ValueError, "duplicate scored row"):
            paired_cluster_bootstrap(
                rows,
                method_a="M3",
                method_b="M1",
                draws=100,
            )

    def test_rejects_nonfinite_metric(self) -> None:
        rows = _rows({"cluster-a": 1.0})
        rows[0]["metric_value"] = float("nan")

        with self.assertRaisesRegex(ValueError, "finite numeric"):
            paired_cluster_bootstrap(
                rows,
                method_a="M3",
                method_b="M1",
                draws=100,
            )


if __name__ == "__main__":
    unittest.main()
