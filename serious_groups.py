#!/usr/bin/env python3
"""Export cross-year serious-misconduct allegation and Authority-finding groups."""
from __future__ import annotations

import csv
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    rows = []
    for year in range(2020, 2026):
        if year == 2024:
            source = root / "output" / "baseline_substantive_claims.csv"
        else:
            source = root / "years" / str(year) / "output" / f"{year}_final_categorized.csv"
        with source.open(newline="") as handle:
            for row in csv.DictReader(handle):
                row["year"] = str(year)
                if year != 2024:
                    row["review_status"] = "initial_route_not_legal_confirmation"
                else:
                    row["review_status"] = "2024_reviewed_baseline"
                rows.append(row)
    fields = ["year", "era_citation", "case_name", "pdf_url", "review_status",
              "serious_misconduct_alleged", "era_confirmed_serious_misconduct",
              "initial_outcome", "final_outcome", "outcome", "included_in_baseline"]
    out = root / "output" / "combined_serious_misconduct_groups.csv"
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
