from __future__ import annotations

import argparse


def _divider(title: str) -> str:
    # Keep logs readable in terminals and CI.
    inner = f" {title} "
    line = "═" * 72
    if len(inner) >= len(line) - 2:
        return line
    pad = len(line) - len(inner)
    left = pad // 2
    right = pad - left
    return ("═" * left) + inner + ("═" * right)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m candidate_pipeline",
        description=(
            "Candidate pipeline entrypoint.\n\n"
            "This is a placeholder scaffold included so you don't have to wire up packaging/CLI plumbing.\n"
            "Replace the placeholder behavior with your real ingestion pipeline."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Run the pipeline.")
    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "run":
        print(_divider("🧪 Candidate pipeline (PLACEHOLDER)"))
        print("⚠️  Placeholder candidate pipeline code. No files were processed.")
        print("")
        print("What to do:")
        print("- Replace this placeholder with your real ingestion + modeling pipeline.")
        print("- Ingest new files from: data/s3/{partner}/{org}/pending/")
        print("- On success, move ingested files to: data/s3/{partner}/{org}/processed/")
        print("- Write/update: output/warehouse.duckdb")
        print(_divider("End placeholder"))
        return
    raise SystemExit(2)


if __name__ == "__main__":
    main()

