# Excel Report Template Guide

## Required Libraries
```
pip install openpyxl pandas
```

## Report Structure

Generate an `.xlsx` file with these sheets in order:

1. **SUMMARY** — dashboard view
2. **ALL_CHANGES** — complete delta table
3. **MRO_ACTION_ITEMS** — tools, materials, special tests
4. **CAMO_AMP_IMPACT** — interval changes vs AMP
5. **NEW_TASKS** — tasks requiring engineering evaluation
6. **DELETED_TASKS** — tasks to remove from packages

---

## Column Definitions

### ALL_CHANGES sheet columns

| Column | Description | Example |
|---|---|---|
| ATA | ATA chapter-section-subject | 32-10-00 |
| Task_Ref | Task/MPD reference number | 32-10-01-200-801 |
| Task_Title | Short task description | Main Gear Borescope Inspection |
| Change_Type | Classification tag | NEW_SPECIAL_TEST |
| Old_Value | Previous content | N/A |
| New_Value | New content | Borescope required, p/n TOOL-XYZ |
| Old_Interval | Previous interval | 3000 FH |
| New_Interval | New interval | 2500 FH |
| Interval_Delta | Change in interval | -500 FH ⚠️ |
| Old_Materials | Previous material list | PR-1422 (Sealant) |
| New_Materials | New material list | PR-1422, PR-1776-B2 (New) |
| Old_Tools | Previous tool list | Standard |
| New_Tools | New tool list | Borescope Set B-1234 (NEW) |
| Special_Test | NDT/Borescope flag | BORESCOPE |
| Old_MH | Previous man-hours | 2.5 |
| New_MH | New man-hours | 4.0 |
| Effectivity | Applicable aircraft | MSN 0001-9999 |
| Priority | Engineer priority level | HIGH / MEDIUM / LOW |
| Action_Required | Recommended action | Procure borescope tool; Update work order |
| Rev_Old | AMM revision baseline | Rev 15, Dec 1996 |
| Rev_New | AMM revision analyzed | Rev 21, Jul 2007 |

### Priority Logic
```python
def assign_priority(row: dict) -> str:
    if row['change_type'] in ['INTERVAL_REDUCED', 'NEW_TASK', 'DELETED_TASK']:
        return 'HIGH'
    elif row['change_type'] in ['NEW_SPECIAL_TEST', 'NEW_TOOL', 'NEW_MATERIAL']:
        return 'MEDIUM'
    else:
        return 'LOW'
```

---

## Full openpyxl Implementation

