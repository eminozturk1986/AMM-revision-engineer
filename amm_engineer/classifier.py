"""Classify AMM changes by type and assign priority + action text."""

from __future__ import annotations

from .models import ChangeRecord

# ---------------------------------------------------------------------------
# Canonical change type constants
# ---------------------------------------------------------------------------

CHANGE_TYPES = [
    "NEW_TASK",
    "DELETED_TASK",
    "INTERVAL_CHANGE",
    "INTERVAL_REDUCED",
    "INTERVAL_EXTENDED",
    "NEW_MATERIAL",
    "MATERIAL_CHANGED",
    "NEW_TOOL",
    "TOOL_CHANGED",
    "NEW_SPECIAL_TEST",
    "MH_CHANGE",
    "EFFECTIVITY_CHANGE",
    "SAFETY_NOTE",
    "ACCESS_CHANGE",
]

# CMR / ALI keyword indicators on new tasks → always HIGH priority
_CMR_ALI_KEYWORDS = ["CMR", "ALI", "AIRWORTHINESS LIMITATION", "CRITICAL MAINTENANCE"]


def assign_priority(change: ChangeRecord) -> str:
    """
    Determine priority level for a change.

    HIGH   — INTERVAL_REDUCED, DELETED_TASK, NEW_TASK with CMR/ALI keywords,
              NEW_SPECIAL_TEST
    MEDIUM — INTERVAL_EXTENDED, NEW_MATERIAL, MATERIAL_CHANGED, NEW_TOOL,
              TOOL_CHANGED, MH_CHANGE >20%, NEW_TASK (standard)
    LOW    — SAFETY_NOTE, EFFECTIVITY_CHANGE, MH_CHANGE 10-20%, ACCESS_CHANGE,
              INTERVAL_CHANGE (generic)
    """
    ct = change.change_type

    if ct == "INTERVAL_REDUCED":
        return "HIGH"

    if ct == "DELETED_TASK":
        return "HIGH"

    if ct == "NEW_TASK":
        title_upper = (change.task_title or "").upper()
        desc_upper = (change.new_value or "").upper()
        if any(kw in title_upper or kw in desc_upper for kw in _CMR_ALI_KEYWORDS):
            return "HIGH"
        return "MEDIUM"

    if ct == "NEW_SPECIAL_TEST":
        return "HIGH"

    if ct in ("NEW_MATERIAL", "MATERIAL_CHANGED", "NEW_TOOL", "TOOL_CHANGED",
              "INTERVAL_EXTENDED"):
        return "MEDIUM"

    if ct == "MH_CHANGE":
        old = change.old_mh or 0.0
        new = change.new_mh or 0.0
        if old > 0:
            pct = abs(new - old) / old * 100
            if pct > 20:
                return "MEDIUM"
        return "LOW"

    return "LOW"


def generate_action_text(change: ChangeRecord) -> str:
    """
    Generate a concise human-readable action recommendation for the change.
    """
    ct = change.change_type

    actions = {
        "INTERVAL_REDUCED": (
            f"UPDATE AMP task interval ({change.old_interval} → {change.new_interval}). "
            "Check if authority notification required per Part-M / Part-CAMO."
        ),
        "INTERVAL_EXTENDED": (
            f"Review AMP task interval. New interval {change.new_interval} is less restrictive. "
            "Submit AMP amendment if desired."
        ),
        "INTERVAL_CHANGE": (
            f"Verify AMP interval matches new AMM value: {change.new_interval}."
        ),
        "NEW_TASK": (
            f"Evaluate new task '{change.task_title}' for incorporation into AMP / work package. "
            "Assess effectivity against fleet."
        ),
        "DELETED_TASK": (
            f"Remove task '{change.task_title}' from AMP and check packages. "
            "Notify authority if task was part of approved AMP."
        ),
        "NEW_MATERIAL": (
            f"Add material to approved materials list: {', '.join(change.new_materials)}. "
            "Check stock availability."
        ),
        "MATERIAL_CHANGED": (
            f"Update approved material specification. "
            f"Old: {change.old_value} → New: {change.new_value}. "
            "Ensure QA approves new spec."
        ),
        "NEW_TOOL": (
            f"Procure new special tool: {', '.join(change.new_tools)}. "
            "Check availability in stores; raise purchase request if missing."
        ),
        "TOOL_CHANGED": (
            f"Update tool specification: {change.new_value}. "
            "Verify calibration requirements."
        ),
        "NEW_SPECIAL_TEST": (
            f"Schedule trained {change.special_test or 'NDT'} personnel for inspection. "
            "Verify Part-66 competency and equipment availability."
        ),
        "MH_CHANGE": (
            f"Update work package man-hours: {change.old_mh} MH → {change.new_mh} MH. "
            "Revise labour cost estimates."
        ),
        "EFFECTIVITY_CHANGE": (
            "Review updated effectivity against fleet MSN list. "
            "Confirm which aircraft are now affected."
        ),
        "SAFETY_NOTE": (
            "Review new WARNING/CAUTION with maintenance team. "
            "Update job cards and training material if required."
        ),
        "ACCESS_CHANGE": (
            "Update work package with new access panel procedure. "
            "Check man-hours impact."
        ),
    }
    return actions.get(ct, f"Review {ct} change and assess impact.")


def classify_and_enrich(change: ChangeRecord) -> ChangeRecord:
    """Assign priority and action text to a ChangeRecord in-place."""
    change.priority = assign_priority(change)
    change.action_required = generate_action_text(change)
    return change
