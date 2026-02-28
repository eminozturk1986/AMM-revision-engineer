# CLAUDE CODE — PROJECT HANDOVER DOCUMENT
# AMM Revision Engineer Skill
# Author: Emin Öztürk | Agentic Aviation
# Handover Date: 2026-02-28
# GitHub: https://github.com/eminozturk1986/AMM-revision-engineer

---

## 🧠 WHO YOU ARE WORKING WITH

You are working with **Emin Öztürk**, an AMOS Administrator and Aeronautical
Engineer at Lufthansa with 10+ years of aviation MRO experience. He has already
built 3 working AI agent projects using Claude and Python:

1. **CAMO Engineer AD Monitor** — EASA/FAA Airworthiness Directive tracking
2. **Invoice Check Engineer Agent** — MRO invoice auditing
3. **Warranty Engineer Agent** — Automated warranty claim processing

All three projects are on GitHub at: https://github.com/eminozturk1986

He codes in Python, is comfortable with Claude API, GitHub, and has a working
local environment on Windows (path: C:\Users\delye\Desktop\)

He speaks English and is learning German (B1 level). Be direct and technical.
No hand-holding needed.

---

## 📁 PROJECT: AMM-revision-engineer

### What This Project Does

Automates the work of an **AMM Revision Engineer** — the person who:
1. Reads newly published OEM AMM revisions
2. Identifies every change (new tasks, tools, materials, intervals)
3. Flags impact on Maintenance Program (MRO focus) or AMP (CAMO focus)
4. Produces a structured report for the engineering team

### Two User Contexts

**MRO Context** (Maintenance Planning Engineers):
- Focus: New tools, materials, special tests (borescope, NDT), man-hours
- Use case: Before a C-check on B737, check what the AMM revision means for the work package

**CAMO Context** (Airworthiness / Planning Engineers):
- Focus: Changed scheduled intervals vs. current AMP
- Use case: New AMM revision → does any AMP task interval need authority notification?

---

## 📂 REPOSITORY STRUCTURE (what's already done)

```
AMM-revision-engineer/
├── SKILL.md                          ✅ DONE — Main skill file for Claude Code
├── README.md                         ✅ DONE — GitHub project readme
├── references/
│   ├── parsing_guide.md              ✅ DONE — PDF/text extraction patterns
│   ├── excel_template_guide.md       ✅ DONE — openpyxl report code
│   ├── ata_chapters.md               ✅ DONE — ATA 100 chapter reference
│   └── aviation_glossary.md          ✅ DONE — MRO/CAMO terminology
├── sample_data/
│   ├── README.md                     ✅ DONE
│   ├── amm_revisions/
│   │   ├── cessna172_amm_rev15_excerpt.txt  ✅ DONE (synthetic baseline)
│   │   └── cessna172_amm_rev21_excerpt.txt  ✅ DONE (synthetic, 10 changes)
│   └── amp_excel/
│       └── sample_AMP_cessna172.xlsx        ✅ DONE (12-task AMP)
└── [everything below = YOUR JOB TO BUILD]
```

---

## 🔨 YOUR TASKS — BUILD THESE IN ORDER

### TASK 1: Create the Python Package Structure

Create this layout under the repo root:

```
amm_engineer/
├── __init__.py
├── cli.py              ← Typer CLI entrypoint
├── parser.py           ← AMM text/PDF extraction
├── differ.py           ← Old vs new revision comparison
├── classifier.py       ← Tag each change by type
├── reporter.py         ← Excel + Markdown output
├── amp_matcher.py      ← Cross-reference with AMP Excel
└── models.py           ← Pydantic data models

tests/
├── test_parser.py
├── test_differ.py
├── test_classifier.py
└── test_amp_matcher.py

requirements.txt
setup.py  (or pyproject.toml)
```

### TASK 2: Data Models (models.py)

Use Pydantic v2. Define these models:

```python
class AMMTask(BaseModel):
    ata: str                    # "32-10-00"
    task_ref: str               # "32-10-00-200-801"
    task_title: str
    interval_fh: float | None
    interval_calendar: str | None  # "12 Months", "90 Days" etc
    interval_cycles: int | None
    materials: list[str]
    tools: list[str]
    special_tests: list[str]    # ["BORESCOPE", "NDT", "PRESSURE TEST"]
    man_hours: float | None
    effectivity: str
    warnings: list[str]
    cautions: list[str]
    page_status: str            # "NEW", "REVISED", "DELETED", "UNCHANGED"
    raw_text: str               # full original text block

class AMMRevision(BaseModel):
    aircraft_type: str
    revision_number: str
    revision_date: str
    tasks: list[AMMTask]
    highlights: list[dict]      # from front-matter highlights page

class ChangeRecord(BaseModel):
    ata: str
    task_ref: str
    task_title: str
    change_type: str            # see classifier.py for all types
    old_value: str | None
    new_value: str | None
    old_interval: str | None
    new_interval: str | None
    interval_delta: str | None  # e.g. "-200 FH" or "+2 Months"
    new_materials: list[str]
    removed_materials: list[str]
    new_tools: list[str]
    special_test: str | None
    old_mh: float | None
    new_mh: float | None
    effectivity: str
    priority: str               # "HIGH", "MEDIUM", "LOW"
    action_required: str
    amp_task_match: str | None  # matched AMP task number if found
```

