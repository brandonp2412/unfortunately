#!/usr/bin/env python3
"""Create a blank human legal-review ledger from a legacy review brief."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


REVIEW_FIELDS = [
    "year",
    "search_result_number",
    "era_citation",
    "case_name",
    "decision_date",
    "pdf_url",
    "document_category",
    "included_in_merits_denominator",
    "final_outcome",
    "dismissal_reason_alleged",
    "serious_misconduct_alleged",
    "era_confirmed_conduct",
    "era_confirmed_serious_misconduct",
    "dismissal_substantively_justified",
    "dismissal_procedurally_justified",
    "contributory_conduct_found_s124",
    "contribution_percentage",
    "remedies_awarded",
    "supporting_quote_or_paragraph",
    "duplicate_of",
    "exclusion_reason",
    "confidence",
    "manual_review_status",
    "manual_review_notes",
    "second_review_required",
    "second_review_status",
    "second_review_notes",
]


def build(root: Path, year: int) -> Path:
    source = root / "output" / f"{year}_review_brief.csv"
    with source.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    review_rows = []
    for row in rows:
        second = row.get("full_dossier_second_pass_candidate") == "yes"
        review_rows.append({
            "year": str(year),
            "search_result_number": row.get("search_result_number", ""),
            "era_citation": row.get("era_citation", ""),
            "case_name": row.get("case_name", ""),
            "decision_date": row.get("decision_date", ""),
            "pdf_url": row.get("pdf_url", ""),
            "document_category": "",
            "included_in_merits_denominator": "",
            "final_outcome": "",
            "dismissal_reason_alleged": "",
            "serious_misconduct_alleged": "",
            "era_confirmed_conduct": "",
            "era_confirmed_serious_misconduct": "",
            "dismissal_substantively_justified": "",
            "dismissal_procedurally_justified": "",
            "contributory_conduct_found_s124": "",
            "contribution_percentage": "",
            "remedies_awarded": "",
            "supporting_quote_or_paragraph": "",
            "duplicate_of": "",
            "exclusion_reason": "",
            "confidence": "",
            "manual_review_status": "pending",
            "manual_review_notes": "",
            "second_review_required": "yes" if second else "no",
            "second_review_status": "pending" if second else "not_required",
            "second_review_notes": "",
        })

    target = root / "output" / f"{year}_manual_review.csv"
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(review_rows)
    print(f"wrote {len(review_rows)} blank review rows to {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    build(args.root, args.year)
