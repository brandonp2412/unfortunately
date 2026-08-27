#!/usr/bin/env python3
"""Assemble incrementally reviewed batch CSVs into the canonical year ledger."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from create_legacy_review_template import REVIEW_FIELDS
from validate_legacy_review import validate


SOURCE_FIELDS = {"year", "search_result_number", "era_citation", "case_name", "decision_date", "pdf_url"}


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def assemble(root: Path, year: int, require_complete: bool = False) -> Path:
    brief_path = root / "output" / f"{year}_review_brief.csv"
    brief = load(brief_path)
    source_by_number = {row["search_result_number"]: row for row in brief}

    reviewed_by_number: dict[str, dict[str, str]] = {}
    for path in sorted((root / "review_batches").glob("*.csv")):
        for row in load(path):
            number = row.get("search_result_number", "").strip()
            if not number:
                raise SystemExit(f"{path}: row missing search_result_number")
            if number not in source_by_number:
                raise SystemExit(f"{path}: unknown search_result_number {number}")
            if number in reviewed_by_number:
                raise SystemExit(f"duplicate reviewed search_result_number {number} in {path}")
            reviewed_by_number[number] = row

    assembled: list[dict[str, str]] = []
    for source in brief:
        number = source["search_result_number"]
        reviewed = reviewed_by_number.get(number)
        if reviewed is None:
            continue
        out = {field: "" for field in REVIEW_FIELDS}
        for field in SOURCE_FIELDS:
            out[field] = source.get(field, "")
        for field in REVIEW_FIELDS:
            if field not in SOURCE_FIELDS and field in reviewed:
                out[field] = reviewed.get(field, "")
        assembled.append(out)

    target = root / "output" / f"{year}_manual_review.csv"
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(assembled)

    print(f"{year}: assembled {len(assembled)} of {len(brief)} review rows")
    if require_complete:
        if len(assembled) != len(brief):
            raise SystemExit(f"{year}: {len(brief) - len(assembled)} determinations remain unreviewed")
        errors = validate(root, year)
        if errors:
            for error in errors:
                print(error)
            raise SystemExit(f"{year}: review validation failed with {len(errors)} error(s)")
        print(f"{year}: complete review passed validation")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    assemble(args.root, args.year, args.require_complete)
