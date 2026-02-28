"""AMM text/PDF extraction — handles plain text, single PDF, and multi-chapter PDFs."""

from __future__ import annotations

import re
from pathlib import Path

from .models import AMMRevision, AMMTask

# ---------------------------------------------------------------------------
# Keyword lists (from references/parsing_guide.md)
# ---------------------------------------------------------------------------

SPECIAL_TEST_KEYWORDS = [
    "BORESCOPE", "EDDY CURRENT", "ULTRASONIC", "MAGNETIC PARTICLE",
    "DYE PENETRANT", "NDT", "NON-DESTRUCTIVE", "PRESSURE TEST", "LEAK TEST",
]

INTERVAL_UNITS = r"(?:HOURS?|FH|FLIGHT HOURS?|CYCLES?|FC|MONTHS?|MO|DAYS?|YEARS?|ANNUAL)"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_fh(text: str) -> float | None:
    """Extract the first flight-hour number from a text string."""
    m = re.search(r"(\d[\d,]*\.?\d*)\s*(?:FH|FLIGHT HOURS?|HOURS?)\b", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _parse_calendar(text: str) -> str | None:
    """Extract calendar interval description, e.g. '90 Days', '12 Months', 'Annual'."""
    m = re.search(
        r"(\d[\d,]*\.?\d*)\s*(MONTHS?|MO|DAYS?|YEARS?)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)} {m.group(2).capitalize()}"
    if re.search(r"\bANNUAL\b", text, re.IGNORECASE):
        return "Annual"
    return None


def _parse_man_hours(text: str) -> float | None:
    """Extract man-hour value from a line."""
    m = re.search(
        r"(\d+\.?\d*)\s*(?:M[\./]?H|MAN[\s\-]?HOURS?)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        return float(m.group(1))
    return None


def _detect_special_tests(text: str) -> list[str]:
    upper = text.upper()
    found = []
    for kw in SPECIAL_TEST_KEYWORDS:
        if kw in upper:
            found.append(kw)
    return found


def _extract_list_section(lines: list[str], header_keywords: list[str]) -> list[str]:
    """
    Extract bullet/dash items from a section that starts with one of the header keywords.
    Stops when another header or empty section boundary is reached.
    """
    items: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if any(kw in upper for kw in header_keywords):
            in_section = True
            continue
        if in_section:
            # Stop on next numbered section like "3." or blank then different header
            if re.match(r"^\d+\.", stripped) and stripped:
                # New numbered section — stop if it's not a sub-item
                if not any(kw in upper for kw in header_keywords):
                    break
            if stripped.startswith("-") or stripped.startswith("*"):
                items.append(stripped.lstrip("-* ").strip())
            elif stripped and not stripped.startswith(("WARNING", "CAUTION", "NOTE")):
                # Indented continuation
                if lines.index(line) > 0:
                    items.append(stripped)
    return [i for i in items if i]


def _extract_materials(lines: list[str]) -> list[str]:
    return _extract_list_section(lines, ["MATERIALS REQUIRED", "CONSUMABLE MATERIAL"])


def _extract_tools(lines: list[str]) -> list[str]:
    return _extract_list_section(lines, ["TOOLS REQUIRED", "SPECIAL TOOL"])


def _extract_warnings_cautions(lines: list[str]) -> tuple[list[str], list[str]]:
    warnings, cautions = [], []
    for i, line in enumerate(lines):
        upper = line.strip().upper()
        if upper.startswith("WARNING"):
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if nxt:
                warnings.append(nxt)
        elif upper.startswith("CAUTION"):
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if nxt:
                cautions.append(nxt)
    return warnings, cautions


def _parse_page_status_from_lep(header_block: str) -> dict[str, str]:
    """
    Parse the LEP (List of Effective Pages) section.
    Returns dict: ata_ref -> status (NEW | REVISED | DELETED | UNCHANGED)
    """
    status_map: dict[str, str] = {}
    pattern = re.compile(
        r"(\d{2}-\d{2}-\d{2})\s+\d+\s+\S+\s+(\S+)\s*$",
        re.MULTILINE,
    )
    for m in pattern.finditer(header_block):
        ata = m.group(1)
        code = m.group(2).strip()
        if code == "R":
            status_map[ata] = "REVISED"
        elif code == "N":
            status_map[ata] = "NEW"
        elif code == "D":
            status_map[ata] = "DELETED"
        elif code == "-":
            status_map[ata] = "UNCHANGED"
    return status_map


def _parse_highlights(text: str) -> list[dict]:
    """Extract highlights section entries."""
    highlights: list[dict] = []
    pattern = re.compile(
        r"(\d{2}-\d{2}-\d{2})[,\s]+[Pp]age[s]?\s+\d+[:\s]+(NEW|REVISED|DELETED)\s*[—\u2013\u2014\-]+\s*(.+)",
        re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        highlights.append({
            "ata": m.group(1),
            "status": m.group(2).upper(),
            "description": m.group(3).strip(),
        })
    return highlights


def _split_task_blocks(text: str) -> list[tuple[str, str]]:
    """
    Split AMM text into individual task blocks.
    Returns list of (task_ref, block_text).
    """
    task_pattern = re.compile(
        r"^(?:[-]+\n)?TASK\s+([\w\-]+):\s*(.+?)$",
        re.MULTILINE,
    )
    matches = list(task_pattern.finditer(text))
    blocks: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        blocks.append((m.group(1).strip(), block))
    return blocks


def _parse_task_block(task_ref: str, block: str, lep_status: dict[str, str]) -> AMMTask:
    """Parse a single TASK block into an AMMTask."""
    lines = block.splitlines()

    # ATA from task_ref (e.g. "05-10-00-200-801" → "05-10-00")
    ata_match = re.match(r"(\d{2}-\d{2}-\d{2})", task_ref)
    ata = ata_match.group(1) if ata_match else ""

    # Task title from first TASK line
    title_match = re.match(r"TASK\s+[\w\-]+:\s*(.+)", lines[0])
    task_title = title_match.group(1).strip() if title_match else ""

    # Determine page status
    page_status = lep_status.get(ata, "UNCHANGED")
    if "THIS TASK IS NEW IN REVISION" in block.upper():
        page_status = "NEW"

    # Interval — look for explicit INTERVAL: line first, then TIME LIMITS table
    interval_fh: float | None = None
    interval_calendar: str | None = None

    interval_line_pattern = re.compile(r"INTERVAL\s*:\s*(.+)", re.IGNORECASE)
    for line in lines:
        m = interval_line_pattern.search(line)
        if m:
            raw = m.group(1)
            fh = _parse_fh(raw)
            cal = _parse_calendar(raw)
            if fh:
                interval_fh = fh
            if cal:
                interval_calendar = cal
            break

    # Also scrape inline interval annotations: "100 FH or 12 Mo" style
    if interval_fh is None:
        for line in lines:
            if re.search(r"\bINTERVAL\b|\bFLIGHT HOUR", line, re.IGNORECASE):
                fh = _parse_fh(line)
                cal = _parse_calendar(line)
                if fh and interval_fh is None:
                    interval_fh = fh
                if cal and interval_calendar is None:
                    interval_calendar = cal

    # Man-hours — pick the Annual or first listed value
    man_hours: float | None = None
    for line in lines:
        if re.search(r"\bANNUAL\b.*MH|MH.*\bANNUAL\b", line, re.IGNORECASE):
            man_hours = _parse_man_hours(line)
            if man_hours:
                break
    if man_hours is None:
        for line in lines:
            mh = _parse_man_hours(line)
            if mh:
                man_hours = mh
                break

    materials = _extract_materials(lines)
    tools = _extract_tools(lines)
    special_tests = _detect_special_tests(block)
    warnings, cautions = _extract_warnings_cautions(lines)

    return AMMTask(
        ata=ata,
        task_ref=task_ref,
        task_title=task_title,
        interval_fh=interval_fh,
        interval_calendar=interval_calendar,
        materials=materials,
        tools=tools,
        special_tests=special_tests,
        man_hours=man_hours,
        effectivity="All",
        warnings=warnings,
        cautions=cautions,
        page_status=page_status,
        raw_text=block,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_text_amm(text: str, revision_number: str = "", revision_date: str = "") -> AMMRevision:
    """
    Parse AMM from extracted plain text.

    Extracts aircraft type, revision info, highlights, LEP status, and all task blocks.
    """
    # Aircraft type and revision from header
    aircraft_type = ""
    at_match = re.search(r"CESSNA MODEL ([\w\s]+)(?:SERIES|—)", text, re.IGNORECASE)
    if at_match:
        aircraft_type = f"Cessna {at_match.group(1).strip()}"

    if not revision_number:
        rev_match = re.search(r"REVISION\s+(\d+)", text, re.IGNORECASE)
        if rev_match:
            revision_number = rev_match.group(1)

    if not revision_date:
        date_match = re.search(r"REVISION\s+\d+\s+[—\-–]\s*([\w\s/]+\d{4})", text, re.IGNORECASE)
        if date_match:
            revision_date = date_match.group(1).strip()

    highlights = _parse_highlights(text)
    lep_status = _parse_page_status_from_lep(text)

    task_blocks = _split_task_blocks(text)
    tasks: list[AMMTask] = []
    for task_ref, block in task_blocks:
        tasks.append(_parse_task_block(task_ref, block, lep_status))

    return AMMRevision(
        aircraft_type=aircraft_type,
        revision_number=revision_number,
        revision_date=revision_date,
        tasks=tasks,
        highlights=highlights,
    )


def parse_pdf_amm(pdf_path: str) -> AMMRevision:
    """
    Parse AMM directly from a PDF file using pdfplumber, falling back to PyMuPDF.
    """
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(pages)
    except Exception:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            text = "\n".join(page.get_text() for page in doc)
        except Exception as exc:
            raise RuntimeError(
                f"Cannot parse PDF '{pdf_path}'. Install pdfplumber or PyMuPDF."
            ) from exc

    return parse_text_amm(text)


def parse_chapter_pdfs(pdf_paths: list[str]) -> AMMRevision:
    """
    Parse AMM from multiple chapter PDFs (one per ATA chapter).
    Merges all chapters into a single AMMRevision.
    """
    combined_text = ""
    for path in pdf_paths:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    combined_text += (page.extract_text() or "") + "\n"
        except Exception:
            pass

    return parse_text_amm(combined_text)
