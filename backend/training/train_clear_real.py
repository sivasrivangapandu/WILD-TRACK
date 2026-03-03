"""
WildTrackAI strict training runner
=================================
One command to:
1) build strict clear-image dataset
2) train v4 model against strict dataset
3) enforce target accuracy (optional)

Usage:
    python train_clear_real.py
    python train_clear_real.py --target-accuracy 0.80 --enforce-target
    python train_clear_real.py --dry-run-filter
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def run(cmd, cwd):
    print("\n$ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(cmd)}")


def main():
    parser = argparse.ArgumentParser(description="Strict clean-image training pipeline")
    parser.add_argument("--target-accuracy", type=float, default=0.80)
    parser.add_argument("--enforce-target", action="store_true")
    parser.add_argument("--progressive", action="store_true")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--tta", type=int, default=None)
    parser.add_argument("--dry-run-filter", action="store_true")
    parser.add_argument("--min-blur", type=float, default=50.0)
    parser.add_argument("--min-entropy", type=float, default=3.2)
    parser.add_argument("--garbage-threshold", type=float, default=85.0)
    args = parser.parse_args()

    training_dir = Path(__file__).resolve().parent
    backend_dir = training_dir.parent
    strict_filter_script = backend_dir / "strict_filter_dataset.py"
    train_script = training_dir / "train_v4.py"
    strict_dataset_dir = backend_dir / "dataset_strict"

    filter_cmd = [
        sys.executable,
        str(strict_filter_script),
        "--source", str(backend_dir / "dataset_cleaned"),
        "--output", str(strict_dataset_dir),
        "--quarantine", str(backend_dir / "dataset_quarantine_strict"),
        "--min-blur", str(args.min_blur),
        "--min-entropy", str(args.min_entropy),
        "--garbage-threshold", str(args.garbage_threshold),
    ]
    if args.dry_run_filter:
        filter_cmd.append("--dry-run")

    run(filter_cmd, cwd=str(backend_dir))

    if args.dry_run_filter:
        print("\nDry-run filter complete. Training skipped.")
        return

    train_cmd = [
        sys.executable,
        str(train_script),
        "--dataset", str(strict_dataset_dir),
        "--target-accuracy", str(args.target_accuracy),
    ]

    if args.enforce_target:
        train_cmd.append("--enforce-target")
    if args.progressive:
        train_cmd.append("--progressive")
    if args.epochs:
        train_cmd.extend(["--epochs", str(args.epochs)])
    if args.batch:
        train_cmd.extend(["--batch", str(args.batch)])
    if args.tta:
        train_cmd.extend(["--tta", str(args.tta)])

    run(train_cmd, cwd=str(training_dir))
    print("\nStrict training complete.")


if __name__ == "__main__":
    main()
