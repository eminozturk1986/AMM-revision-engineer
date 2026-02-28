"""Pydantic v2 data models for AMM revision analysis."""

from __future__ import annotations
from pydantic import BaseModel, Field


class AMMTask(BaseModel):
    """A single maintenance task extracted from an AMM revision."""

    ata: str = ""
    task_ref: str = ""
    task_title: str = ""
    interval_fh: float | None = None
    interval_calendar: str | None = None   # e.g. "12 Months", "90 Days"
    interval_cycles: int | None = None
    materials: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    special_tests: list[str] = Field(default_factory=list)
    man_hours: float | None = None
    effectivity: str = "All"
    warnings: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)
    page_status: str = "UNCHANGED"   # NEW | REVISED | DELETED | UNCHANGED
    raw_text: str = ""


class AMMRevision(BaseModel):
    """A complete parsed AMM revision document."""

    aircraft_type: str = ""
    revision_number: str = ""
    revision_date: str = ""
    tasks: list[AMMTask] = Field(default_factory=list)
    highlights: list[dict] = Field(default_factory=list)


class ChangeRecord(BaseModel):
    """A single detected change between two AMM revisions."""

    ata: str = ""
    task_ref: str = ""
    task_title: str = ""
    change_type: str = ""              # see classifier.CHANGE_TYPES
    old_value: str | None = None
    new_value: str | None = None
    old_interval: str | None = None
    new_interval: str | None = None
    interval_delta: str | None = None  # e.g. "-200 FH" or "+2 Months"
    new_materials: list[str] = Field(default_factory=list)
    removed_materials: list[str] = Field(default_factory=list)
    new_tools: list[str] = Field(default_factory=list)
    special_test: str | None = None
    old_mh: float | None = None
    new_mh: float | None = None
    effectivity: str = "All"
    priority: str = "MEDIUM"          # HIGH | MEDIUM | LOW
    action_required: str = ""
    amp_task_match: str | None = None
