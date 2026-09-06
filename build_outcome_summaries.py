#!/usr/bin/env python3
"""Build canonical, separate legal-merits and monetary-outcome summaries."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

BINARY = {"employee_win", "employer_win"}
YEARS = tuple(str(year) for year in range(2010, 2026))
DIRECT_REVIEW_STATUS = "direct_agent_source_review"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def _unique_by_url(rows: list[dict[str, str]], label: str) -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    for row in rows:
        url = row.get("pdf_url", "").strip()
        if not url:
            raise ValueError(f"{label} row has no pdf_url")
        if url in seen:
            raise ValueError(f"duplicate {label} pdf_url: {url}")
        seen[url] = row
    return list(seen.values())


def direct_review_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in range(2020, 2026):
        path = root / "years" / str(year) / "output" / f"{year}_direct_legal_reviews.csv"
        if not path.exists():
            continue
        for row in read_csv(path):
            url = row.get("pdf_url", "").strip()
            if not url:
                raise ValueError(f"direct review row has no pdf_url in {path}")
            if row.get("review_status") != DIRECT_REVIEW_STATUS:
                raise ValueError(f"direct review lacks required status for {url}")
            included = row.get("included_in_merits_denominator", "")
            outcome = row.get("legal_outcome", "")
            if included not in {"yes", "no"}:
                raise ValueError(f"invalid direct-review inclusion {included!r} for {url}")
            if included == "yes" and outcome not in BINARY:
                raise ValueError(f"included direct review lacks binary legal outcome for {url}")
            if included == "no" and outcome != "excluded":
                raise ValueError(f"excluded direct review must use legal_outcome=excluded for {url}")
            if not row.get("supporting_quote_or_paragraph", "").strip():
                raise ValueError(f"direct review lacks supporting source text for {url}")
            if row.get("confidence") not in {"high", "medium"}:
                raise ValueError(f"direct review lacks valid confidence for {url}")
            rows.append({**row, "year": str(year), "source": str(path.relative_to(root))})
    return _unique_by_url(rows, "direct legal review")


def legal_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    legacy_path = root / "output" / "combined_2010_2019_strict_classification.csv"
    for row in read_csv(legacy_path):
        outcome = row.get("final_outcome", "")
        if row.get("included_in_merits_denominator") == "yes" and outcome in BINARY:
            rows.append({
                "year": row["year"],
                "era_citation": row.get("era_citation", ""),
                "case_name": row.get("case_name", ""),
                "pdf_url": row["pdf_url"],
                "outcome": outcome,
                "source": str(legacy_path.relative_to(root)),
            })

    recent_path = root / "output" / "combined_2020_2025_binary_classification.csv"
    for row in read_csv(recent_path):
        outcome = row.get("original_legal_outcome", "")
        if outcome not in BINARY and row.get("classification_status") == "legal_reviewed_2024":
            fallback = row.get("classified_outcome", "")
            outcome = fallback if fallback in BINARY else ""
        if outcome in BINARY:
            rows.append({
                "year": row["year"],
                "era_citation": row.get("era_citation", ""),
                "case_name": row.get("case_name", ""),
                "pdf_url": row["pdf_url"],
                "outcome": outcome,
                "source": str(recent_path.relative_to(root)),
            })

    base = {row["pdf_url"]: row for row in _unique_by_url(rows, "legal")}
    for reviewed in direct_review_rows(root):
        if reviewed["included_in_merits_denominator"] == "no":
            base.pop(reviewed["pdf_url"], None)
            continue
        base[reviewed["pdf_url"]] = {
            "year": reviewed["year"],
            "era_citation": reviewed.get("era_citation", ""),
            "case_name": reviewed.get("case_name", ""),
            "pdf_url": reviewed["pdf_url"],
            "outcome": reviewed["legal_outcome"],
            "source": reviewed["source"],
        }

    # Automated source-cue matching is an audit/routing aid only. Only the
    # year-level data above and explicit direct-agent review ledgers can produce
    # canonical legal outcomes.
    return list(base.values())


def monetary_rows(root: Path) -> list[dict[str, str]]:
    path = root / "output" / "uniform_financial_2010_2025.csv"
    excluded_urls = {
        row["pdf_url"]
        for row in direct_review_rows(root)
        if row["included_in_merits_denominator"] == "no"
    }
    rows = []
    for row in read_csv(path):
        if row.get("pdf_url", "") in excluded_urls:
            continue
        outcome = row.get("financial_binary_outcome", "")
        if outcome not in BINARY:
            raise ValueError(f"non-binary monetary outcome {outcome!r} for {row.get('pdf_url', '')}")
        rows.append({
            "year": row["year"],
            "era_citation": row.get("era_citation", ""),
            "case_name": row.get("case_name", ""),
            "pdf_url": row["pdf_url"],
            "outcome": outcome,
            "source": str(path.relative_to(root)),
        })
    return _unique_by_url(rows, "monetary")


def summarize(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        if row["year"] not in YEARS:
            raise ValueError(f"unexpected year: {row['year']}")
        by_year[row["year"]][row["outcome"]] += 1

    result: list[dict[str, str]] = []
    total = Counter()
    for year in YEARS:
        counts = by_year[year]
        total.update(counts)
        n = counts["employee_win"] + counts["employer_win"]
        result.append({
            "year": year,
            "cases": str(n),
            "employee_wins": str(counts["employee_win"]),
            "employer_wins": str(counts["employer_win"]),
            "employee_win_rate": f"{100 * counts['employee_win'] / n:.1f}" if n else "",
        })
    n = total["employee_win"] + total["employer_win"]
    result.append({
        "year": "2010-2025",
        "cases": str(n),
        "employee_wins": str(total["employee_win"]),
        "employer_wins": str(total["employer_win"]),
        "employee_win_rate": f"{100 * total['employee_win'] / n:.1f}" if n else "",
    })
    return result


def paired_rows(legal: list[dict[str, str]], monetary: list[dict[str, str]]) -> list[dict[str, str]]:
    legal_by_url = {row["pdf_url"]: row for row in legal}
    monetary_by_url = {row["pdf_url"]: row for row in monetary}
    rows: list[dict[str, str]] = []
    for url in sorted(set(legal_by_url) | set(monetary_by_url)):
        legal_row = legal_by_url.get(url)
        monetary_row = monetary_by_url.get(url)
        source_row = legal_row or monetary_row
        assert source_row is not None
        if legal_row and monetary_row and legal_row["year"] != monetary_row["year"]:
            raise ValueError(f"year mismatch for {url}")
        rows.append({
            "year": source_row["year"],
            "era_citation": source_row.get("era_citation", ""),
            "case_name": source_row.get("case_name", ""),
            "pdf_url": url,
            "legal_outcome": legal_row["outcome"] if legal_row else "",
            "monetary_outcome": monetary_row["outcome"] if monetary_row else "",
            "paired": "yes" if legal_row and monetary_row else "no",
            "disagrees": "yes" if legal_row and monetary_row and legal_row["outcome"] != monetary_row["outcome"] else "no",
        })
    return rows


def comparison_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for year in (*YEARS, "2010-2025"):
        selected = rows if year == "2010-2025" else [row for row in rows if row["year"] == year]
        paired = [row for row in selected if row["paired"] == "yes"]
        legal_employee = sum(row["legal_outcome"] == "employee_win" for row in paired)
        money_employee = sum(row["monetary_outcome"] == "employee_win" for row in paired)
        disagreements = sum(row["disagrees"] == "yes" for row in paired)
        n = len(paired)
        result.append({
            "year": year,
            "paired_cases": str(n),
            "legal_employee_wins": str(legal_employee),
            "legal_employee_win_rate": f"{100 * legal_employee / n:.1f}" if n else "",
            "monetary_employee_wins": str(money_employee),
            "monetary_employee_win_rate": f"{100 * money_employee / n:.1f}" if n else "",
            "disagreements": str(disagreements),
            "disagreement_rate": f"{100 * disagreements / n:.1f}" if n else "",
            "legal_only": str(sum(bool(row["legal_outcome"]) and not row["monetary_outcome"] for row in selected)),
            "monetary_only": str(sum(bool(row["monetary_outcome"]) and not row["legal_outcome"] for row in selected)),
        })
    return result


def unresolved_legal_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "year": row["year"],
            "era_citation": row["era_citation"],
            "case_name": row["case_name"],
            "pdf_url": row["pdf_url"],
            "monetary_outcome": row["monetary_outcome"],
            "work_status": "agent_source_review_pending",
        }
        for row in rows
        if row["monetary_outcome"] and not row["legal_outcome"]
    ]


def headline_markdown(
    legal_summary: list[dict[str, str]],
    monetary_summary: list[dict[str, str]],
    comparison: list[dict[str, str]],
    unresolved_count: int,
) -> str:
    legal = legal_summary[-1]
    money = monetary_summary[-1]
    paired = comparison[-1]
    legal_n = int(legal["cases"])
    money_n = int(money["cases"])
    coverage = 100 * legal_n / money_n if money_n else 0.0
    if unresolved_count:
        status_text = (
            f"**Research status: UNFINISHED.** Legal merits currently has a binary result for "
            f"**{legal_n} of {money_n} determinations in the monetary corpus ({coverage:.1f}% coverage)**. "
            f"The remaining **{unresolved_count} determinations are unfinished agent work** and are listed in "
            "`unfinished_legal_cases.csv`. They still require direct source review by the reviewing agent; "
            "their monetary outcome is not used as a substitute legal result. Automated text cues are routing "
            "aids only and cannot complete this work."
        )
    else:
        status_text = (
            f"**Research status: COMPLETE.** Direct legal-merits source review is complete for all "
            f"**{money_n} determinations in the canonical monetary corpus (100.0% coverage)**. "
            "`unfinished_legal_cases.csv` is empty. Automated text cues remain non-canonical routing aids."
        )
    return f"""# Canonical outcome summary

