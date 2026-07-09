"""Shepherd-AI research prototype package."""

from shepherd_ai.intent import MissionIntent, parse_intent
from shepherd_ai.grounding import (
    GroundedIntent,
    GroundedMapObject,
    GroundedReference,
    MapLocation,
    ground_intent,
    grounded_map_objects,
)
from shepherd_ai.grounding_clarification import (
    ClarificationReport,
    ClarificationRequest,
    apply_clarification_choices,
    build_clarification_report,
)
from shepherd_ai.mission_planning import (
    MissionPlan,
    MissionPlanStep,
    MissionPlanValidation,
    mission_plan_mermaid,
    mission_plan_networkx_graph,
    mission_plan_task_graph,
    plan_grounded_mission,
    validate_mission_plan,
)
from shepherd_ai.scheduling import (
    Assignment,
    DroneState,
    ScheduleResult,
    SchedulableTask,
    compare_scheduling_strategies,
    extract_tasks_from_plan_payloads,
    load_drones,
    render_allocation_html,
    render_assignment_csv,
    render_assignment_markdown,
    schedule_tasks,
)
from shepherd_ai.week5_completion import (
    Week5CompletionAudit,
    build_week5_completion_audit,
    render_week5_completion_markdown,
)
from shepherd_ai.week2_completion import (
    Week2CompletionAudit,
    build_week2_completion_audit,
    render_week2_completion_markdown,
)
from shepherd_ai.vision import (
    DetectionRecord,
    VisionManifestRecord,
    load_vision_manifest,
    summarize_detections,
    summarize_vision_manifest,
)

__all__ = [
    "Assignment",
    "ClarificationReport",
    "ClarificationRequest",
    "DetectionRecord",
    "DroneState",
    "GroundedIntent",
    "GroundedMapObject",
    "GroundedReference",
    "MapLocation",
    "MissionPlan",
    "MissionPlanStep",
    "MissionPlanValidation",
    "MissionIntent",
    "ScheduleResult",
    "SchedulableTask",
    "Week5CompletionAudit",
    "Week2CompletionAudit",
    "VisionManifestRecord",
    "apply_clarification_choices",
    "build_week2_completion_audit",
    "build_week5_completion_audit",
    "build_clarification_report",
    "compare_scheduling_strategies",
    "extract_tasks_from_plan_payloads",
    "ground_intent",
    "grounded_map_objects",
    "load_drones",
    "load_vision_manifest",
    "mission_plan_mermaid",
    "mission_plan_networkx_graph",
    "mission_plan_task_graph",
    "plan_grounded_mission",
    "parse_intent",
    "render_allocation_html",
    "render_assignment_csv",
    "render_assignment_markdown",
    "render_week5_completion_markdown",
    "render_week2_completion_markdown",
    "schedule_tasks",
    "summarize_detections",
    "summarize_vision_manifest",
    "validate_mission_plan",
]
