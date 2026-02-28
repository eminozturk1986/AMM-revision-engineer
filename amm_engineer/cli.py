"""Typer CLI entrypoint for AMM Revision Engineer."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .amp_matcher import load_amp, match_changes_to_amp
from .differ import diff_revisions
from .parser import parse_pdf_amm, parse_text_amm
from .reporter import create_excel_report, create_markdown_report

app = typer.Typer(
    name="amm-engineer",
    help="AMM Revision Engineer — automated delta analysis for MRO and CAMO.",
    add_completion=False,
)
console = Console()


def _load_revision(text_path: Optional[str], pdf_path: Optional[str], label: str):
    """Load an AMM revision from text or PDF path."""
    if text_path:
        p = Path(text_path)
        if not p.exists():
            console.print(f"[red]File not found: {text_path}[/red]")
            raise typer.Exit(1)
        text = p.read_text(encoding="utf-8", errors="replace")
        return parse_text_amm(text)
    elif pdf_path:
        p = Path(pdf_path)
        if not p.exists():
            console.print(f"[red]PDF not found: {pdf_path}[/red]")
            raise typer.Exit(1)
        return parse_pdf_amm(str(p))
    else:
        console.print(f"[red]No {label} file specified. Use --old/--new or --old-pdf/--new-pdf.[/red]")
        raise typer.Exit(1)


@app.command("analyze")
def analyze(
    old: Optional[str] = typer.Option(None, help="Old AMM revision — plain text file"),
    new: Optional[str] = typer.Option(None, help="New AMM revision — plain text file"),
    old_pdf: Optional[str] = typer.Option(None, help="Old AMM revision — PDF file"),
    new_pdf: Optional[str] = typer.Option(None, help="New AMM revision — PDF file"),
    amp: Optional[str] = typer.Option(None, help="AMP Excel file for CAMO matching"),
    aircraft: str = typer.Option("Unknown Aircraft", help="Aircraft type identifier"),
    mode: str = typer.Option("both", help="Analysis mode: mro | camo | both"),
    output_dir: str = typer.Option("./reports", help="Output directory for reports"),
):
    """
    Analyze the delta between two AMM revisions.

    Examples:

    \b
    # Text files
    amm-engineer analyze --old rev15.txt --new rev21.txt --aircraft "Cessna 172"

    \b
    # With AMP matching (CAMO mode)
    amm-engineer analyze --old rev15.txt --new rev21.txt \\
        --amp sample_AMP.xlsx --mode camo --aircraft "Cessna 172"

    \b
    # PDF input
    amm-engineer analyze --old-pdf old.pdf --new-pdf new.pdf --aircraft "B737-800"
    """
    console.print(Panel.fit(
        "[bold cyan]AMM Revision Engineer[/bold cyan]\n"
        "[dim]Automated delta analysis for MRO and CAMO[/dim]",
        border_style="cyan",
    ))

    # --- Load revisions ---
    with console.status("[bold]Parsing old revision...", spinner="dots"):
        old_rev = _load_revision(old, old_pdf, "old")
    console.print(f"[green]Old revision:[/green] Rev {old_rev.revision_number} "
                  f"— {len(old_rev.tasks)} tasks")

    with console.status("[bold]Parsing new revision...", spinner="dots"):
        new_rev = _load_revision(new, new_pdf, "new")
    console.print(f"[green]New revision:[/green] Rev {new_rev.revision_number} "
                  f"— {len(new_rev.tasks)} tasks")

    # Use aircraft from CLI flag (override parsed value if provided)
    if aircraft != "Unknown Aircraft":
        new_rev.aircraft_type = aircraft
        old_rev.aircraft_type = aircraft

    # --- Diff ---
    with console.status("[bold]Running delta analysis...", spinner="dots"):
        changes = diff_revisions(old_rev, new_rev)

    # --- AMP matching (optional) ---
    if amp:
        amp_path = Path(amp)
        if not amp_path.exists():
            console.print(f"[yellow]Warning: AMP file not found: {amp}[/yellow]")
        else:
            with console.status("[bold]Matching changes to AMP...", spinner="dots"):
                amp_df = load_amp(str(amp_path))
                changes = match_changes_to_amp(changes, amp_df)
            console.print(f"[green]AMP loaded:[/green] {len(amp_df)} tasks")

    # --- Print results summary ---
    _print_summary(changes)

    # --- Generate reports ---
    out_dir = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_path = out_dir / f"AMM_Delta_{timestamp}.xlsx"
    md_path = out_dir / f"AMM_Delta_{timestamp}.md"

    amm_info = {
        "aircraft": aircraft,
        "old_rev": old_rev.revision_number or "?",
        "new_rev": new_rev.revision_number or "?",
        "date": datetime.now().strftime("%d %b %Y"),
    }

    with console.status("[bold]Generating Excel report...", spinner="dots"):
        xlsx = create_excel_report(changes, str(excel_path), amm_info)
    with console.status("[bold]Generating Markdown summary...", spinner="dots"):
        md = create_markdown_report(changes, amm_info, str(md_path))

    console.print(f"\n[bold green]Reports saved:[/bold green]")
    console.print(f"  Excel : {xlsx}")
    console.print(f"  Markdown: {md}")


@app.command("extract")
def extract(
    input_file: str = typer.Option(..., "--input", help="AMM text or PDF file to extract"),
    output_dir: str = typer.Option("./reports", help="Output directory"),
    aircraft: str = typer.Option("Unknown Aircraft", help="Aircraft type"),
):
    """
    Extract structured data from a single AMM revision (no diff).
    Useful when only one revision is available.
    """
    console.print(Panel.fit("[bold cyan]AMM Revision Engineer — Extract[/bold cyan]"))

    p = Path(input_file)
    if not p.exists():
        console.print(f"[red]File not found: {input_file}[/red]")
        raise typer.Exit(1)

    if p.suffix.lower() == ".pdf":
        rev = parse_pdf_amm(str(p))
    else:
        text = p.read_text(encoding="utf-8", errors="replace")
        rev = parse_text_amm(text)

    console.print(f"[green]Parsed:[/green] {len(rev.tasks)} tasks from "
                  f"Rev {rev.revision_number}")

    table = Table(title="Extracted Tasks", show_lines=True)
    table.add_column("ATA", style="cyan", width=12)
    table.add_column("Task Ref", width=22)
    table.add_column("Title", width=40)
    table.add_column("Interval FH", justify="right", width=12)
    table.add_column("Calendar", width=14)
    table.add_column("Status", width=10)

    for t in rev.tasks:
        table.add_row(
            t.ata,
            t.task_ref,
            t.task_title[:38],
            str(t.interval_fh or ""),
            t.interval_calendar or "",
            t.page_status,
        )

    console.print(table)


def _print_summary(changes) -> None:
    """Print a Rich summary table to the terminal."""
    from collections import Counter
    ct_counts = Counter(c.change_type for c in changes)
    prio_counts = Counter(c.priority for c in changes)

    table = Table(title=f"Delta Analysis — {len(changes)} changes detected", show_lines=True)
    table.add_column("Change Type", style="bold", width=24)
    table.add_column("Count", justify="right", width=8)

    priority_styles = {"HIGH": "bold red", "MEDIUM": "bold yellow", "LOW": "bold green"}
    change_style = {
        "INTERVAL_REDUCED": "red",
        "NEW_TASK": "green",
        "DELETED_TASK": "red",
        "NEW_SPECIAL_TEST": "yellow",
    }

    for ct, count in sorted(ct_counts.items()):
        table.add_row(ct, str(count), style=change_style.get(ct, ""))

    console.print(table)

    for prio in ("HIGH", "MEDIUM", "LOW"):
        count = prio_counts.get(prio, 0)
        console.print(
            f"  [{priority_styles[prio]}]{prio}[/{priority_styles[prio]}]: "
            f"{count} changes"
        )


if __name__ == "__main__":
    app()
