#!/usr/bin/env python3
"""Overwrite headline outcome charts with the audited binary classification."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict

from make_charts import (
    COLORS,
    OUT,
    ROOT,
    horizontal_year_chart,
    legacy_rows,
    line_chart,
    pie_chart,
)


def recent_binary_rows() -> list[dict[str, str]]:
    path = ROOT / "output" / "combined_2020_2025_binary_classification.csv"
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def outcome_rows() -> list[dict[str, str]]:
    rows = [
        {"year": row["year"], "outcome": row["final_outcome"]}
        for row in legacy_rows()
    ]
    rows.extend(
        {"year": row["year"], "outcome": row["binary_outcome"]}
        for row in recent_binary_rows()
    )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = outcome_rows()
    years = [str(year) for year in range(2010, 2026)]
    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    for row in data:
        by_year[row["year"]][row["outcome"]] += 1

    horizontal_year_chart(
        "ERA corpus rows · 2010–2025",
        years,
        {
            "included": [
                by_year[year]["employee_win"] + by_year[year]["employer_win"]
                for year in years
            ],
            "excluded": [by_year[year]["excluded"] for year in years],
        },
        OUT / "corpus_by_year.png",
    )

    horizontal_year_chart(
        "Binary outcome classification · 2010–2025",
        years,
        {
            key: [by_year[year][key] for year in years]
            for key in ("employee_win", "employer_win", "excluded")
        },
        OUT / "outcomes_by_year.png",
    )

    rates: list[float] = []
    for year in years:
        employee = by_year[year]["employee_win"]
        employer = by_year[year]["employer_win"]
        rates.append(100 * employee / (employee + employer) if employee + employer else 0)

    line_chart(
        "Employee win rate · audited binary view",
        years,
        {"employee win rate": rates},
        OUT / "employee_win_rate_by_year.png",
    )

    pie_chart(
        "Overall binary outcomes · 2010–2025",
        Counter(row["outcome"] for row in data),
        OUT / "outcome_overall_pie.png",
        COLORS,
    )
    print(f"Overwrote headline charts with audited binary outcomes in {OUT}")


if __name__ == "__main__":
    main()