```python
import openpyxl
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter
from datetime import datetime

# Color palette
COLORS = {
    'header_bg': 'FF1F4E79',     # Dark blue header
    'header_font': 'FFFFFFFF',   # White text
    'high_priority': 'FFFF0000', # Red
    'medium_priority': 'FFFF9900', # Orange
    'low_priority': 'FF00B050',  # Green
    'new': 'FFE2EFDA',           # Light green bg
    'deleted': 'FFFFC7CE',       # Light red bg
    'changed': 'FFFFEB9C',       # Light yellow bg
    'interval_reduced': 'FFFF0000', # Red for interval reduction
    'zebra': 'FFF2F2F2',         # Alternating row
}

def create_amm_report(changes: list[dict], output_path: str, 
                       amm_info: dict) -> str:
    """
    Create full Excel AMM revision report.
    
    Args:
        changes: List of change dicts (from diff analysis)
        output_path: Path for output .xlsx file
        amm_info: {'aircraft': str, 'old_rev': str, 'new_rev': str, 'date': str}
    
    Returns:
        Path to created file
    """
    wb = openpyxl.Workbook()
    
    # === SHEET 1: SUMMARY ===
    ws_sum = wb.active
    ws_sum.title = 'SUMMARY'
    _build_summary_sheet(ws_sum, changes, amm_info)
    
    # === SHEET 2: ALL CHANGES ===
    ws_all = wb.create_sheet('ALL_CHANGES')
    _build_changes_sheet(ws_all, changes, COLORS)
    
    # === SHEET 3: MRO ACTION ITEMS ===
    ws_mro = wb.create_sheet('MRO_ACTION_ITEMS')
    mro_changes = [c for c in changes if c.get('change_type') in [
        'NEW_TOOL', 'TOOL_CHANGED', 'NEW_MATERIAL', 'MATERIAL_CHANGED',
        'NEW_SPECIAL_TEST', 'MH_CHANGE', 'NEW_TASK', 'DELETED_TASK'
    ]]
    _build_changes_sheet(ws_mro, mro_changes, COLORS)
    
    # === SHEET 4: CAMO AMP IMPACT ===
    ws_camo = wb.create_sheet('CAMO_AMP_IMPACT')
    camo_changes = [c for c in changes if c.get('change_type') in [
        'INTERVAL_CHANGE', 'INTERVAL_REDUCED', 'INTERVAL_EXTENDED',
        'NEW_TASK', 'DELETED_TASK', 'EFFECTIVITY_CHANGE'
    ]]
    _build_camo_sheet(ws_camo, camo_changes, COLORS)
    
    # === SHEET 5: NEW TASKS ===
    ws_new = wb.create_sheet('NEW_TASKS')
    new_tasks = [c for c in changes if c.get('change_type') == 'NEW_TASK']
    _build_changes_sheet(ws_new, new_tasks, COLORS)
    
    # === SHEET 6: DELETED TASKS ===
    ws_del = wb.create_sheet('DELETED_TASKS')
    del_tasks = [c for c in changes if c.get('change_type') == 'DELETED_TASK']
    _build_changes_sheet(ws_del, del_tasks, COLORS)
    
    wb.save(output_path)
    return output_path


def _build_summary_sheet(ws, changes: list[dict], amm_info: dict):
    """Build the dashboard summary sheet."""
    ws.column_dimensions['A'].width = 35
    ws.column_dimensions['B'].width = 20
    
    # Title
    ws['A1'] = f"AMM Revision Delta Report — {amm_info.get('aircraft', '')}"
    ws['A1'].font = Font(bold=True, size=14, color='FF1F4E79')
    ws['A2'] = f"Rev {amm_info.get('old_rev', '?')} → Rev {amm_info.get('new_rev', '?')}"
    ws['A3'] = f"Analysis Date: {amm_info.get('date', datetime.now().strftime('%d %b %Y'))}"
    
    # Stats
    ws['A5'] = 'Change Summary'
    ws['A5'].font = Font(bold=True)
    
    stats = {}
    for c in changes:
        ct = c.get('change_type', 'UNKNOWN')
        stats[ct] = stats.get(ct, 0) + 1
    
    row = 6
    for change_type, count in sorted(stats.items()):
        ws.cell(row=row, column=1, value=change_type)
        ws.cell(row=row, column=2, value=count)
        if change_type == 'INTERVAL_REDUCED':
            ws.cell(row=row, column=1).font = Font(color='FFFF0000', bold=True)
            ws.cell(row=row, column=2).font = Font(color='FFFF0000', bold=True)
        row += 1
    
    ws.cell(row=row, column=1, value='TOTAL CHANGES')
    ws.cell(row=row, column=2, value=len(changes))
    ws.cell(row=row, column=1).font = Font(bold=True)
    ws.cell(row=row, column=2).font = Font(bold=True)


def _apply_header_style(ws, headers: list[str], row: int = 1):
    """Apply header row styling."""
    fill = PatternFill('solid', fgColor='1F4E79')
    font = Font(bold=True, color='FFFFFF')
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(col)].width = max(15, len(header) + 4)


def _build_changes_sheet(ws, changes: list[dict], colors: dict):
    """Build a standard changes table sheet."""
    headers = [
        'ATA', 'Task_Ref', 'Task_Title', 'Change_Type',
        'Old_Value', 'New_Value', 'Old_Interval', 'New_Interval',
        'Interval_Delta', 'New_Materials', 'New_Tools',
        'Special_Test', 'Old_MH', 'New_MH',
        'Priority', 'Action_Required', 'Effectivity'
    ]
    _apply_header_style(ws, headers)
    
    priority_colors = {
        'HIGH': 'FFFF0000',
        'MEDIUM': 'FFFF9900', 
        'LOW': 'FF00B050'
    }
    
    for i, change in enumerate(changes, 2):
        row_data = [
            change.get('ata', ''),
            change.get('task_ref', ''),
            change.get('task_title', ''),
            change.get('change_type', ''),
            change.get('old_value', ''),
            change.get('new_value', ''),
            change.get('old_interval', ''),
            change.get('new_interval', ''),
            change.get('interval_delta', ''),
            change.get('new_materials', ''),
            change.get('new_tools', ''),
            change.get('special_test', ''),
            change.get('old_mh', ''),
            change.get('new_mh', ''),
            change.get('priority', 'MEDIUM'),
            change.get('action_required', ''),
            change.get('effectivity', ''),
        ]
        
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=i, column=col, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
        
        # Color coding
        change_type = change.get('change_type', '')
        priority = change.get('priority', 'LOW')
        
        if change_type == 'INTERVAL_REDUCED':
            for col in range(1, len(headers)+1):
                ws.cell(row=i, column=col).fill = PatternFill('solid', fgColor='FFFFC7CE')
        elif change_type == 'NEW_TASK':
            for col in range(1, len(headers)+1):
                ws.cell(row=i, column=col).fill = PatternFill('solid', fgColor='FFE2EFDA')
        elif change_type == 'DELETED_TASK':
            for col in range(1, len(headers)+1):
                ws.cell(row=i, column=col).fill = PatternFill('solid', fgColor='FFFFC7CE')
        elif i % 2 == 0:
            for col in range(1, len(headers)+1):
                ws.cell(row=i, column=col).fill = PatternFill('solid', fgColor='FFF2F2F2')
        
        # Priority cell color
        priority_col = headers.index('Priority') + 1
        p_color = priority_colors.get(priority, 'FF000000')
        ws.cell(row=i, column=priority_col).font = Font(color=p_color, bold=True)
    
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = 'A2'


def _build_camo_sheet(ws, changes: list[dict], colors: dict):
    """Build CAMO-specific AMP impact sheet."""
    headers = [
        'ATA', 'Task_Ref', 'Task_Title', 'AMP_Task_Match',
        'Old_Interval', 'New_Interval', 'Interval_Delta',
        'Change_Type', 'Authority_Notification_Required',
        'AMP_Amendment_Required', 'Action_Required', 'Priority'
    ]
    _apply_header_style(ws, headers)
    
    for i, change in enumerate(changes, 2):
        interval_delta = change.get('interval_delta', '')
        amp_amendment = 'YES' if change.get('change_type') in [
            'INTERVAL_REDUCED', 'INTERVAL_EXTENDED', 'NEW_TASK', 'DELETED_TASK'
        ] else 'NO'
        authority_notif = 'YES' if change.get('change_type') == 'INTERVAL_REDUCED' else 'EVALUATE'
        
        row_data = [
            change.get('ata', ''),
            change.get('task_ref', ''),
            change.get('task_title', ''),
            change.get('amp_task_match', 'Not matched'),
            change.get('old_interval', ''),
            change.get('new_interval', ''),
            interval_delta,
            change.get('change_type', ''),
            authority_notif,
            amp_amendment,
            change.get('action_required', ''),
            change.get('priority', ''),
        ]
        
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=i, column=col, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
        
        if change.get('change_type') == 'INTERVAL_REDUCED':
            for col in range(1, len(headers)+1):
                ws.cell(row=i, column=col).fill = PatternFill('solid', fgColor='FFFFC7CE')
    
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = 'A2'
```
