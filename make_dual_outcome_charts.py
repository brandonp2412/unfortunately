#!/usr/bin/env python3
"""Generate public charts with legal and monetary outcomes kept separate."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from make_charts import COLORS, OUT, horizontal_year_chart, line_chart, pie_chart

ROOT = Path(__file__).resolve().parent
HEADLINE = ROOT / "output" / "headline"
YEARS = [str(year) for year in range(2010, 2026)]


def rows(name: str) -> list[dict[str, str]]:
    with (HEADLINE / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def by_year(summary: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["year"]: row for row in summary if row["year"] != "2010-2025"}


def outcome_charts(title_prefix: str, summary_name: str, file_prefix: str) -> None:
    summary = rows(summary_name)
    annual = by_year(summary)
    total = summary[-1]

    horizontal_year_chart(
        f"{title_prefix} outcomes · 2010–2025",
        YEARS,
        {
            "employee_win": [int(annual[year]["employee_wins"]) for year in YEARS],
            "employer_win": [int(annual[year]["employer_wins"]) for year in YEARS],
        },
        OUT / f"{file_prefix}_outcomes_by_year.png",
    )
    line_chart(
        f"{title_prefix} employee win rate · 2010–2025",
        YEARS,
        {
            f"{title_prefix.lower()} employee win rate": [
                float(annual[year]["employee_win_rate"] or 0) for year in YEARS
            ]
        },
        OUT / f"{file_prefix}_employee_win_rate_by_year.png",
        label_all_points=True,
    )
    pie_chart(
        f"{title_prefix} outcomes · 2010–2025",
        Counter({
            "employee_win": int(total["employee_wins"]),
            "employer_win": int(total["employer_wins"]),
        }),
        OUT / f"{file_prefix}_outcome_overall_pie.png",
        COLORS,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    outcome_charts("Legal merits", "legal_outcome_summary.csv", "legal")
    outcome_charts("Monetary", "monetary_outcome_summary.csv", "monetary")

    comparison = by_year(rows("legal_vs_monetary_summary.csv"))
    line_chart(
        "Legal vs monetary employee win rate · paired cases",
        YEARS,
        {
            "legal merits": [
                float(comparison[year]["legal_employee_win_rate"] or 0) for year in YEARS
            ],
            "monetary outcome": [
                float(comparison[year]["monetary_employee_win_rate"] or 0) for year in YEARS
            ],
        },
        OUT / "legal_vs_monetary_win_rate_by_year.png",
    )
    print(f"Wrote dual-outcome charts to {OUT}")


if __name__ == "__main__":
    main()
