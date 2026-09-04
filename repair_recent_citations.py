#!/usr/bin/env python3
"""Repair 2020-2025 ERA citation labels from authoritative source PDF URLs."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from era_identity import canonical_citation

DEFAULT_FILES = (
    "output/combined_2020_2025_full_classification.csv",
    "output/combined_2020_2025_binary_classification.csv",
)


def repair_file(path: Path) -> int:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if not rows or "era_citation" not in fields or "pdf_url" not in fields or "year" not in fields:
        raise ValueError(f"unexpected classification schema: {path}")

    changed = 0
    for row in rows:
        citation = canonical_citation(row.get("era_citation", ""), row.get("pdf_url", ""))
        if not citation:
            raise ValueError(f"missing canonical citation for {row.get('pdf_url', '')}")
        if not citation.startswith(f"{row['year']} NZERA "):
            raise ValueError(
                f"citation year mismatch: year={row['year']} citation={citation} url={row['pdf_url']}"
            )
        if row.get("era_citation") != citation:
            row["era_citation"] = citation
            changed += 1

    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--file", action="append", dest="files")
    args = parser.parse_args()
    root = args.root.resolve()
    total = 0
    for relative in args.files or DEFAULT_FILES:
        path = root / relative
        changed = repair_file(path)
        total += changed
        print(f"{relative}: repaired {changed} citation labels")
    print(f"total repaired citation labels: {total}")


if __name__ == "__main__":
    main()