The repository publishes two different outcome measures. They are intentionally not merged into one \"win rate\".

| Measure | Cases with a binary result | Employee wins | Employer wins | Employee win rate |
|---|---:|---:|---:|---:|
| Legal merits | {legal['cases']} | {legal['employee_wins']} | {legal['employer_wins']} | {legal['employee_win_rate']}% |
| Monetary outcome | {money['cases']} | {money['employee_wins']} | {money['employer_wins']} | {money['employee_win_rate']}% |

**Legal merits** asks whether the Authority upheld the employee's dismissal grievance or found the dismissal unjustified.

**Monetary outcome** asks whether the employee obtained a positive observable net monetary order in the public determination. Zero observable employee recovery, or a net adverse order, is an employer-side monetary outcome. This is not a legal-merits classification.

{status_text}

There are **{paired['paired_cases']} determinations with both measures**. Among those paired cases, the two measures disagree in **{paired['disagreements']} cases ({paired['disagreement_rate']}%)**.

The source corpus is search-derived from the ERA determinations database. It should not be described as a proven census of every dismissal determination unless the recall audit establishes that.

Generated by `build_outcome_summaries.py`. See `manifest.json` for definitions and source files.
"""


def build(root: Path) -> dict[str, object]:
    out = root / "output" / "headline"
    legal = legal_rows(root)
    monetary = monetary_rows(root)
    paired = paired_rows(legal, monetary)
    unresolved = unresolved_legal_rows(paired)
    legal_summary = summarize(legal)
    monetary_summary = summarize(monetary)
    comparison = comparison_summary(paired)

    summary_fields = ["year", "cases", "employee_wins", "employer_wins", "employee_win_rate"]
    write_csv(out / "legal_outcome_summary.csv", legal_summary, summary_fields)
    write_csv(out / "monetary_outcome_summary.csv", monetary_summary, summary_fields)
    write_csv(out / "legal_vs_monetary_summary.csv", comparison, [
        "year", "paired_cases", "legal_employee_wins", "legal_employee_win_rate",
        "monetary_employee_wins", "monetary_employee_win_rate", "disagreements",
        "disagreement_rate", "legal_only", "monetary_only",
    ])
    write_csv(out / "paired_case_outcomes.csv", paired, [
        "year", "era_citation", "case_name", "pdf_url", "legal_outcome",
        "monetary_outcome", "paired", "disagrees",
    ])
    write_csv(out / "unfinished_legal_cases.csv", unresolved, [
        "year", "era_citation", "case_name", "pdf_url", "monetary_outcome", "work_status",
    ])

    legal_total = int(legal_summary[-1]["cases"])
    money_total = int(monetary_summary[-1]["cases"])
    coverage = 100 * legal_total / money_total if money_total else 0.0
    totals = {"legal": legal_summary[-1], "monetary": monetary_summary[-1], "paired": comparison[-1]}
    manifest = {
        "schema_version": 4,
        "period": "2010-2025",
        "status": {
            "state": "complete" if not unresolved else "unfinished",
            "remaining_agent_legal_reviews": len(unresolved),
        },
        "corpus": {
            "description": "ERA determination search-derived dismissal corpus",
            "primary_search_phrase": "unjustified dismissal",
            "complete_population_claim": False,
        },
        "measures": {
            "legal_merits": {
                "employee_win": "ERA upheld the dismissal grievance or found the dismissal unjustified",
                "employer_win": "ERA rejected the dismissal grievance or found the dismissal justified",
                "sources": [
                    "output/combined_2010_2019_strict_classification.csv",
                    "output/combined_2020_2025_binary_classification.csv:original_legal_outcome",
                    "years/YYYY/output/YYYY_direct_legal_reviews.csv:direct_agent_source_review",
                ],
                "binary_classification_coverage": {
                    "classified": legal_total,
                    "reference_monetary_corpus": money_total,
                    "coverage_percent": round(coverage, 1),
                    "unfinished_agent_source_review": len(unresolved),
                    "unfinished_cases": "output/headline/unfinished_legal_cases.csv",
                },
            },
            "monetary_outcome": {
                "employee_win": "positive observable net monetary order to the employee",
                "employer_win": "zero observable employee recovery or net adverse monetary order",
                "source": "output/uniform_financial_2010_2025.csv:financial_binary_outcome",
            },
        },
        "totals": totals,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "README.md").write_text(
        headline_markdown(legal_summary, monetary_summary, comparison, len(unresolved))
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    manifest = build(args.root.resolve())
    print(json.dumps(manifest["totals"], indent=2))


if __name__ == "__main__":
    main()
