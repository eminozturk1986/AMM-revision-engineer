"""Tests for amm_engineer.amp_matcher module."""

from pathlib import Path
import pytest
import pandas as pd

from amm_engineer.amp_matcher import load_amp, match_changes_to_amp, generate_amp_impact_matrix
from amm_engineer.differ import diff_revisions
from amm_engineer.parser import parse_text_amm

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
REV15 = SAMPLE_DIR / "amm_revisions" / "cessna172_amm_rev15_excerpt.txt"
REV21 = SAMPLE_DIR / "amm_revisions" / "cessna172_amm_rev21_excerpt.txt"
AMP_XLSX = SAMPLE_DIR / "amp_excel" / "sample_AMP_cessna172.xlsx"


@pytest.fixture
def amp_df():
    return load_amp(str(AMP_XLSX))


@pytest.fixture
def changes_with_amp(amp_df):
    old_rev = parse_text_amm(REV15.read_text(encoding="utf-8"))
    new_rev = parse_text_amm(REV21.read_text(encoding="utf-8"))
    changes = diff_revisions(old_rev, new_rev)
    return match_changes_to_amp(changes, amp_df)


def test_amp_loads_successfully(amp_df):
    """AMP Excel must load with required columns."""
    required = {"task_number", "ata_ref", "task_description"}
    assert required.issubset(set(amp_df.columns)), (
        f"Missing columns. Found: {list(amp_df.columns)}"
    )


def test_amp_has_tasks(amp_df):
    """AMP must contain at least 5 tasks."""
    assert len(amp_df) >= 5, f"Expected >=5 AMP tasks, got {len(amp_df)}"


def test_amp_matcher_finds_fuel_filter(changes_with_amp):
    """An interval change in ATA 05 (fuel filter) should match an AMP task."""
    interval_changes = [
        c for c in changes_with_amp
        if c.change_type == "INTERVAL_REDUCED" and c.ata.startswith("05")
    ]
    assert len(interval_changes) >= 1, (
        "No INTERVAL_REDUCED change found for ATA 05"
    )
    matched = [c for c in interval_changes if c.amp_task_match]
    assert len(matched) >= 1, (
        "Fuel filter interval change not matched to AMP task. "
        + f"Found changes: {[(c.ata, c.change_type, c.amp_task_match) for c in interval_changes]}"
    )


def test_amp_impact_matrix_has_rows(changes_with_amp, amp_df):
    """AMP impact matrix must have at least 1 row."""
    matrix = generate_amp_impact_matrix(changes_with_amp, amp_df)
    assert len(matrix) >= 1, "AMP impact matrix is empty"


def test_amp_impact_matrix_columns(changes_with_amp, amp_df):
    """AMP impact matrix must have required columns."""
    matrix = generate_amp_impact_matrix(changes_with_amp, amp_df)
    required_cols = {"ATA", "Change_Type", "Change_Required", "Authority_Notification"}
    assert required_cols.issubset(set(matrix.columns)), (
        f"Missing columns. Found: {list(matrix.columns)}"
    )
