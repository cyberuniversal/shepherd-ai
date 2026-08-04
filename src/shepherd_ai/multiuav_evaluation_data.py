"""Approval manifest and case loading for the locked MultiUAV evaluation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from shepherd_ai.multiuav_checkpoints import RunConfig
from shepherd_ai.multiuav_experiment import EvaluationCase
from shepherd_ai.multiuav_interventions import VARIANTS, materialize_case_context
from shepherd_ai.multiuav_methods import METHOD_SPECS
from shepherd_ai.multiuav_model_revisions import REGISTERED_MODEL_REVISIONS
from shepherd_ai.multiuav_prompts import PROMPT_CONTRACT_VERSION


APPROVED_EVALUATION_DATA_STATUS = "approved_evaluation_data"
APPROVED_CASE_STATUS = "approved_evaluation_case"
LABEL_PROVENANCE = (
    "deterministic_controlled_derivative_with_stratified_expert_qc"
)


def build_accuracy_case_manifest(
    dataset: Mapping[str, Any],
    dataset_validation: Mapping[str, Any],
    expert_qc: Mapping[str, Any],
    protocol_freeze: Mapping[str, Any],
) -> dict[str, Any]:
    """Approve the complete held-out controlled-derivative matrix for inference."""

    if dataset_validation.get("valid") is not True:
        raise ValueError("accuracy manifest requires valid dataset evidence")
    if expert_qc.get("valid") is not True:
        raise ValueError("accuracy manifest requires valid expert QC")
    if protocol_freeze.get("study_scores_inspected") is not False:
        raise ValueError("accuracy protocol was not registered score-blind")
    if protocol_freeze.get("dataset", {}).get("dataset_sha256") != (
        dataset_validation.get("dataset_sha256")
    ):
        raise ValueError("accuracy protocol is not bound to the full dataset")

    clusters = dataset.get("clusters")
    if not isinstance(clusters, list):
        raise ValueError("full dataset requires a cluster list")
    selected = [cluster for cluster in clusters if cluster.get("split") == "test"]
    if len(selected) != 284:
        raise ValueError("accuracy manifest requires 284 held-out source clusters")

    cases: list[dict[str, Any]] = []
    for cluster in selected:
        cluster_cases = cluster.get("cases")
        if not isinstance(cluster_cases, list) or len(cluster_cases) != len(VARIANTS):
            raise ValueError("accuracy manifest requires complete five-case clusters")
        observed_variants = {str(case.get("variant")) for case in cluster_cases}
        if observed_variants != set(VARIANTS):
            raise ValueError("accuracy manifest cluster variants differ from protocol")
        for case in cluster_cases:
            cases.append(
                {
                    "case_id": str(case["case_id"]),
                    "cluster_id": str(cluster["cluster_id"]),
                    "source_task_id": str(cluster["source_task_id"]),
                    "split": "test",
                    "variant": str(case["variant"]),
                    "registered_decision": str(case["proposed_decision"]),
                    "case_status": APPROVED_CASE_STATUS,
                    "label_provenance": LABEL_PROVENANCE,
                }
            )
    cases.sort(key=lambda row: str(row["case_id"]))
    if len(cases) != 1_420 or len({row["case_id"] for row in cases}) != 1_420:
        raise ValueError("accuracy manifest requires 1,420 unique held-out cases")
    return {
        "schema_version": 1,
        "data_status": APPROVED_EVALUATION_DATA_STATUS,
        "approval_scope": "locked_text_first_static_fidelity_evaluation",
        "label_provenance": LABEL_PROVENANCE,
        "human_review_scope": {
            "design": "stratified_expert_quality_control_sample",
            "source_clusters": 30,
            "cases": 150,
            "full_row_level_human_review_performed": False,
        },
        "source_clusters": 284,
        "cases_per_cluster": len(VARIANTS),
        "case_count": len(cases),
        "cases": cases,
        "claim_limit": (
            "approval denotes validated controlled-derivative study data, not "
            "1,420 independently human-labeled test cases"
        ),
    }


def load_accuracy_evaluation_cases(
    dataset: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[EvaluationCase, ...]:
    """Materialize only manifest-approved cases without exposing gold labels."""

    if manifest.get("data_status") != APPROVED_EVALUATION_DATA_STATUS:
        raise ValueError("evaluation manifest is not approved")
    manifest_rows = manifest.get("cases")
    if not isinstance(manifest_rows, Sequence) or isinstance(
        manifest_rows, (str, bytes)
    ):
        raise ValueError("evaluation manifest requires case rows")
    approved = {str(row["case_id"]): row for row in manifest_rows}
    if len(approved) != len(manifest_rows):
        raise ValueError("evaluation manifest case ids must be unique")

    dataset_cases: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for cluster in dataset.get("clusters", []):
        for case in cluster.get("cases", []):
            case_id = str(case["case_id"])
            if case_id in approved:
                dataset_cases[case_id] = (cluster, case)
    if set(dataset_cases) != set(approved):
        raise ValueError("evaluation manifest is not covered by the dataset")

    evaluation_cases: list[EvaluationCase] = []
    for case_id in sorted(approved):
        row = approved[case_id]
        cluster, case = dataset_cases[case_id]
        expected = {
            "cluster_id": str(cluster["cluster_id"]),
            "source_task_id": str(cluster["source_task_id"]),
            "split": str(cluster["split"]),
            "variant": str(case["variant"]),
            "registered_decision": str(case["proposed_decision"]),
        }
        if any(str(row.get(key)) != value for key, value in expected.items()):
            raise ValueError(f"{case_id}: approval metadata differs from dataset")
        if row.get("case_status") != APPROVED_CASE_STATUS:
            raise ValueError(f"{case_id}: case is not approved for evaluation")
        context = materialize_case_context(cluster, case)
        if any(
            key in context
            for key in ("registered_decision", "proposed_decision", "variant")
        ):
            raise ValueError(f"{case_id}: gold label leaked into model context")
        evaluation_cases.append(
            EvaluationCase(
                case_id=case_id,
                case_status=APPROVED_CASE_STATUS,
                context=context,
            )
        )
    return tuple(evaluation_cases)


def build_accuracy_run_configs(
    manifest: Mapping[str, Any],
    protocol_freeze: Mapping[str, Any],
    *,
    manifest_sha256: str,
    code_commit: str,
) -> list[RunConfig]:
    """Bind one deterministic full-matrix accuracy config per frozen model."""

    if manifest.get("data_status") != APPROVED_EVALUATION_DATA_STATUS:
        raise ValueError("accuracy configs require approved evaluation data")
    if manifest.get("case_count") != 1_420:
        raise ValueError("accuracy configs require the complete test matrix")
    expected_methods = tuple(spec.method_id for spec in METHOD_SPECS)
    if tuple(protocol_freeze.get("methods", ())) != expected_methods:
        raise ValueError("accuracy protocol method registry differs from code")
    decoding = protocol_freeze.get("decoding")
    if not isinstance(decoding, Mapping):
        raise ValueError("accuracy protocol decoding configuration is missing")

    configs = [
        RunConfig(
            run_id=(
                "multiuav_validation_placement_v1.accuracy."
                f"{model.model_id.rsplit('/', 1)[-1]}"
            ),
            study_id="multiuav_validation_placement_v1",
            run_kind="accuracy",
            model_id=model.model_id,
            model_revision=model.revision,
            methods=expected_methods,
            dataset_sha256=manifest_sha256,
            prompt_contract_version=PROMPT_CONTRACT_VERSION,
            decoding=dict(decoding),
            code_commit=code_commit,
        )
        for model in REGISTERED_MODEL_REVISIONS
    ]
    for config in configs:
        config.validate()
    return configs
