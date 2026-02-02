from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _project_root() -> Path:
    # sr-data-eng-tech-assessment/scaffolding/transfer_input_to_s3.py -> project root
    return Path(__file__).resolve().parents[1]


def transfer(raw_input: str, append: bool) -> None:
    started = time.time()
    project_root = _project_root()
    raw_inputs_root = project_root / "data" / "raw_inputs"
    s3_root = project_root / "data" / "s3"

    source_root = raw_inputs_root / raw_input
    if not source_root.exists() or not source_root.is_dir():
        raise SystemExit(
            f"raw_input not found: {source_root}\n"
            f"Expected a folder under: {raw_inputs_root}\n"
            f"Example: --raw_input raw_input_20260123"
        )

    if not append and s3_root.exists():
        shutil.rmtree(s3_root)

    copied = 0
    for src in sorted(source_root.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(source_root)
        # Files “arrive” to: data/s3/{partner}/{org}/pending/<file>.csv
        dst = s3_root / rel.parent / "pending" / rel.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    total = 0
    if s3_root.exists():
        total = sum(1 for p in s3_root.rglob("*") if p.is_file())

    divider = "═" * 72
    print(divider)
    print("🚚 Transfer raw input → simulated S3 (scaffolding)")
    print(f"📥 Raw input bundle: {raw_input}")
    print(f"🪣 S3 root: {s3_root}")
    print(f"➕ Append mode: {append}")
    print(f"📄 Files copied (this run): {copied}")
    print(f"📦 Total files in S3 (after copy): {total}")
    print(divider)
    sys.stdout.flush()

    # After files “arrive”, immediately trigger the candidate pipeline entrypoint.
    # Candidates are expected to replace the placeholder implementation.
    print("▶️  Triggering pipeline: `python -m candidate_pipeline run`")
    sys.stdout.flush()
    proc = subprocess.run(
        [sys.executable, "-m", "candidate_pipeline", "run"], cwd=str(project_root)
    )
    if proc.returncode != 0:
        print(f"❌ Pipeline exited non-zero (exit_code={proc.returncode})")
        raise SystemExit(proc.returncode)
    elapsed_ms = int((time.time() - started) * 1000)
    print(f"✅ Done (elapsed={elapsed_ms}ms)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m scaffolding.transfer_input_to_s3",
        description=(
            "Copy a raw input bundle into the simulated S3 workspace and trigger the pipeline.\n\n"
            "This is assessment scaffolding (not the take-home)."
        ),
        epilog=(
            "Examples:\n"
            "  python -m scaffolding.transfer_input_to_s3 --raw_input raw_input_20260123\n"
            "  python -m scaffolding.transfer_input_to_s3 --raw_input raw_input_20260124 --append\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--raw_input",
        required=True,
        help="Which raw input folder to apply (e.g. raw_input_20260123).",
    )
    p.add_argument(
        "--append",
        action="store_true",
        help="Append into existing simulated S3 workspace instead of clearing it first.",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    transfer(raw_input=args.raw_input, append=bool(args.append))


if __name__ == "__main__":
    main()

