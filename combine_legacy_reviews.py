#!/usr/bin/env python3
"""Combine 2010-2019 only after every year passes the human-review gate."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from validate_legacy_review import validate


ROOT = Path(__file__).resolve().parent
YEARS = range(2010, 2020)


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_union(path: Path, rows: list[dict[str, str]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    all_rows: list[dict[str, str]] = []
    for year in YEARS:
        root = ROOT / "years" / str(year)
        errors = validate(root, year)
        if errors:
            preview = "\n".join(errors[:20])
            raise SystemExit(f"{year} is not ready for combination ({len(errors)} validation errors):\n{preview}")
        rows = load(root / "output" / f"{year}_manual_review.csv")
        all_rows.extend(rows)

    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    write_union(output / "combined_2010_2019_manual_review.csv", all_rows)
    substantive = [row for row in all_rows if row.get("included_in_merits_denominator") == "yes"]
    write_union(output / "combined_2010_2019_substantive_claims.csv", substantive)

    by_year: dict[int, Counter[str]] = {}
    for year in YEARS:
        by_year[year] = Counter(
            row.get("final_outcome", "")
            for row in substantive
            if row.get("year") == str(year)
        )

    lines = [
        "# 2010-2019 manually reviewed ERA dismissal corpus",
        "",
        "Every source row in this report passed `validate_legacy_review.py`. Automated outcome hints were not accepted as final classifications.",
        "",
        "| Year | Included merits | Employee win | Employer win | Mixed/unclear |",
        "|---:|---:|---:|---:|---:|",
    ]
    for year in YEARS:
        counts = by_year[year]
        total = sum(counts.values())
        lines.append(
            f"| {year} | {total} | {counts['employee_win']} | {counts['employer_win']} | {counts['mixed_unclear']} |"
        )
    (output / "combined_2010_2019_report.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(all_rows)} reviewed rows and {len(substantive)} substantive claims")


if __name__ == "__main__":
    main()
