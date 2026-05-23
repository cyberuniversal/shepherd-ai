import re
from typing import Dict, List


PRIORITY_ENGINE = "deterministic_priority_v1"
HIGH_PRIORITY_TERMS = [
    "urgent",
    "urgently",
    "critical",
    "emergency",
    "immediate",
    "immediately",
    "asap",
    "right now",
    "now",
    "fast",
    "quickly",
    "priority one",
    "high priority",
    "\u0639\u0627\u062c\u0644",
    "\u0641\u0648\u0631\u0627",
    "\u0641\u0648\u0631\u0627\u064b",
    "\u0627\u0644\u0622\u0646",
    "\u0637\u0648\u0627\u0631\u0626",
    "\u062d\u0631\u062c",
]
LOW_PRIORITY_TERMS = [
    "low priority",
    "when possible",
    "when available",
    "no rush",
    "not urgent",
    "whenever",
    "later",
    "\u063a\u064a\u0631 \u0639\u0627\u062c\u0644",
    "\u0644\u0627 \u064a\u0648\u062c\u062f \u0627\u0633\u062a\u0639\u062c\u0627\u0644",
    "\u0644\u0627\u062d\u0642\u0627",
    "\u0644\u0627\u062d\u0642\u0627\u064b",
]
SAFETY_CONTROL_ACTIONS = {"return", "land", "hold", "cancel"}
ELEVATED_ACTIONS = {"secure"}


def assess_priority(command: str, intent: Dict) -> Dict:
    """Compute mission priority from operator language and deterministic policy.

    Parser/model priority is recorded for auditability but is not trusted as the
    authority. This keeps priority explainable and independent of dataset labels.
    """
    normalized = _normalize(command)
    low_terms = _matched_terms(normalized, LOW_PRIORITY_TERMS)
    high_terms = [
        term
        for term in _matched_terms(normalized, HIGH_PRIORITY_TERMS)
        if not _negated_high_urgency_term(normalized, term)
    ]
    action = str(intent.get("action") or "").strip().lower()
    parser_priority = intent.get("priority")
    score = 50
    reasons: List[str] = []

    if action in SAFETY_CONTROL_ACTIONS:
        score += 25
        reasons.append(f"Safety/control action '{action}' raises priority.")
    elif action in ELEVATED_ACTIONS:
        score += 10
        reasons.append(f"Operational action '{action}' modestly raises priority.")

    if high_terms:
        score += 35
        reasons.append(f"Explicit high-urgency terms: {', '.join(high_terms)}.")
    if low_terms:
        score -= 35
        reasons.append(f"Explicit low-urgency terms: {', '.join(low_terms)}.")

    conflict = bool(high_terms and low_terms)
    if conflict:
        priority = "medium"
        urgency_hint = "conflict"
        reasons.append("Conflicting urgency language requires operator review.")
    elif score >= 70:
        priority = "high"
        urgency_hint = "high" if high_terms or action in SAFETY_CONTROL_ACTIONS else None
    elif score <= 35:
        priority = "low"
        urgency_hint = "low"
    else:
        priority = "medium"
        urgency_hint = None

    if not reasons:
        reasons.append("No explicit urgency language or priority-raising mission policy matched.")

    return {
        "priority": priority,
        "urgency_hint": urgency_hint,
        "score": max(0, min(score, 100)),
        "source": PRIORITY_ENGINE,
        "parser_priority": parser_priority,
        "parser_priority_used": False,
        "matched_high_terms": high_terms,
        "matched_low_terms": low_terms,
        "requires_priority_review": conflict,
        "reasons": reasons,
    }


def apply_priority_assessment(command: str, intent: Dict) -> Dict:
    updated = dict(intent)
    assessment = assess_priority(command, updated)
    updated["priority"] = assessment["priority"]
    updated["urgency_hint"] = assessment["urgency_hint"]
    updated["priority_assessment"] = assessment
    return updated


def _normalize(command: str) -> str:
    return " ".join(str(command or "").lower().strip().split())


def _matched_terms(normalized: str, terms: List[str]) -> List[str]:
    matches = []
    for term in terms:
        normalized_term = _normalize(term)
        if not normalized_term:
            continue
        if re.search(rf"(?<!\w){re.escape(normalized_term)}(?!\w)", normalized, flags=re.UNICODE):
            matches.append(term)
    return matches


def _negated_high_urgency_term(normalized: str, term: str) -> bool:
    normalized_term = _normalize(term)
    if normalized_term not in {"urgent", "urgently"}:
        return False
    return bool(re.search(r"\b(?:not|non)\s+urgent(?:ly)?\b", normalized))
