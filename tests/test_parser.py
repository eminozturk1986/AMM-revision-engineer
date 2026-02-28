"""Tests for amm_engineer.parser module."""

from pathlib import Path
import pytest
from amm_engineer.parser import parse_text_amm

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data" / "amm_revisions"
REV15 = SAMPLE_DIR / "cessna172_amm_rev15_excerpt.txt"
REV21 = SAMPLE_DIR / "cessna172_amm_rev21_excerpt.txt"


@pytest.fixture
def rev15():
    return parse_text_amm(REV15.read_text(encoding="utf-8"))


@pytest.fixture
def rev21():
    return parse_text_amm(REV21.read_text(encoding="utf-8"))


def test_parser_detects_all_tasks(rev21):
    """Rev 21 excerpt should yield at least 7 tasks."""
    assert len(rev21.tasks) >= 7, (
        f"Expected >=7 tasks, got {len(rev21.tasks)}: "
        + str([t.task_ref for t in rev21.tasks])
    )


def test_parser_finds_new_task_marker(rev21):
    """Tasks marked 'THIS TASK IS NEW' should have page_status='NEW'."""
    new_tasks = [t for t in rev21.tasks if t.page_status == "NEW"]
    assert len(new_tasks) >= 3, (
        f"Expected >=3 NEW tasks, got {len(new_tasks)}: "
        + str([t.task_ref for t in new_tasks])
    )


def test_parser_extracts_revision_number(rev15, rev21):
    """Revision numbers must be parsed from header."""
    assert rev15.revision_number == "15"
    assert rev21.revision_number == "21"


def test_parser_extracts_highlights(rev21):
    """Highlights section must be parsed and contain entries."""
    assert len(rev21.highlights) >= 1, "No highlights extracted from Rev 21"


def test_parser_extracts_ata(rev21):
    """All tasks should have a non-empty ATA reference."""
    for task in rev21.tasks:
        assert task.ata, f"Task {task.task_ref} has empty ATA"


def test_parser_detects_borescope_special_test(rev21):
    """Rev 21 borescope task should have BORESCOPE in special_tests."""
    borescope_tasks = [
        t for t in rev21.tasks
        if any("BORESCOPE" in s.upper() for s in t.special_tests)
    ]
    assert len(borescope_tasks) >= 1, (
        "No task with BORESCOPE special test found in Rev 21"
    )


def test_parser_extracts_man_hours(rev21):
    """At least one task in Rev 21 should have man_hours parsed."""
    tasks_with_mh = [t for t in rev21.tasks if t.man_hours is not None]
    assert len(tasks_with_mh) >= 1, "No man-hours parsed from Rev 21"
