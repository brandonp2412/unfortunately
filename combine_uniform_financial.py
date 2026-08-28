#!/usr/bin/env python3
"""Combine per-year uniform financial scoring and surface only cases needing judgment."""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_SUBSTANTIVE = 3046  # 2,373 (2010-2019) + 673 (2020-2025)


def load_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in range(2010, 2026):
        path = root / "output" / "uniform_financial" / f"{year}.csv"
        if not path.exists():
            raise SystemExit(f"missing {path}")
        rows.extend(csv.DictReader(path.open(newline="")))
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    rows = load_rows(root)

    if len(rows) != EXPECTED_SUBSTANTIVE:
        raise SystemExit(f"expected {EXPECTED_SUBSTANTIVE} substantive rows, got {len(rows)}")
    urls = [row["pdf_url"] for row in rows]
    if len(set(urls)) != len(urls):
        raise SystemExit("duplicate substantive PDF URLs in uniform financial output")
    if any(row["financial_binary_outcome"] not in {"employee_win", "employer_win"} for row in rows):
        raise SystemExit("non-binary financial outcome found")

    write_csv(root / "output" / "uniform_financial_2010_2025.csv", rows)

    audit = [row for row in rows if row.get("parser_audit_reason")]
    audit_fields = [
        "year", "era_citation", "case_name", "legal_outcome", "financial_binary_outcome",
        "employee_money_awarded", "employee_money_adverse", "observable_net_money",
        "positive_money_signal", "negative_money_signal", "both_sides_money",
        "unallocated_money_units", "parser_audit_reason", "prior_financial_audit",
        "financial_evidence", "unallocated_money_evidence", "order_excerpt", "pdf_url",
    ]
    write_csv(root / "output" / "uniform_financial_audit_queue.csv", audit, audit_fields)

    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_year[row["year"]][row["financial_binary_outcome"]] += 1
    summary: list[dict[str, str]] = []
    total = Counter()
    for year in range(2010, 2026):
        counts = by_year[str(year)]
        n = counts["employee_win"] + counts["employer_win"]
        total.update(counts)
        summary.append({
            "year": str(year),
            "substantive_cases": str(n),
            "employee_wins": str(counts["employee_win"]),
            "employer_wins": str(counts["employer_win"]),
            "employee_win_rate": f"{100 * counts['employee_win'] / n:.1f}" if n else "0.0",
        })
    n = total["employee_win"] + total["employer_win"]
    summary.append({
        "year": "2010-2025",
        "substantive_cases": str(n),
        "employee_wins": str(total["employee_win"]),
        "employer_wins": str(total["employer_win"]),
        "employee_win_rate": f"{100 * total['employee_win'] / n:.1f}",
    })
    write_csv(
        root / "output" / "uniform_financial_summary.csv",
        summary,
        ["year", "substantive_cases", "employee_wins", "employer_wins", "employee_win_rate"],
    )

    clear = len(rows) - len(audit)
    progress = (
        f"total_substantive={len(rows)}\n"
        f"mechanically_clear_or_prior_audited={clear}\n"
        f"direct_audit_remaining={len(audit)}\n"
        f"progress_percent={100 * clear / len(rows):.2f}\n"
    )
    (root / "output" / "uniform_financial_progress.txt").write_text(progress)
    print(progress, end="", flush=True)
    print("provisional totals", dict(total), flush=True)


if __name__ == "__main__":
    main()
