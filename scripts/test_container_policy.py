#!/usr/bin/env python3
"""Verify that forbidden container changes are rejected."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_violation(label, filename, old, new):
    path = ROOT / filename
    original = path.read_bytes()
    content = original.decode("utf-8")

    if content.count(old) != 1:
        print(f"[ERROR] Cannot find unique target: {label}")
        return False

    try:
        path.write_text(content.replace(old, new, 1))

        result = subprocess.run(
            ["make", "container-check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        rejected = result.returncode != 0
        print(f"\nTEST: {label}")
        print(f"Exit code: {result.returncode}")

        failures = [
            line for line in result.stdout.splitlines()
            if "[FAIL]" in line or line.startswith("FAILED:")
        ]

        for line in failures:
            print(line)

        if rejected:
            print("[PASS] Unsafe change was rejected")
        else:
            print("[FAIL] Unsafe change was accepted")

        return rejected
    finally:
        path.write_bytes(original)


def main():
    tests = [
        (
            "Forbidden latest image",
            "compose.yaml",
            "postgres:17.6-bookworm@sha256:",
            "postgres:latest@sha256:",
        ),
        (
            "Published database port",
            "compose.yaml",
            "    healthcheck:\n      test: [\"CMD-SHELL\"",
            "    ports:\n      - \"5432:5432\"\n    healthcheck:\n      test: [\"CMD-SHELL\"",
        ),
        (
            "Disabled database healthcheck",
            "compose.yaml",
            "    healthcheck:\n      test: [\"CMD-SHELL\"",
            "    healthcheck:\n      disable: true\n      test: [\"CMD-SHELL\"",
        ),
        (
            "Root application user",
            "Dockerfile",
            "USER 10001:10001",
            "USER root",
        ),
    ]

    results = [
        test_violation(*test)
        for test in tests
    ]

    print("\n=== POLICY REJECTION SUMMARY ===")
    print(f"Rejected: {sum(results)}/{len(results)}")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
