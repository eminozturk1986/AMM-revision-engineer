"""Compare two AMMRevision objects and produce a list of ChangeRecords."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .classifier import classify_and_enrich
from .models import AMMRevision, AMMTask, ChangeRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _similarity(a: str, b: str) -> float:
    """Return 0-1 string similarity ratio."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _interval_str(task: AMMTask) -> str | None:
    """Return a combined interval description string for a task."""
    parts = []
    if task.interval_fh is not None:
        parts.append(f"{task.interval_fh:g} FH")
    if task.interval_calendar:
        parts.append(task.interval_calendar)
    return " or ".join(parts) if parts else None


def _parse_fh_value(s: str | None) -> float | None:
    """Extract flight-hour number from interval string."""
    if not s:
        return None
    m = re.search(r"(\d[\d,]*\.?\d*)\s*FH", s, re.IGNORECASE)
    return float(m.group(1).replace(",", "")) if m else None


def _parse_calendar_days(s: str | None) -> float | None:
    """Convert calendar interval string to days for comparison."""
    if not s:
        return None
    upper = s.upper()
    m = re.search(r"(\d+\.?\d*)\s*(MONTHS?|MO)\b", upper)
    if m:
        return float(m.group(1)) * 30
    m = re.search(r"(\d+\.?\d*)\s*DAYS?\b", upper)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+\.?\d*)\s*YEARS?\b", upper)
    if m:
        return float(m.group(1)) * 365
    if "ANNUAL" in upper:
        return 365
    return None


def _build_task_index(rev: AMMRevision) -> dict[str, AMMTask]:
    """Build task_ref → AMMTask index from a revision."""
    return {t.task_ref: t for t in rev.tasks}


def _match_tasks(
    old_tasks: list[AMMTask], new_tasks: list[AMMTask]
) -> tuple[list[tuple[AMMTask, AMMTask]], list[AMMTask], list[AMMTask]]:
    """
    Match tasks between old and new revision.

    Returns:
        matched  — list of (old_task, new_task) pairs
        only_new — tasks present only in new revision
        only_old — tasks present only in old revision
    """
    old_index = {t.task_ref: t for t in old_tasks}
    new_index = {t.task_ref: t for t in new_tasks}

    matched: list[tuple[AMMTask, AMMTask]] = []
    old_unmatched = set(old_index.keys())
    new_unmatched = set(new_index.keys())

    # 1. Exact task_ref match
    for ref in list(new_unmatched):
        if ref in old_unmatched:
            matched.append((old_index[ref], new_index[ref]))
            old_unmatched.discard(ref)
            new_unmatched.discard(ref)

    # 2. Fuzzy title + ATA match for remainders
    for new_ref in list(new_unmatched):
        nt = new_index[new_ref]
        best_score = 0.0
        best_old_ref = None
        for old_ref in old_unmatched:
            ot = old_index[old_ref]
            if ot.ata == nt.ata:
                score = _similarity(ot.task_title, nt.task_title)
                if score > best_score:
                    best_score = score
                    best_old_ref = old_ref
        if best_score >= 0.65 and best_old_ref:
            matched.append((old_index[best_old_ref], new_index[new_ref]))
            old_unmatched.discard(best_old_ref)
            new_unmatched.discard(new_ref)

    only_new = [new_index[r] for r in new_unmatched]
    only_old = [old_index[r] for r in old_unmatched]
    return matched, only_new, only_old


# ---------------------------------------------------------------------------
# Interval comparison
# ---------------------------------------------------------------------------