### TASK 3: Parser (parser.py)

Must handle THREE input formats:

**Format A: Plain text** (most important — sample_data uses this)
```python
def parse_text_amm(text: str, revision_number: str, revision_date: str) -> AMMRevision:
    """Parse AMM from extracted plain text."""
```

**Format B: PDF**
```python
def parse_pdf_amm(pdf_path: str) -> AMMRevision:
    """Parse AMM directly from PDF using pdfplumber."""
    # Try pdfplumber first, fall back to PyMuPDF if needed
    # Extract text per page, detect ATA structure
    # Detect HIGHLIGHTS section first (front matter)
    # Then detect individual task blocks by "TASK XX-XX-XX" pattern
```

**Format C: Multiple PDFs (one per ATA chapter)**
```python
def parse_chapter_pdfs(pdf_paths: list[str]) -> AMMRevision:
    """Parse AMM from multiple chapter PDFs."""
```

**Key parsing rules from the sample data structure:**
- Task blocks start with: `TASK XX-XX-XX-XXX-XXX:` pattern
- Intervals appear near: `INTERVAL:` or in table format with FH/Months/Days
- Materials appear under: `MATERIALS REQUIRED` header
- Tools appear under: `TOOLS REQUIRED` header
- Special tests detected by keywords: BORESCOPE, NDT, EDDY CURRENT,
  ULTRASONIC, MAGNETIC PARTICLE, DYE PENETRANT, PRESSURE TEST, LEAK TEST
- Man-hours appear near: `MAN-HOURS:` keyword
- Page status in LEP section: `R` = Revised, `N` = New, `D` = Deleted
- New tasks indicated by: "THIS TASK IS NEW IN REVISION" text

**Full keyword lists are in: references/parsing_guide.md**

### TASK 4: Differ (differ.py)

```python
def diff_revisions(old_rev: AMMRevision, new_rev: AMMRevision) -> list[ChangeRecord]:
    """
    Compare two AMM revisions and return list of all changes.
    
    Logic:
    1. Match tasks between revisions by task_ref (primary) or ATA+title (fallback)
    2. For each matched pair: compare all fields
    3. Tasks only in new_rev = NEW_TASK
    4. Tasks only in old_rev = DELETED_TASK  
    5. For matched tasks: detect field-level changes
    """
```

**Interval comparison logic (critical):**
```python
def compare_intervals(old: AMMTask, new: AMMTask) -> tuple[str, str] | None:
    """
    Returns (change_type, delta_description) or None if unchanged.
    
    Rules:
    - If FH reduced: INTERVAL_REDUCED (HIGH priority)
    - If calendar reduced (e.g. 90 days → 60 days): INTERVAL_REDUCED
    - If FH increased: INTERVAL_EXTENDED
    - Parse "X Months" → days for comparison
    - Parse "X FH" → float for comparison
    """
```

### TASK 5: Classifier (classifier.py)

```python
CHANGE_TYPES = [
    "NEW_TASK",           # Task added in new revision
    "DELETED_TASK",       # Task removed
    "INTERVAL_CHANGE",    # Any interval change
    "INTERVAL_REDUCED",   # Interval shorter (more restrictive) — HIGH PRIORITY
    "INTERVAL_EXTENDED",  # Interval longer
    "NEW_MATERIAL",       # New material/consumable added
    "MATERIAL_CHANGED",   # Existing material spec changed
    "NEW_TOOL",           # New special tool required
    "TOOL_CHANGED",       # Tool specification changed
    "NEW_SPECIAL_TEST",   # Borescope/NDT/pressure test added
    "MH_CHANGE",          # Man-hours estimate changed significantly (>10%)
    "EFFECTIVITY_CHANGE", # Applicability changed
    "SAFETY_NOTE",        # New WARNING or CAUTION added
    "ACCESS_CHANGE",      # New access procedure required
]

def assign_priority(change: ChangeRecord) -> str:
    """
    HIGH:   INTERVAL_REDUCED, NEW_TASK (if contains CMR/ALI keywords),
            DELETED_TASK, NEW_SPECIAL_TEST
    MEDIUM: INTERVAL_EXTENDED, NEW_MATERIAL, MATERIAL_CHANGED, 
            NEW_TOOL, MH_CHANGE (>20%)
    LOW:    SAFETY_NOTE (new caution), EFFECTIVITY_CHANGE,
            MH_CHANGE (10-20%), editorial
    """

def generate_action_text(change: ChangeRecord) -> str:
    """Generate human-readable action recommendation."""
    # E.g.: "INTERVAL_REDUCED: Update AMP task interval. 
    #        Check if authority notification required per Part-M."
```

