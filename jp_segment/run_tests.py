#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from jp_segment import segment


def main() -> int:
    root = Path(__file__).resolve().parent
    expected_path = root / "resources" / "expected.json"
    if not expected_path.exists():
        print("expected.json not found; add expected test cases before running.")
        return 2
    entries = json.loads(expected_path.read_text(encoding="utf-8"))
    failures = 0
    for i, entry in enumerate(entries, 1):
        text = entry["text"]
        expected = entry["tokens"]
        actual = segment(text)
        if actual != expected:
            failures += 1
            print(f"[{i}] MISMATCH\n  text:    {text}\n  expected:{expected}\n  actual:  {actual}")
    if failures:
        print(f"FAILED: {failures} mismatches out of {len(entries)}")
        return 1
    print(f"OK: {len(entries)} cases matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
