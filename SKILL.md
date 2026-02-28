---
name: amm-revision-engineer
description: >
  AMM Revision Analysis Engineer for MRO and CAMO operations. Use this skill
  whenever a user wants to analyze Aircraft Maintenance Manual (AMM) revisions,
  compare old vs new AMM revisions, identify changed tasks, new material
  requirements, new tooling or special equipment (borescope, NDT, etc.),
  revised maintenance intervals, or any impact on a Maintenance Program (AMP/
  Maintenance Planning Document). Also trigger when the user mentions: "AMM
  revision", "check revision impact", "what changed in the AMM", "new task
  added to AMM", "AMP update needed", "C-check task review", "tool requirement
  change", "material requirement changed", "scheduled interval updated". Always
  use this skill for AMM delta analysis in both MRO (task/tool/material focus)
  and airline CAMO (AMP interval focus) contexts.
compatibility:
  tools: [bash, python3, pandas, openpyxl, pdfplumber or PyMuPDF, difflib]
  python_packages: [pdfplumber, pandas, openpyxl, rich, typer]
---

# AMM Revision Engineer Skill

## Role & Purpose

This skill automates the job of an **AMM Revision Engineer** — the person
responsible for reviewing newly published OEM AMM revisions and identifying
every maintenance impact. Two main user groups exist:

| Context | Primary Focus |
|---|---|
| **MRO (Maintenance / Planning)** | New tools, materials, man-hours, special tests (NDT/borescope/pressure test), task additions/deletions before a check (A/C/D-check) |
| **Airline CAMO** | Changed scheduled intervals in the AMP, new mandatory tasks affecting the Approved Maintenance Programme |

---

## Workflow Overview

When the user invokes this skill, follow this sequence:

```
1. INTAKE     → Understand inputs (AMM revisions, AMP, aircraft type, context)
2. PARSE      → Extract structured data from AMM revision documents
3. DIFF       → Compare old vs. new AMM revision content
4. CLASSIFY   → Tag each change by impact type
5. FILTER     → Apply user's filter (MRO focus vs CAMO focus, ATA chapter, fleet)
6. REPORT     → Generate structured output (Excel + Markdown summary)
7. RECOMMEND  → Flag what actions the engineer must take
```

---

## Step 1: INTAKE — Understand the Task

Ask the user (or infer from context):

- **Aircraft type**: e.g. B737-800, A320, Cessna 172
- **AMM chapters affected**: ATA 05, 20, 21, 27, 28, 32, 57, etc.
- **Revision info**: Old revision number/date → New revision number/date
- **Input format**: PDF files, text extracted, or structured JSON
- **User context**: MRO pre-check planning OR airline CAMO AMP update
- **AMP/MPD file**: Excel or CSV with current scheduled tasks (for CAMO context)
- **Fleet effectivity**: Which MSNs/serial numbers are affected

If inputs are files, check `/mnt/user-data/uploads/` first.

---

## Step 2: PARSE — Extract AMM Content

Read `references/parsing_guide.md` for detailed extraction patterns.

**For PDF AMM revisions:**
```python
import pdfplumber

def extract_amm_tasks(pdf_path):
    """Extract task blocks from AMM PDF using ATA structure."""
    # See references/parsing_guide.md for full implementation
```

**Key fields to extract per task/section:**
- ATA Chapter-Section-Subject (e.g. 32-10-00)
- Task number / MPD reference
- Task title / description
- Interval (hours/cycles/calendar)
- Materials required (part numbers, quantities)
- Tools required (special tools, equipment)
- Special requirements (NDT, borescope, pressure test, eddy current)
- Man-hours estimate
- Effectivity (MSN ranges, modification status)
- Revision markers (new page, revised page, deleted page)

**Revision markers to look for:**
- "NEW" or "N" page codes in List of Effective Pages (LEP)
- "REVISED" or "R" page codes
- "DELETED" or "D" page codes
- Change bars (|) in page margins
- Highlights section at AMM front matter

---

## Step 3: DIFF — Compare Revisions

```python
import difflib

def compare_task_versions(old_task_text, new_task_text):
    """Generate structured diff of task content."""
    diff = list(difflib.unified_diff(
        old_task_text.splitlines(),
        new_task_text.splitlines(),
        lineterm='',
        n=3
    ))
    return diff
```

**Also compare at structured level:**
- Old interval vs. New interval (flag if changed)
- Old material list vs. New material list (flag new P/Ns added)
- Old tool list vs. New tool list (flag new special tools)
- Old man-hours vs. New man-hours

---

## Step 4: CLASSIFY — Tag Each Change

Classify every detected change into one or more categories:

