"""Match AMM change records against an AMP (Approved Maintenance Programme) Excel file."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from thefuzz import fuzz

from .models import ChangeRecord


# ---------------------------------------------------------------------------
# AMP loader
# ---------------------------------------------------------------------------

# Flexible column name aliases
_COL_ALIASES = {
    "task_number": ["task_no", "task_number", "task", "task no", "amp task", "item"],
    "ata_ref": ["ata", "ata_ref", "ata ref", "ata chapter", "chapter"],
    "task_description": ["description", "task_description", "task_title", "title", "task description"],
    "interval_fh": ["interval_fh", "fh", "flight hours", "hours", "fh interval"],
    "interval_calendar": ["interval_calendar", "calendar", "calendar interval", "months", "days"],
}


def _find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    """Find a DataFrame column matching one of the aliases (case-insensitive)."""
    lower_cols = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias in lower_cols:
            return lower_cols[alias]
    return None


def load_amp(excel_path: str) -> pd.DataFrame:
    """
    Load AMP from an Excel file with flexible column detection.

    Attempts to map common column name variants to a canonical schema.
    Returns a DataFrame with columns: task_number, ata_ref, task_description,
    interval_fh, interval_calendar.
    """
    df = pd.read_excel(excel_path, engine="openpyxl")

    rename_map: dict[str, str] = {}
    for canonical, aliases in _COL_ALIASES.items():
        found = _find_column(df, aliases)
        if found and found not in rename_map.values():
            rename_map[found] = canonical

    df = df.rename(columns=rename_map)

    # Ensure all canonical columns exist (fill with empty if missing)
    for col in ["task_number", "ata_ref", "task_description", "interval_fh", "interval_calendar"]:
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("").astype(str)
    return df[["task_number", "ata_ref", "task_description", "interval_fh", "interval_calendar"]]


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------

def _ata_prefix(ata: str) -> str:
    """Return two-digit ATA chapter from 'XX-YY-ZZ' or 'XX'."""
    return str(ata).split("-")[0].strip().zfill(2)


def match_changes_to_amp(
    changes: list[ChangeRecord],
    amp_df: pd.DataFrame,
    fuzzy_threshold: int = 65,
) -> list[ChangeRecord]:
    """
    For each ChangeRecord, attempt to find a matching AMP task.

    Matching priority:
      1. Exact ATA chapter match + fuzzy description match (>=threshold)
      2. ATA chapter match only (lower confidence)

    Sets change.amp_task_match to the AMP task number.
    """
    for change in changes:
        change_ata = _ata_prefix(change.ata)

        # Filter AMP rows by ATA chapter
        ata_rows = amp_df[amp_df["ata_ref"].str.startswith(change_ata)]
        if ata_rows.empty:
            # Try broader match (just first two digits)
            ata_rows = amp_df[amp_df["ata_ref"].str[:2] == change_ata]

        if ata_rows.empty:
            continue

        # Fuzzy match against task descriptions
        best_score = 0
        best_task_no = None
        for _, row in ata_rows.iterrows():
            score = fuzz.token_sort_ratio(
                change.task_title.lower(),
                str(row["task_description"]).lower(),
            )
            if score > best_score:
                best_score = score
                best_task_no = str(row["task_number"])

        if best_score >= fuzzy_threshold and best_task_no:
            change.amp_task_match = best_task_no
        elif not ata_rows.empty:
            # Fall back: use first ATA-matched task with low confidence note
            first = ata_rows.iloc[0]
            change.amp_task_match = f"{first['task_number']} (ATA match only)"

    return changes


# ---------------------------------------------------------------------------
# AMP impact matrix
# ---------------------------------------------------------------------------

def generate_amp_impact_matrix(
    changes: list[ChangeRecord],
    amp_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a CAMO-focused AMP impact matrix.

    Columns: AMP_Task_No, ATA, Current_Interval, New_AMM_Interval,
             Change_Required, Authority_Notification, Priority, Notes
    """
    relevant_types = {
        "INTERVAL_REDUCED", "INTERVAL_EXTENDED", "INTERVAL_CHANGE",
        "NEW_TASK", "DELETED_TASK",
    }
    rows = []

    for change in changes:
        if change.change_type not in relevant_types:
            continue

        # Look up current AMP interval
        amp_task = change.amp_task_match or ""
        current_interval = ""
        if amp_task and not amp_task.endswith("(ATA match only)"):
            row = amp_df[amp_df["task_number"] == amp_task]
            if not row.empty:
                fh = str(row.iloc[0]["interval_fh"]).strip()
                cal = str(row.iloc[0]["interval_calendar"]).strip()
                parts = [p for p in [fh, cal] if p and p not in ("", "nan", "0")]
                current_interval = " / ".join(parts)

        authority_needed = "YES" if change.change_type == "INTERVAL_REDUCED" else "EVALUATE"
        change_needed = (
            "YES" if change.change_type in ("INTERVAL_REDUCED", "INTERVAL_EXTENDED",
                                            "NEW_TASK", "DELETED_TASK")
            else "NO"
        )

        rows.append({
            "AMP_Task_No": amp_task or "N/A",
            "ATA": change.ata,
            "Task_Title": change.task_title,
            "Current_AMP_Interval": current_interval,
            "New_AMM_Interval": change.new_interval or "",
            "Interval_Delta": change.interval_delta or "",
            "Change_Type": change.change_type,
            "Change_Required": change_needed,
            "Authority_Notification": authority_needed,
            "Priority": change.priority,
            "Notes": change.action_required,
        })

    return pd.DataFrame(rows)
