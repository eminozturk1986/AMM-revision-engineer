# AMM Parsing Guide

## AMM Document Structure (ATA iSpec 2200)

A standard AMM revision package contains:

```
Front Matter:
  - Title Page (revision number, date, aircraft type)
  - Highlights (list of changed ATA chapters with reason codes)
  - List of Effective Pages (LEP) — NEW / REVISED / DELETED markers
  - Record of Revisions
  - Record of Temporary Revisions (TRs)

Body Chapters (ATA 05 → ATA 92):
  Each chapter → Section → Subject
  e.g. 32-10-00 = ATA 32 (Landing Gear) → Section 10 (Main Gear) → Subject 00

Each task/page block:
  - Page number with code: 201 (maintenance practices), 401 (removal), 801 (test)
  - Effectivity statement
  - REFERENCES section (tools, materials, other AMM tasks)
  - EQUIPMENT section (special tools, consumables)
  - MATERIALS section (parts, fluids, sealants)
  - PROCEDURE (numbered steps)
```

## Revision Identification Patterns

### From the LEP (List of Effective Pages)
```
Pattern: <Chapter>-<Section>-<Subject>  <Page>  <Date>  <Status>
Example:
  32-10-00  201  Jun 1/2024  R   ← REVISED
  32-10-00  202  Jun 1/2024  N   ← NEW
  32-10-00  203  Dec 1/2023  -   ← unchanged
  32-10-00  204  (deleted)       ← DELETED
```

### From Highlights Page
```
Pattern: Chapter listing with reason codes
Example:
  ATA 32 — Landing Gear
    32-10-00, Page 201: REVISED — New borescope inspection added
    32-10-00, Page 202: NEW — Added corrosion inspection task
```

### Change Bars in Page Margins
- Vertical bar `|` in left/right margin = changed content on that line
- "R" or asterisk in header/footer = revised page

## Python Extraction Patterns

### Extract Highlights with pdfplumber
```python
import pdfplumber
import re

def extract_highlights(pdf_path: str) -> list[dict]:
    """Extract AMM highlights section."""
    changes = []
    highlight_pattern = re.compile(
        r'(ATA\s+\d{2}|Chapter\s+\d{2})',
        re.IGNORECASE
    )
    task_pattern = re.compile(
        r'(\d{2}-\d{2}-\d{2})[,\s]+[Pp]age[s]?\s+(\d+)[:\s]+(NEW|REVISED|DELETED)[—–-]\s*(.+)',
        re.IGNORECASE
    )
    
    with pdfplumber.open(pdf_path) as pdf:
        in_highlights = False
        for page in pdf.pages:
            text = page.extract_text() or ''
            if 'HIGHLIGHTS' in text.upper():
                in_highlights = True
            if in_highlights:
                for match in task_pattern.finditer(text):
                    changes.append({
                        'ata': match.group(1),
                        'page': match.group(2),
                        'status': match.group(3).upper(),
                        'description': match.group(4).strip()
                    })
    return changes
```

### Extract Materials from Task
```python
MATERIAL_KEYWORDS = [
    'MATERIAL', 'CONSUMABLE', 'PART NUMBER', 'P/N', 'SPECIFICATION',
    'SEALANT', 'LUBRICANT', 'FLUID', 'ADHESIVE', 'PRIMER'
]
TOOL_KEYWORDS = [
    'SPECIAL TOOL', 'EQUIPMENT', 'TOOL NUMBER', 'T.N.', 'GSE',
    'FIXTURE', 'BORESCOPE', 'EDDY CURRENT', 'ULTRASONIC', 'NDT'
]
INTERVAL_KEYWORDS = [
    'HOURS', 'CYCLES', 'MONTHS', 'DAYS', 'FLIGHT HOURS', 'FH', 'FC',
    'CALENDAR', 'ANNUAL', 'WHICHEVER COMES FIRST'
]

def extract_task_data(task_text: str) -> dict:
    """Extract structured data from a single AMM task block."""
    result = {
        'materials': [],
        'tools': [],
        'special_tests': [],
        'interval': None,
        'man_hours': None,
        'warnings': [],
        'cautions': []
    }
    
    lines = task_text.splitlines()
    
    for i, line in enumerate(lines):
        upper = line.upper()
        
        # Interval detection
        if any(kw in upper for kw in INTERVAL_KEYWORDS):
            interval_match = re.search(
                r'(\d[\d,]*\.?\d*)\s*(HOURS?|FH|CYCLES?|FC|MONTHS?|DAYS?|YEARS?)',
                upper
            )
            if interval_match:
                result['interval'] = f"{interval_match.group(1)} {interval_match.group(2)}"
        
        # Special test detection
        if any(kw in upper for kw in ['BORESCOPE', 'EDDY CURRENT', 'ULTRASONIC', 
                                       'MAGNETIC PARTICLE', 'DYE PENETRANT', 'NDT',
                                       'NON-DESTRUCTIVE', 'PRESSURE TEST', 'LEAK TEST']):
            result['special_tests'].append(line.strip())
        
        # Man-hours
        mh_match = re.search(r'(\d+\.?\d*)\s*M[\./]?H|MAN[\s-]?HOUR', upper)
        if mh_match:
            result['man_hours'] = float(mh_match.group(1))
        
        # Warnings and cautions
        if upper.strip().startswith('WARNING'):
            result['warnings'].append(lines[i+1].strip() if i+1 < len(lines) else '')
        if upper.strip().startswith('CAUTION'):
            result['cautions'].append(lines[i+1].strip() if i+1 < len(lines) else '')
    
    return result
```

## Handling Different AMM Source Formats

### Format 1: Plain Text (extracted from PDF)
- Most common for processing
- Use regex patterns above
- Watch for OCR errors in old documents

### Format 2: XML/SGML (S1000D or ATA iSpec 2200 native)
- Modern Boeing/Airbus documents
- Use XML parsers (lxml, BeautifulSoup)
- Tags: `<task>`, `<para>`, `<reqequip>`, `<reqmat>`, `<interval>`

### Format 3: HTML (browser-based portals like Airbus AIRNav, Boeing TechOps)
- Use web scraping only if authorized
- BeautifulSoup for parsing

### Format 4: SGML (legacy)
- Convert with `osgml` or `opensp` tools
- Or treat as near-XML with cleanup

## Cessna 172 AMM Public Sources

For testing, the Cessna 172 AMM is available in multiple revisions:

- **Revision 15** (Dec 1996): https://pdfcoffee.com/cessna-172-maintenance-manual-pdf-free.html
- **Revision 21** (Jul 2007): ManualsLib — search "Cessna 172 Series 1996"
- **Inspection Tables**: NTSB document library has excerpts with temporal revisions
  URL: https://data.ntsb.gov/Docket/Document/docBLOB?ID=16480019&FileExtension=pdf

**Alternatively, use the included sample_data/ synthetic AMM excerpts** which
simulate realistic changes without copyright concerns.
