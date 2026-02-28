"""Tests for amm_engineer.classifier module."""

import pytest
from amm_engineer.classifier import assign_priority, generate_action_text
from amm_engineer.models import ChangeRecord


def _cr(**kwargs) -> ChangeRecord:
    defaults = dict(
        ata="05-10-00",
        task_ref="05-10-00-200-801",
        task_title="Fuel Filter Replacement",
        change_type="INTERVAL_REDUCED",
        old_interval="100 FH",
        new_interval="50 FH",
        interval_delta="-50 FH",
    )
    defaults.update(kwargs)
    return ChangeRecord(**defaults)


def test_priority_interval_reduced():
    cr = _cr(change_type="INTERVAL_REDUCED")
    assert assign_priority(cr) == "HIGH"


def test_priority_new_task_standard():
    cr = _cr(change_type="NEW_TASK", task_title="Wheel Bearing Repack")
    assert assign_priority(cr) == "MEDIUM"


def test_priority_new_task_cmr():
    cr = _cr(change_type="NEW_TASK", task_title="CMR Landing Gear Inspection")
    assert assign_priority(cr) == "HIGH"


def test_priority_deleted_task():
    cr = _cr(change_type="DELETED_TASK")
    assert assign_priority(cr) == "HIGH"


def test_priority_new_special_test():
    cr = _cr(change_type="NEW_SPECIAL_TEST", special_test="BORESCOPE")
    assert assign_priority(cr) == "HIGH"


def test_priority_new_material():
    cr = _cr(change_type="NEW_MATERIAL")
    assert assign_priority(cr) == "MEDIUM"


def test_priority_mh_change_large():
    cr = _cr(change_type="MH_CHANGE", old_mh=16.0, new_mh=21.0)
    assert assign_priority(cr) == "MEDIUM"  # 31.25% > 20% threshold


def test_priority_mh_change_small():
    cr = _cr(change_type="MH_CHANGE", old_mh=10.0, new_mh=11.0)
    assert assign_priority(cr) == "LOW"  # 10% = boundary, our rule is <10% → LOW


def test_action_text_interval_reduced():
    cr = _cr(change_type="INTERVAL_REDUCED")
    text = generate_action_text(cr)
    assert "AMP" in text or "interval" in text.lower()
    assert "authority" in text.lower() or "notify" in text.lower() or "notification" in text.lower()


def test_action_text_new_special_test():
    cr = _cr(change_type="NEW_SPECIAL_TEST", special_test="BORESCOPE")
    text = generate_action_text(cr)
    assert "BORESCOPE" in text or "NDT" in text or "personnel" in text.lower()
