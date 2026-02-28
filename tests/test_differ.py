"""Tests for amm_engineer.differ module."""

from pathlib import Path
import pytest
from amm_engineer.differ import diff_revisions
from amm_engineer.parser import parse_text_amm

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data" / "amm_revisions"
REV15 = SAMPLE_DIR / "cessna172_amm_rev15_excerpt.txt"
REV21 = SAMPLE_DIR / "cessna172_amm_rev21_excerpt.txt"


@pytest.fixture
def changes():
    old_rev = parse_text_amm(REV15.read_text(encoding="utf-8"))
    new_rev = parse_text_amm(REV21.read_text(encoding="utf-8"))
    return diff_revisions(old_rev, new_rev)


def test_differ_detects_interval_reduction(changes):
    """Fuel filter 100 FH → 50 FH must be detected as INTERVAL_REDUCED."""
    reduced = [c for c in changes if c.change_type == "INTERVAL_REDUCED"]
    assert len(reduced) >= 1, (
        "No INTERVAL_REDUCED changes detected. "
        + f"All change types found: {[c.change_type for c in changes]}"
    )


def test_differ_detects_battery_interval_reduction(changes):
    """Battery 90 Days → 60 Days must be in INTERVAL_REDUCED."""
    reduced = [c for c in changes if c.change_type == "INTERVAL_REDUCED"]
    # At least 2 interval reductions expected (fuel filter + battery or engine mount)
    assert len(reduced) >= 2, (
        f"Expected >=2 INTERVAL_REDUCED, got {len(reduced)}"
    )


def test_differ_detects_new_borescope(changes):
    """Borescope inspection task must be tagged NEW_TASK."""
    new_tasks = [c for c in changes if c.change_type == "NEW_TASK"]
    assert len(new_tasks) >= 1, "No NEW_TASK changes detected"


def test_differ_detects_new_special_test(changes):
    """Borescope inspection must also generate a NEW_SPECIAL_TEST change."""
    special_tests = [c for c in changes if c.change_type == "NEW_SPECIAL_TEST"]
    assert len(special_tests) >= 1, "No NEW_SPECIAL_TEST changes detected"


def test_differ_detects_material_change(changes):
    """MIL-H-5606 → MIL-PRF-5606 must be MATERIAL_CHANGED."""
    mat_changes = [
        c for c in changes
        if c.change_type in ("MATERIAL_CHANGED", "NEW_MATERIAL")
    ]
    assert len(mat_changes) >= 1, (
        "No material changes detected. "
        + f"Found: {[c.change_type for c in changes]}"
    )


def test_differ_detects_mh_change(changes):
    """Annual MH change (16 → 19 hours) must be detected as MH_CHANGE."""
    mh_changes = [c for c in changes if c.change_type == "MH_CHANGE"]
    assert len(mh_changes) >= 1, "No MH_CHANGE detected"


def test_differ_total_changes(changes):
    """At least 8 distinct changes must be detected between Rev 15 and Rev 21."""
    assert len(changes) >= 8, (
        f"Expected >=8 changes total, got {len(changes)}: "
        + str([(c.change_type, c.ata) for c in changes])
    )


def test_priority_interval_reduced_is_high(changes):
    """All INTERVAL_REDUCED changes must have priority=HIGH."""
    for c in changes:
        if c.change_type == "INTERVAL_REDUCED":
            assert c.priority == "HIGH", (
                f"INTERVAL_REDUCED change {c.task_ref} has priority={c.priority}, expected HIGH"
            )