### TASK 6: AMP Matcher (amp_matcher.py)

```python
def load_amp(excel_path: str) -> pd.DataFrame:
    """Load AMP from Excel. Column mapping flexible — detect by header names."""
    # Required columns to find (fuzzy match): 
    #   task_number, ata_ref, task_description, interval_fh, interval_calendar

def match_changes_to_amp(
    changes: list[ChangeRecord], 
    amp_df: pd.DataFrame
) -> list[ChangeRecord]:
    """
    For each ChangeRecord, find matching AMP task.
    
    Matching logic (in order of preference):
    1. Exact ATA match + interval type match
    2. Partial task description match (fuzzy, threshold 0.7)
    3. ATA chapter match only (if description too different)
    
    Add matched AMP task number to change.amp_task_match
    """

def generate_amp_impact_matrix(
    changes: list[ChangeRecord],
    amp_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Create CAMO-focused AMP impact matrix.
    
    Columns: AMP_Task_No, ATA, Current_Interval, New_AMM_Interval,
             Change_Required, Authority_Notification, Priority, Notes
    """
```

### TASK 7: Reporter (reporter.py)

Full implementation is in: **references/excel_template_guide.md**

Build from that template. The Excel report must have 6 sheets:
1. SUMMARY — counts by change type and priority
2. ALL_CHANGES — complete delta table
3. MRO_ACTION_ITEMS — tools/materials/special tests only
4. CAMO_AMP_IMPACT — interval changes vs AMP
5. NEW_TASKS — new tasks for engineering review
6. DELETED_TASKS — tasks removed from AMM

Also generate a Markdown summary file alongside the Excel.

### TASK 8: CLI Interface (cli.py)

Use Typer. These commands:

```bash
# Basic delta analysis (two text files)
amm-engineer analyze \
    --old sample_data/amm_revisions/cessna172_amm_rev15_excerpt.txt \
    --new sample_data/amm_revisions/cessna172_amm_rev21_excerpt.txt \
    --aircraft "Cessna 172" \
    --output-dir ./reports/

# With AMP matching (CAMO mode)
amm-engineer analyze \
    --old rev15.txt \
    --new rev21.txt \
    --amp sample_data/amp_excel/sample_AMP_cessna172.xlsx \
    --mode camo \
    --aircraft "Cessna 172" \
    --output-dir ./reports/

# PDF input
amm-engineer analyze \
    --old-pdf amm_old.pdf \
    --new-pdf amm_new.pdf \
    --aircraft "B737-800" \
    --output-dir ./reports/

# Single revision (no old available — just extract)
amm-engineer extract \
    --input amm_rev21.txt \
    --output-dir ./reports/
```

### TASK 9: Tests

Write pytest tests for the sample data. These tests MUST PASS:

```python
def test_parser_detects_all_tasks():
    """Rev 21 excerpt should yield at least 7 tasks."""

def test_parser_finds_new_task_marker():
    """Tasks marked 'THIS TASK IS NEW' should have page_status='NEW'."""

def test_differ_detects_interval_reduction():
    """Fuel filter 100FH→50FH must be detected as INTERVAL_REDUCED."""

def test_differ_detects_new_borescope():
    """Borescope inspection must be tagged NEW_TASK + NEW_SPECIAL_TEST."""

def test_differ_detects_material_change():
    """MIL-H-5606→MIL-PRF-5606 must be MATERIAL_CHANGED."""

def test_amp_matcher_finds_fuel_filter():
    """AMP task AMP-004 must match to the fuel filter interval change."""

def test_reporter_creates_excel():
    """Excel output must have 6 sheets."""

def test_priority_interval_reduced_is_high():
    """All INTERVAL_REDUCED changes must have priority=HIGH."""
```

### TASK 10: requirements.txt

```
pdfplumber>=0.10.0
PyMuPDF>=1.23.0
pandas>=2.0.0
openpyxl>=3.1.0
pydantic>=2.0.0
typer>=0.9.0
rich>=13.0.0
thefuzz>=0.20.0       # fuzzy string matching for AMP matcher
python-dateutil>=2.8.0
pytest>=7.0.0
pytest-cov>=4.0.0
```

