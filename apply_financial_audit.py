#!/usr/bin/env python3
"""Apply source-audited financial resolutions to review-routed ERA outcomes.

Direct source review resolves parser-sensitive orders such as question-framed
amounts, named-party orders, and awards with implicit payers. The recorded
resolutions keep reruns deterministic and auditable.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path


def normalize_citation(value: str) -> str:
    return "".join(re.findall(r"[a-z0-9]+", (value or "").lower()))


# These amounts establish the audited observable direction for parser-sensitive
# cases and form the deterministic override set.
AUDITED_OVERRIDES: dict[str, dict[str, object]] = {
    "2020nzera314": {
        "binary_outcome": "employee_win",
        "employee_money_awarded": 2892.77,
        "employee_money_adverse": 0.0,
        "note": "Burton v Cruse: wages ordered to Mr Burton ($1,805.75) and Ms Burton ($1,087.02); positive employee recovery. Costs reserved.",
    },
    "2020nzera485": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 0.0,
        "note": "Remihana v Rigweld Engineering: the $348 reimbursement appeared in an issue/question; the Authority expressly determined it should not be reimbursed.",
    },
    "2021nzera445": {
        "binary_outcome": "employee_win",
        "employee_money_awarded": 8000.0,
        "employee_money_adverse": 0.0,
        "note": "Operative remedies award $8,000 under s 123(1)(c)(i); positive employee recovery.",
    },
    "2022nzera342": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 0.0,
        "note": "Liability for a possible penalty was found, but this determination made no employee-side monetary order; zero observable recovery in this determination.",
    },
    "2023nzera11": {
        "binary_outcome": "employee_win",
        "employee_money_awarded": 7000.0,
        "employee_money_adverse": 0.0,
        "note": "Teague v Pyro Fires: Authority assessed and awarded $7,000 compensation under s 123(1)(c); positive employee recovery.",
    },
    "2024nzera327": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 0.0,
        "note": "The dollar figures are remedies sought, not money ordered to the employee; zero observable recovery.",
    },
    "2024nzera269": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 14250.0,
        "note": "Bhojwani v Baker Property Services: applicant ordered to pay respondent $14,250 as a contribution to costs.",
    },
    "2024nzera171": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 2250.0,
        "note": "W v YZ: W ordered to pay YZ $2,250 as a contribution to costs.",
    },
    "2024nzera550": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 2250.0,
        "note": "Pretorius v Taupo Intermediate School Board: applicant ordered to pay the Board $2,250 costs.",
    },
    "2024nzera249": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 3250.0,
        "note": "Hancock, Gibson and Ryan: applicants ordered to pay Mitre 10 $3,250 as a contribution to legal costs.",
    },
    "2025nzera643": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 0.0,
        "note": "The $151.24 weekly figure is a reimbursement claim, not an operative monetary award; zero observable recovery.",
    },
    "2025nzera160": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 0.0,
        "note": "The $868,852 figure is damages sought by the company, not an operative order; zero employee recovery.",
    },
    "2025nzera551": {
        "binary_outcome": "employer_win",
        "employee_money_awarded": 0.0,
        "employee_money_adverse": 2533.92,
        "note": "Green v Property Services Unlimited: Mr Green ordered to pay the employer $2,533.92 as a contribution to legal costs.",
    },
}

# These cases had money identified on both sides by the parser. Direct reading
# confirmed that the positive net direction is correct, so the parser result is
# retained but marked as audited.
AUDITED_CONFIRMED: dict[str, str] = {
    "2021nzera433": "Bennien v Carevets Hamilton: employee-side awards exceed any employee-side adverse amount; employee win confirmed.",
    "2022nzera109": "Naidu v Azak Cars: employee-side awards remain positive after deductions/contribution; employee win confirmed.",
}


def apply_audit_to_row(row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    out["financial_audit_status"] = "not_targeted"
    out["financial_audit_note"] = ""
    key = normalize_citation(row.get("era_citation", ""))

    override = AUDITED_OVERRIDES.get(key)
    if override is not None:
        awarded = float(override["employee_money_awarded"])
        adverse = float(override["employee_money_adverse"])
        out["employee_money_awarded"] = f"{awarded:.2f}"
        out["employee_money_adverse"] = f"{adverse:.2f}"
        out["observable_net_money"] = f"{awarded - adverse:.2f}"
        out["binary_outcome"] = str(override["binary_outcome"])
        out["financial_audit_status"] = "audited_override"
        out["financial_audit_note"] = str(override["note"])
        return out

    note = AUDITED_CONFIRMED.get(key)
    if note is not None:
        out["financial_audit_status"] = "audited_confirmed"
        out["financial_audit_note"] = note
    return out


def write_summary(root: Path, rows: list[dict[str, str]]) -> None:
    target = root / "output" / "binary_outcome_summary.csv"
    fields = ["year", "included_binary_cases", "employee_wins", "employer_wins", "employee_win_rate"]
    years = sorted({row["year"] for row in rows if row.get("year")})
    summary_rows: list[dict[str, str]] = []
    overall = Counter()
    for year in years:
        selected = [row for row in rows if row["year"] == year and row["binary_outcome"] in {"employee_win", "employer_win"}]
        counts = Counter(row["binary_outcome"] for row in selected)
        total = len(selected)
        overall.update(counts)
        summary_rows.append({
            "year": year,
            "included_binary_cases": str(total),
            "employee_wins": str(counts["employee_win"]),
            "employer_wins": str(counts["employer_win"]),
            "employee_win_rate": f"{(100 * counts['employee_win'] / total if total else 0):.1f}",
        })
    overall_total = overall["employee_win"] + overall["employer_win"]
    summary_rows.append({
        "year": "2020-2025",
        "included_binary_cases": str(overall_total),
        "employee_wins": str(overall["employee_win"]),
        "employer_wins": str(overall["employer_win"]),
        "employee_win_rate": f"{(100 * overall['employee_win'] / overall_total if overall_total else 0):.1f}",
    })
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary_rows)


def write_audit_resolutions(root: Path, rows: list[dict[str, str]]) -> None:
    selected = [row for row in rows if row["financial_audit_status"] != "not_targeted"]
    fields = [
        "year", "era_citation", "case_name", "binary_outcome",
        "employee_money_awarded", "employee_money_adverse", "observable_net_money",
        "financial_audit_status", "financial_audit_note", "pdf_url",
    ]
    with (root / "output" / "financial_audit_resolutions.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in selected)


def apply(root: Path) -> list[dict[str, str]]:
    target = root / "output" / "combined_2020_2025_binary_classification.csv"
    rows = list(csv.DictReader(target.open(newline="")))
    audited = [apply_audit_to_row(row) for row in rows]
    fieldnames = list(audited[0]) if audited else []
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audited)
    write_summary(root, audited)
    write_audit_resolutions(root, audited)
    return audited


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    rows = apply(args.root.resolve())
    audited = Counter(row["financial_audit_status"] for row in rows)
    binary = Counter(row["binary_outcome"] for row in rows if row["binary_outcome"] in {"employee_win", "employer_win"})
    print("financial audit", dict(audited), flush=True)
    print("2020-2025 binary totals", dict(binary), flush=True)


if __name__ == "__main__":
    main()
