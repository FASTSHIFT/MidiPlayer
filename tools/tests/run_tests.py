#!/usr/bin/env python3
"""
MidiPlayer Python test runner.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py coverage     # Run with coverage report
    python run_tests.py coverage -v  # Verbose + coverage
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(SCRIPT_DIR)


def main():
    os.chdir(TOOLS_DIR)

    args = sys.argv[1:]
    use_coverage = "coverage" in args
    verbose = "-v" in args

    cmd = [sys.executable, "-m", "pytest", "tests/"]

    if verbose:
        cmd.append("-v")

    if use_coverage:
        cmd.extend(
            [
                "--cov=player",
                "--cov-report=term-missing",
                "--cov-report=html:tests/htmlcov",
            ]
        )

    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {TOOLS_DIR}")
    print()

    result = subprocess.run(cmd, cwd=TOOLS_DIR)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
