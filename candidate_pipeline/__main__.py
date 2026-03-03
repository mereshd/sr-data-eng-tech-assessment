"""Candidate pipeline CLI entrypoint.

Usage:
    python -m candidate_pipeline run
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .config import S3_ROOT
from .ingest import discover_pending_files, load_csv
from .transform import (
    apply_all_transforms,
    load_stores_mapping,
    load_uom_mapping,
    load_distributors,
)
from .quality import QualityReport, deduplicate, validate_and_flag
from .warehouse import get_connection, upsert_file

console = Console()


def _divider(title: str) -> str:
    inner = f" {title} "
    line = "=" * 72
    if len(inner) >= len(line) - 2:
        return line
    pad = len(line) - len(inner)
    left = pad // 2
    right = pad - left
    return ("=" * left) + inner + ("=" * right)


def run_pipeline() -> None:
    """Main pipeline: discover, load, transform, validate, write, move."""
    console.print(_divider("Candidate Pipeline"))

    # ── Load reference mappings ────────────────────────────────────────
    stores_mapping = load_stores_mapping()
    uom_mapping = load_uom_mapping()
    valid_distributors = load_distributors()
    console.print(f"Loaded mappings: {len(stores_mapping)//2} stores, "
                  f"{len(uom_mapping)} UOM variants, {len(valid_distributors)} distributors")

    # ── Discover pending files ─────────────────────────────────────────
    pending = discover_pending_files()
    if not pending:
        console.print("[yellow]No pending files found. Nothing to process.[/yellow]")
        console.print(_divider("Done"))
        return

    console.print(f"Found [bold]{len(pending)}[/bold] pending file(s)")

    # ── Process each file ──────────────────────────────────────────────
    conn = get_connection()
    reports: list[QualityReport] = []

    for meta in pending:
        console.print(f"\n--- Processing: [cyan]{meta.source_file}[/cyan]"
                      + (" [red][CORRECTION][/red]" if meta.is_correction else ""))
        report = QualityReport(source_file=meta.source_file)

        try:
            # Load
            df = load_csv(meta)
            report.rows_loaded = len(df)
            console.print(f"  Loaded {len(df)} rows")

            # Transform
            df = apply_all_transforms(df, stores_mapping, uom_mapping)

            # Deduplicate
            df, dupes = deduplicate(df)
            report.duplicates_removed = dupes
            report.rows_after_dedup = len(df)
            if dupes > 0:
                console.print(f"  [yellow]Removed {dupes} duplicate row(s)[/yellow]")

            # Validate and flag
            good_df, quarantine_df = validate_and_flag(df, report)

            if len(quarantine_df) > 0:
                console.print(f"  [red]Quarantined {len(quarantine_df)} row(s)[/red]")

            # Write to DuckDB
            upsert_file(conn, good_df, quarantine_df, meta.source_file,
                        meta.is_correction, dupes)
            console.print(f"  [green]Wrote {len(good_df)} rows to warehouse[/green]")

            # Move to processed
            _move_to_processed(meta.path)
            console.print(f"  Moved to processed/")

            reports.append(report)

        except Exception as e:
            console.print(f"  [red bold]ERROR: {e}[/red bold]")
            console.print(f"  File remains in pending/ for retry")
            report.rows_ingested = 0
            reports.append(report)
            continue

    conn.close()

    # ── Summary ────────────────────────────────────────────────────────
    _print_summary(reports)
    console.print(_divider("Done"))


def _move_to_processed(file_path: Path) -> None:
    """Move a file from pending/ to processed/ within the same partner/org folder."""
    processed_dir = file_path.parent.parent / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    dest = processed_dir / file_path.name
    shutil.move(str(file_path), str(dest))


def _print_summary(reports: list[QualityReport]) -> None:
    """Print a summary table of all processed files."""
    console.print("\n")
    table = Table(title="Pipeline Summary")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Loaded", justify="right")
    table.add_column("Deduped", justify="right")
    table.add_column("Quarantined", justify="right", style="red")
    table.add_column("Ingested", justify="right", style="green")

    total_loaded = total_deduped = total_quarantined = total_ingested = 0
    for r in reports:
        # Shorten file name for display
        short = r.source_file.split("/")[-1] if "/" in r.source_file else r.source_file
        table.add_row(
            short,
            str(r.rows_loaded),
            str(r.duplicates_removed),
            str(r.rows_quarantined),
            str(r.rows_ingested),
        )
        total_loaded += r.rows_loaded
        total_deduped += r.duplicates_removed
        total_quarantined += r.rows_quarantined
        total_ingested += r.rows_ingested

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_loaded}[/bold]",
        f"[bold]{total_deduped}[/bold]",
        f"[bold]{total_quarantined}[/bold]",
        f"[bold]{total_ingested}[/bold]",
    )
    console.print(table)

    # Print quality flags
    all_flags: dict[str, int] = {}
    for r in reports:
        for k, v in r.flags.items():
            all_flags[k] = all_flags.get(k, 0) + v
    if all_flags:
        console.print("\n[bold]Quality flags:[/bold]")
        for flag, count in sorted(all_flags.items()):
            console.print(f"  {flag}: {count}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m candidate_pipeline",
        description="Invoice ingestion pipeline for Sightline OS.",
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Run the pipeline.")
    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "run":
        run_pipeline()
        return
    raise SystemExit(2)


if __name__ == "__main__":
    main()