---

## ✅ KNOWN CHANGES IN SAMPLE DATA (your tests must catch all of these)

These 10 changes are deliberately embedded in cessna172_amm_rev21_excerpt.txt:

| # | Change | Type | Priority |
|---|--------|------|----------|
| 1 | Fuel Filter: 100 FH → 50 FH | INTERVAL_REDUCED | HIGH |
| 2 | Battery: 90 Days → 60 Days | INTERVAL_REDUCED | HIGH |
| 3 | Engine Mount: 500 FH → 300 FH | INTERVAL_REDUCED | HIGH |
| 4 | Engine Cylinder Borescope (new task, 600 FH) | NEW_TASK + NEW_SPECIAL_TEST | HIGH |
| 5 | Wheel Bearing Repack (new task, 500 FH) | NEW_TASK | MEDIUM |
| 6 | Torque Link Lubrication (new task, 200 FH) | NEW_TASK | MEDIUM |
| 7 | Brake fluid: MIL-H-5606 → MIL-PRF-5606 | MATERIAL_CHANGED | MEDIUM |
| 8 | Borescope equipment (Olympus IPLEX SA) | NEW_TOOL | MEDIUM |
| 9 | Wheel bearing grease MIL-PRF-81322 | NEW_MATERIAL | MEDIUM |
| 10 | Annual MH: 16 → 19 hours (+3 MH) | MH_CHANGE | LOW |

These AMP tasks need updating after the analysis:
- AMP-004 (Fuel Filter): interval 100 FH → 50 FH ← authority notification needed
- AMP-005 (Battery): 90 Days → 60 Days ← authority notification needed
- AMP-008 (Engine Mount): 500 FH → 300 FH ← authority notification needed
- 3 new AMP tasks need engineering evaluation for incorporation

---

## 🎨 CODE STYLE PREFERENCES

Based on Emin's previous projects:
- Python 3.10+
- Type hints everywhere
- Pydantic models for data structures
- Pathlib for file paths (not os.path)
- Rich library for terminal output (colored, professional)
- f-strings (not .format())
- Clear docstrings on every function
- No Jupyter notebooks — pure Python scripts/modules

---

## 🚀 HOW TO START A SESSION

When Emin opens a new Claude Code session on this project, he will say something like:
- "Continue the AMM revision engineer project"
- "Build the parser module"
- "Run the tests and fix failures"

Your first action in every new session:
1. Read this HANDOVER.md
2. List what's already built (check directory structure)
3. Identify what's next in the task list
4. Start working without asking unnecessary questions

---

## 📋 SESSION LOG (update this after each session)

### Session 1 — 2026-02-28
- Created SKILL.md, README.md, references/, sample_data/
- Generated synthetic AMM excerpts (Rev 15 + Rev 21) with 10 deliberate changes
- Generated sample_AMP_cessna172.xlsx with 12 tasks and 4 aircraft fleet
- Status: Foundation complete. Next → TASK 1 (Python package structure)

### Session 2 — 2026-02-28
- Built complete amm_engineer/ Python package (7 modules: models, parser, differ, classifier, amp_matcher, reporter, cli)
- 34 pytest tests — all passing
- Fixed: TIME LIMITS table per-item diffing (fuel filter 100→50 FH, battery 90→60 Days)
- Fixed: Highlights regex for em-dash separator
- Generated index.html GitHub Pages landing page (dark aerospace / amber theme, matches Invoice Check Engineer style)
- Pushed to GitHub: github.com/eminozturk1986/AMM-revision-engineer
- Status: Complete. Enable GitHub Pages (Settings > Pages > main, root) to activate landing page.

---

## 🔗 RELATED PROJECTS (Emin's other work)

For consistency in coding style and structure, you can look at:
- https://github.com/eminozturk1986/CAMO-Engineer-AD-Monitor

That project uses similar Python structure with Claude API integration.

---

## ⚡ IMPORTANT NOTES

1. **Real AMMs are proprietary** — never hard-code Boeing/Airbus manual structure
   assumptions. The parser must be format-agnostic.

2. **INTERVAL_REDUCED is always HIGH priority** — in aviation, a shorter interval
   means the regulator (EASA) may need to approve an AMP amendment. This is a
   safety-critical flag.

3. **The AMP match is fuzzy** — airline AMP task descriptions rarely match AMM
   task titles exactly. Use fuzzy matching with clear confidence scores.

4. **Borescope = special skill required** — always flag borescope tasks as
   requiring trained personnel. This is an EASA Part-66 competency issue.

5. **Test first** — Emin values working code. Run tests after every module.
   If tests fail, fix before moving to next task.

---

END OF HANDOVER DOCUMENT
