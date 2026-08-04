import unittest


from shepherd_ai.multiuav_resource_schedule import (
    RESOURCE_REPETITIONS,
    build_condition_schedule,
    build_resource_run_configs,
    select_resource_source_tasks,
)


class ResourceSubsetTests(unittest.TestCase):
    def _rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for scenario in ("search", "patrol", "target"):
            for difficulty in ("easy", "moderate", "hard", "intermediate", "extreme"):
                for index in range(4):
                    rows.append(
                        {
                            "task_id": f"{scenario}-{difficulty}-{index}",
                            "session_id": f"session-{scenario}-{difficulty}",
                            "scenario": scenario,
                            "difficulty": difficulty,
                            "split": "test",
                            "eligible": True,
                        }
                    )
        return rows

    def test_selects_two_tasks_from_each_test_stratum_deterministically(self) -> None:
        rows = self._rows()

        first = select_resource_source_tasks(rows)
        second = select_resource_source_tasks(list(reversed(rows)))

        self.assertEqual(first, second)
        self.assertEqual(len(first), 30)
        counts: dict[tuple[str, str], int] = {}
        for row in first:
            key = (str(row["scenario"]), str(row["difficulty"]))
            counts[key] = counts.get(key, 0) + 1
            self.assertEqual(row["split"], "test")
            self.assertTrue(row["eligible"])
            self.assertEqual(len(str(row["selection_rank_sha256"])), 64)
        self.assertEqual(set(counts.values()), {2})

    def test_rejects_an_incomplete_stratum(self) -> None:
        rows = self._rows()
        rows = [row for row in rows if row["task_id"] != "search-easy-0"]
        rows = [row for row in rows if row["task_id"] != "search-easy-1"]
        rows = [row for row in rows if row["task_id"] != "search-easy-2"]

        with self.assertRaisesRegex(ValueError, "fewer than 2"):
            select_resource_source_tasks(rows)

    def test_can_restrict_selection_to_template_supported_tasks(self) -> None:
        rows = self._rows()
        supported = {
            str(row["task_id"])
            for row in rows
            if not str(row["task_id"]).endswith("-0")
        }

        selected = select_resource_source_tasks(
            rows,
            supported_task_ids=supported,
        )

        self.assertTrue({str(row["task_id"]) for row in selected} <= supported)


class ResourceConditionScheduleTests(unittest.TestCase):
    def test_registers_every_model_method_repetition_once(self) -> None:
        schedule = build_condition_schedule(
            model_ids=("model-a", "model-b"),
            method_ids=("M1", "M2", "M3", "M4"),
        )

        self.assertEqual(len(schedule), 24)
        keys = {
            (row["model_id"], row["method_id"], row["repetition"])
            for row in schedule
        }
        self.assertEqual(len(keys), 24)
        self.assertEqual(
            {row["repetition"] for row in schedule},
            set(RESOURCE_REPETITIONS),
        )
        for repetition in RESOURCE_REPETITIONS:
            orders = [
                row["condition_order"]
                for row in schedule
                if row["repetition"] == repetition
            ]
            self.assertEqual(sorted(orders), list(range(1, 9)))

    def test_schedule_is_independent_of_input_order(self) -> None:
        first = build_condition_schedule(
            model_ids=("model-a", "model-b"),
            method_ids=("M1", "M2"),
        )
        second = build_condition_schedule(
            model_ids=("model-b", "model-a"),
            method_ids=("M2", "M1"),
        )

        self.assertEqual(first, second)

    def test_builds_24_schedule_bound_resource_run_configs(self) -> None:
        schedule = build_condition_schedule(
            model_ids=(
                "Qwen/Qwen2.5-3B-Instruct",
                "Qwen/Qwen2.5-7B-Instruct",
            ),
            method_ids=(
                "M1_monolithic",
                "M2_post_plan_deterministic",
                "M3_stage_wise",
                "M4_post_plan_compute_matched",
            ),
        )

        configs = build_resource_run_configs(
            schedule,
            study_id="multiuav_validation_placement_v1",
            dataset_status="approved_evaluation_data",
            dataset_sha256="a" * 64,
            code_commit="b" * 40,
            hardware_protocol_sha256="c" * 64,
            resource_schedule_sha256="d" * 64,
            decoding={
                "do_sample": False,
                "num_beams": 1,
                "max_new_tokens": 512,
            },
        )

        self.assertEqual(len(configs), 24)
        self.assertEqual(len({config.config_hash for config in configs}), 24)
        for config in configs:
            config.validate()
            self.assertEqual(config.run_kind, "resource")
            self.assertEqual(len(config.methods), 1)
            self.assertIn(config.resource_condition_order, range(1, 9))
            self.assertEqual(config.resource_schedule_sha256, "d" * 64)

    def test_refuses_run_configs_for_unapproved_or_candidate_data(self) -> None:
        schedule = build_condition_schedule(
            model_ids=("Qwen/Qwen2.5-3B-Instruct",),
            method_ids=("M1_monolithic",),
        )

        with self.assertRaisesRegex(ValueError, "approved evaluation data"):
            build_resource_run_configs(
                schedule,
                study_id="multiuav_validation_placement_v1",
                dataset_status="candidate_source_subset_only",
                dataset_sha256="a" * 64,
                code_commit="b" * 40,
                hardware_protocol_sha256="c" * 64,
                resource_schedule_sha256="d" * 64,
                decoding={
                    "do_sample": False,
                    "num_beams": 1,
                    "max_new_tokens": 512,
                },
            )


if __name__ == "__main__":
    unittest.main()