def compare_intervals(
    old: AMMTask, new: AMMTask
) -> tuple[str, str] | None:
    """
    Compare intervals between two task versions.

    Returns (change_type, delta_description) or None if no change.
    """
    old_fh = old.interval_fh
    new_fh = new.interval_fh
    old_cal = old.interval_calendar
    new_cal = new.interval_calendar

    fh_changed = old_fh != new_fh and not (old_fh is None and new_fh is None)
    cal_changed = old_cal != new_cal and not (old_cal is None and new_cal is None)

    if not fh_changed and not cal_changed:
        return None

    # Determine direction
    change_type = "INTERVAL_CHANGE"
    delta_parts: list[str] = []

    if fh_changed and old_fh is not None and new_fh is not None:
        diff = new_fh - old_fh
        direction = "+" if diff > 0 else ""
        delta_parts.append(f"{direction}{diff:g} FH")
        if new_fh < old_fh:
            change_type = "INTERVAL_REDUCED"
        else:
            change_type = "INTERVAL_EXTENDED"

    if cal_changed:
        old_days = _parse_calendar_days(old_cal)
        new_days = _parse_calendar_days(new_cal)
        if old_days and new_days:
            diff_days = new_days - old_days
            direction = "+" if diff_days > 0 else ""
            # Report in natural units
            if abs(diff_days) >= 25:
                months = diff_days / 30
                delta_parts.append(f"{direction}{months:.0f} Months")
            else:
                delta_parts.append(f"{direction}{diff_days:.0f} Days")

            if new_days < old_days:
                change_type = "INTERVAL_REDUCED"
            elif new_days > old_days and change_type != "INTERVAL_REDUCED":
                change_type = "INTERVAL_EXTENDED"

    delta = ", ".join(delta_parts) if delta_parts else "changed"
    return change_type, delta


# ---------------------------------------------------------------------------
# Main diff engine
# ---------------------------------------------------------------------------

def _parse_time_limits_items(raw_text: str) -> dict[str, tuple[float | None, str | None]]:
    """
    Parse per-item intervals from a TIME LIMITS table in a task block.

    Returns dict: {item_name_lower: (fh_value, calendar_str)}
    E.g. {"fuel filter replacement": (100.0, "12 Mo"), ...}
    """
    items: dict[str, tuple[float | None, str | None]] = {}
    in_table = False
    for line in raw_text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()

        if re.search(r"TIME\s+LIMITS", upper):
            in_table = True
            continue

        if in_table:
            if re.match(r"^[-=\s]+$", stripped) or upper.startswith("ITEM"):
                continue
            # Stop at numbered section 3 onward
            if re.match(r"^[3-9]\.", stripped):
                break
            if not stripped or stripped.startswith(("←", "NOTE", "WARNING", "CAUTION")):
                continue

            fh_m = re.search(r"(\d+\.?\d*)\s*FH\b", stripped, re.IGNORECASE)
            cal_m = re.search(r"(\d+\.?\d*)\s*(Days?|Months?|Mo)\b", stripped, re.IGNORECASE)
            ann_m = re.search(r"\bAnnual\b", stripped, re.IGNORECASE)

            if not (fh_m or cal_m or ann_m):
                continue

            # Item name = everything before the first interval token
            first_pos = len(stripped)
            for m in (fh_m, cal_m):
                if m and m.start() < first_pos:
                    first_pos = m.start()
            if ann_m and ann_m.start() < first_pos:
                first_pos = ann_m.start()

            item_name = stripped[:first_pos]
            item_name = re.sub(r"\s{2,}.*$", "", item_name).strip()
            item_name = re.sub(r"[←→].*$", "", item_name).strip()

            if len(item_name) < 3 or item_name.startswith("-"):
                continue

            fh = float(fh_m.group(1)) if fh_m else None
            cal: str | None = None
            if cal_m:
                cal = f"{cal_m.group(1)} {cal_m.group(2).capitalize()}"
            elif ann_m:
                cal = "Annual"

            items[item_name.lower()] = (fh, cal)

    return items


