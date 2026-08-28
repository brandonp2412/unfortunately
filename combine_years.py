#!/usr/bin/env python3
"""Combine the 2024 audit corpus and 2025 review queue with year provenance."""
from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: Path, year: int) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["year"] = str(year)
    return rows


def write_union(path: Path, groups: list[list[dict[str, str]]]) -> int:
    rows = [row for group in groups for row in group]
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    root = Path(__file__).resolve().parent
    years = {}
    years[2024] = read_rows(root / "output" / "all_search_results.csv", 2024)
    for year in (2020, 2021, 2022, 2023, 2025):
        years[year] = read_rows(root / "years" / str(year) / "output" / "initial_extraction.csv", year)
    out = root / "output"
    n = write_union(out / "combined_2020_2025_all_results.csv", [years[y] for y in sorted(years)])
    reviewed = []
    for year in sorted(years):
        if year == 2024:
            reviewed.extend(row for row in years[year] if row.get("included_in_baseline") == "yes")
        else:
            final_path = root / "years" / str(year) / "output" / f"{year}_final_categorized.csv"
            if final_path.exists():
                reviewed.extend(read_rows(final_path, year))
    n_sub = write_union(out / "combined_2020_2025_substantive_or_review.csv", [reviewed])
    (out / "combined_2024_2025_README.md").write_text(
        f"# Combined ERA corpus\n\nRows: {n} across calendar years 2020–2025.\n\n"
        "Final binary outcomes come from operative-findings review; routing status remains available in the audit rows.\n"
    )
    print(f"combined_all={n} combined_substantive_or_review={n_sub}")


if __name__ == "__main__":
    main()