| Tag | Description | Primary User |
|---|---|---|
| `NEW_TASK` | Entirely new maintenance task added | MRO + CAMO |
| `DELETED_TASK` | Task removed from AMM | MRO + CAMO |
| `INTERVAL_CHANGE` | Scheduled interval modified | CAMO |
| `INTERVAL_REDUCED` | Interval made more restrictive (shorter) | CAMO ⚠️ |
| `INTERVAL_EXTENDED` | Interval relaxed (longer) | CAMO |
| `NEW_MATERIAL` | New part number or consumable added | MRO |
| `MATERIAL_CHANGED` | Existing material specification changed | MRO |
| `NEW_TOOL` | New special tool required | MRO |
| `TOOL_CHANGED` | Tool specification changed | MRO |
| `NEW_SPECIAL_TEST` | Borescope / NDT / pressure test added | MRO |
| `MH_CHANGE` | Man-hours estimate changed | MRO |
| `EFFECTIVITY_CHANGE` | Applicability (MSN range) changed | Both |
| `ACCESS_CHANGE` | New access panels or procedures required | MRO |
| `SAFETY_NOTE` | New WARNING / CAUTION added | Both |

---

## Step 5: FILTER — Apply Context

**MRO Pre-Check Filter:**
```
Show changes for tasks relevant to upcoming check type:
  - A-check: ATA 05, 12, 20, 21, 27, 28, 29, 30, 32, 36
  - C-check: all chapters + structural (ATA 51-57)
  - Engine shop visit: ATA 70-80
Focus columns: NEW_TOOL, NEW_MATERIAL, NEW_SPECIAL_TEST, MH_CHANGE
```

**CAMO AMP Filter:**
```
Compare changed tasks against current AMP task list.
For each AMP task number:
  → Find matching AMM task
  → Check if interval changed
  → Flag INTERVAL_REDUCED as priority action
  → Flag NEW_TASK for potential AMP incorporation
Output: AMP impact matrix
```

---

## Step 6: REPORT — Generate Output

Always produce TWO outputs:

### A) Excel Report (for engineers)
Use `references/excel_template_guide.md` for format.

Sheets:
1. **Summary** — counts by change type, severity, ATA chapter
2. **All Changes** — full delta table with all tags
3. **MRO Action Items** — filtered for tools/materials/tests
4. **CAMO AMP Impact** — filtered for interval changes vs AMP
5. **New Tasks** — tasks requiring engineering review
6. **Deleted Tasks** — tasks to remove from check packages

### B) Markdown Summary (for quick review)
```markdown
## AMM Revision Delta Report
**Aircraft:** [type]
**AMM:** Rev [old] → Rev [new]  
**Date:** [analysis date]

### ⚠️ Priority Actions
- X tasks with REDUCED intervals → AMP amendment required
- Y new special tests added → Tool/equipment procurement needed

### MRO Impact
...

### CAMO AMP Impact  
...
```

---

## Step 7: RECOMMEND — Engineering Actions

Always end with a clear action list:

**For CAMO:**
- Tasks with `INTERVAL_REDUCED` → Submit AMP revision to authority
- `NEW_TASK` applicable to fleet → Evaluate for AMP incorporation
- `DELETED_TASK` in current AMP → Remove from AMP, notify authority

**For MRO:**
- `NEW_TOOL` → Check tool availability in stores; raise procurement if missing
- `NEW_SPECIAL_TEST` → Schedule NDT/borescope crew for check
- `NEW_MATERIAL` → Check stock; raise material request
- `MH_CHANGE` (significant) → Update check work package man-hours

---

## Sample Data

Sample AMM revision documents and AMP Excel files are in `sample_data/`:

```
sample_data/
├── amm_revisions/
│   ├── cessna172_amm_rev15_excerpt.txt    # Older revision baseline
│   ├── cessna172_amm_rev21_excerpt.txt    # Newer revision to analyze
│   └── revision_highlights_summary.txt    # AMM highlights page
├── amp_excel/
│   └── sample_AMP_cessna172.xlsx          # Simulated airline AMP
└── README.md                              # How to use sample data
```

Use these to test and demonstrate the skill without proprietary documents.

---

## References

- `references/parsing_guide.md` — PDF/text extraction patterns for ATA-format AMMs
- `references/excel_template_guide.md` — Excel report format and openpyxl implementation
- `references/ata_chapters.md` — ATA 100 / iSpec 2200 chapter reference
- `references/aviation_glossary.md` — Key terms: MPD, AMP, MEL, LEP, TR, etc.

---

## Error Handling

- If PDF cannot be parsed → instruct user to extract text manually or try pdfplumber vs PyMuPDF
- If AMM format is non-standard (older ATA 100 vs iSpec 2200) → note in report
- If no old revision available → perform single-revision analysis (extract only, no diff)
- If AMP Excel structure varies → ask user to identify the task number and interval columns