def _diff_time_limits(old_task: AMMTask, new_task: AMMTask) -> list[ChangeRecord]:
    """
    Compare per-item intervals in TIME LIMITS tables of two matched tasks.
    Produces INTERVAL_REDUCED / INTERVAL_EXTENDED records for each changed row.
    """
    old_items = _parse_time_limits_items(old_task.raw_text)
    new_items = _parse_time_limits_items(new_task.raw_text)
    changes: list[ChangeRecord] = []

    for old_name, (old_fh, old_cal) in old_items.items():
        # Find best matching item in new revision
        new_match_name = None
        new_match_vals = None
        best_score = 0.0
        for new_name, vals in new_items.items():
            s = _similarity(old_name, new_name)
            if s > best_score:
                best_score = s
                new_match_name = new_name
                new_match_vals = vals

        if new_match_vals is None or best_score < 0.75:
            continue

        new_fh, new_cal = new_match_vals

        # FH comparison
        fh_changed = (old_fh != new_fh) and not (old_fh is None and new_fh is None)
        # Calendar comparison
        old_days = _parse_calendar_days(old_cal)
        new_days = _parse_calendar_days(new_cal)
        cal_changed = (old_cal != new_cal) and (old_days is not None) and (new_days is not None)

        if not fh_changed and not cal_changed:
            continue

        # Build interval strings
        old_parts = [f"{old_fh:g} FH"] if old_fh else []
        if old_cal:
            old_parts.append(old_cal)
        new_parts = [f"{new_fh:g} FH"] if new_fh else []
        if new_cal:
            new_parts.append(new_cal)

        old_int_str = " or ".join(old_parts) or None
        new_int_str = " or ".join(new_parts) or None

        # Determine type and delta
        change_type = "INTERVAL_CHANGE"
        delta_parts: list[str] = []

        if fh_changed and old_fh is not None and new_fh is not None:
            diff = new_fh - old_fh
            direction = "+" if diff > 0 else ""
            delta_parts.append(f"{direction}{diff:g} FH")
            change_type = "INTERVAL_REDUCED" if new_fh < old_fh else "INTERVAL_EXTENDED"

        if cal_changed and old_days and new_days:
            diff_d = new_days - old_days
            direction = "+" if diff_d > 0 else ""
            if abs(diff_d) >= 25:
                delta_parts.append(f"{direction}{diff_d / 30:.0f} Months")
            else:
                delta_parts.append(f"{direction}{diff_d:.0f} Days")
            if new_days < old_days and change_type != "INTERVAL_REDUCED":
                change_type = "INTERVAL_REDUCED"
            elif new_days > old_days and change_type not in ("INTERVAL_REDUCED", "INTERVAL_EXTENDED"):
                change_type = "INTERVAL_EXTENDED"

        cr = ChangeRecord(
            ata=new_task.ata,
            task_ref=new_task.task_ref,
            task_title=old_name.title(),
            change_type=change_type,
            old_interval=old_int_str,
            new_interval=new_int_str,
            interval_delta=", ".join(delta_parts) if delta_parts else "changed",
            effectivity=new_task.effectivity,
        )
        changes.append(classify_and_enrich(cr))

    return changes


def diff_revisions(
    old_rev: AMMRevision, new_rev: AMMRevision
) -> list[ChangeRecord]:
    """
    Compare two AMM revisions and return a list of all detected ChangeRecords.

    Covers: new/deleted tasks, interval changes, material/tool/special-test
    additions, man-hour changes, and new warnings/cautions.
    """
    changes: list[ChangeRecord] = []
    matched, only_new, only_old = _match_tasks(old_rev.tasks, new_rev.tasks)

    # ---- NEW TASKS --------------------------------------------------------
    for task in only_new:
        cr = ChangeRecord(
            ata=task.ata,
            task_ref=task.task_ref,
            task_title=task.task_title,
            change_type="NEW_TASK",
            new_value=task.task_title,
            new_interval=_interval_str(task),
            new_materials=task.materials,
            new_tools=task.tools,
            special_test=task.special_tests[0] if task.special_tests else None,
            new_mh=task.man_hours,
            effectivity=task.effectivity,
        )
        changes.append(classify_and_enrich(cr))

        # Also emit NEW_SPECIAL_TEST for borescope/NDT new tasks
        for st in task.special_tests:
            cr2 = ChangeRecord(
                ata=task.ata,
                task_ref=task.task_ref,
                task_title=task.task_title,
                change_type="NEW_SPECIAL_TEST",
                new_value=f"{st} inspection required",
                special_test=st,
                effectivity=task.effectivity,
            )
            changes.append(classify_and_enrich(cr2))

    # ---- DELETED TASKS ----------------------------------------------------
    for task in only_old:
        cr = ChangeRecord(
            ata=task.ata,
            task_ref=task.task_ref,
            task_title=task.task_title,
            change_type="DELETED_TASK",
            old_value=task.task_title,
            old_interval=_interval_str(task),
            old_mh=task.man_hours,
            effectivity=task.effectivity,
        )
        changes.append(classify_and_enrich(cr))

    # ---- MATCHED TASKS — field-level diffs --------------------------------
    for old_task, new_task in matched:

        # 1. Interval
        interval_result = compare_intervals(old_task, new_task)
        if interval_result:
            change_type, delta = interval_result
            old_int = _interval_str(old_task)
            new_int = _interval_str(new_task)
            cr = ChangeRecord(
                ata=new_task.ata,
                task_ref=new_task.task_ref,
                task_title=new_task.task_title,
                change_type=change_type,
                old_interval=old_int,
                new_interval=new_int,
                interval_delta=delta,
                effectivity=new_task.effectivity,
            )
            changes.append(classify_and_enrich(cr))

        # 2. Materials
        old_mats = set(m.upper() for m in old_task.materials)
        new_mats = set(m.upper() for m in new_task.materials)
        added_mats = [m for m in new_task.materials if m.upper() not in old_mats]
        removed_mats = [m for m in old_task.materials if m.upper() not in new_mats]

        if added_mats and not removed_mats:
            cr = ChangeRecord(
                ata=new_task.ata,
                task_ref=new_task.task_ref,
                task_title=new_task.task_title,
                change_type="NEW_MATERIAL",
                new_materials=added_mats,
                effectivity=new_task.effectivity,
            )
            changes.append(classify_and_enrich(cr))

        elif added_mats and removed_mats:
            cr = ChangeRecord(
                ata=new_task.ata,
                task_ref=new_task.task_ref,
                task_title=new_task.task_title,
                change_type="MATERIAL_CHANGED",
                old_value="; ".join(removed_mats),
                new_value="; ".join(added_mats),
                new_materials=added_mats,
                removed_materials=removed_mats,
                effectivity=new_task.effectivity,
            )
            changes.append(classify_and_enrich(cr))

        # 3. Tools
        old_tools = set(t.upper() for t in old_task.tools)
        new_tools = set(t.upper() for t in new_task.tools)
        added_tools = [t for t in new_task.tools if t.upper() not in old_tools]

        if added_tools:
            cr = ChangeRecord(
                ata=new_task.ata,
                task_ref=new_task.task_ref,
                task_title=new_task.task_title,
                change_type="NEW_TOOL",
                new_tools=added_tools,
                new_value="; ".join(added_tools),
                effectivity=new_task.effectivity,
            )
            changes.append(classify_and_enrich(cr))

        # 4. Special tests
        old_st = set(new_task.special_tests)  # intentionally new_task here to keep logic correct
        old_st = set(s.upper() for s in old_task.special_tests)
        new_st = [s for s in new_task.special_tests if s.upper() not in old_st]
        for st in new_st:
            cr = ChangeRecord(
                ata=new_task.ata,
                task_ref=new_task.task_ref,
                task_title=new_task.task_title,
                change_type="NEW_SPECIAL_TEST",
                new_value=f"{st} inspection required",
                special_test=st,
                effectivity=new_task.effectivity,
            )
            changes.append(classify_and_enrich(cr))

        # 5. Man-hours (flag if change >= 10%)
        if old_task.man_hours and new_task.man_hours:
            old_mh = old_task.man_hours
            new_mh = new_task.man_hours
            if abs(new_mh - old_mh) / old_mh >= 0.10:
                cr = ChangeRecord(
                    ata=new_task.ata,
                    task_ref=new_task.task_ref,
                    task_title=new_task.task_title,
                    change_type="MH_CHANGE",
                    old_mh=old_mh,
                    new_mh=new_mh,
                    effectivity=new_task.effectivity,
                )
                changes.append(classify_and_enrich(cr))

        # 6. New warnings / cautions (SAFETY_NOTE)
        old_w = set(w.upper() for w in old_task.warnings + old_task.cautions)
        new_safety = [
            x for x in new_task.warnings + new_task.cautions
            if x.upper() not in old_w
        ]
        if new_safety:
            cr = ChangeRecord(
                ata=new_task.ata,
                task_ref=new_task.task_ref,
                task_title=new_task.task_title,
                change_type="SAFETY_NOTE",
                new_value="; ".join(new_safety),
                effectivity=new_task.effectivity,
            )
            changes.append(classify_and_enrich(cr))

        # 7. TIME LIMITS table — per-item interval comparison
        tl_changes = _diff_time_limits(old_task, new_task)
        changes.extend(tl_changes)

    return changes
