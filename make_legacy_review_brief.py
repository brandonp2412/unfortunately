#!/usr/bin/env python3
"""Compress review dossiers into a readable first-pass ledger.

This does not classify cases. It only keeps enough operative material to let a
human reviewer read every row efficiently, while routing ambiguous/high-risk
rows back to the larger dossier or source PDF for a second pass.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def tail_paragraphs(value: str, max_chars: int) -> str:
    parts = [part.strip() for part in value.split(" || ") if part.strip()]
    kept: list[str] = []
    size = 0
    for part in reversed(parts):
        extra = len(part) + (4 if kept else 0)
        if kept and size + extra > max_chars:
            break
        kept.append(part)
        size += extra
        if size >= max_chars:
            break
    if not kept:
        return value[-max_chars:]
    return " || ".join(reversed(kept))


def build(root: Path, year: int) -> Path:
    source = root / "output" / f"{year}_review_dossier.csv"
    with source.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    briefs = []
    for row in rows:
        high_risk = any((
            row.get("candidate_document_category") == "possible_merits_determination"
            and row.get("candidate_outcome") == "mixed_unclear",
            row.get("candidate_serious_misconduct_alleged") == "yes",
            row.get("candidate_contribution") != "no",
            int(row.get("text_chars") or 0) < 1000,
        ))
        briefs.append({
            "year": str(year),
            "search_result_number": row.get("search_result_number", ""),
            "era_citation": row.get("era_citation", ""),
            "case_name": row.get("case_name", ""),
            "decision_date": row.get("decision_date", ""),
            "pdf_url": row.get("pdf_url", ""),
            "text_chars": row.get("text_chars", ""),
            "candidate_document_category": row.get("candidate_document_category", ""),
            "candidate_outcome": row.get("candidate_outcome", ""),
            "candidate_serious_misconduct_alleged": row.get("candidate_serious_misconduct_alleged", ""),
            "candidate_contribution": row.get("candidate_contribution", ""),
            "candidate_contribution_percentage": row.get("candidate_contribution_percentage", ""),
            "dismissal_reason_excerpt": (row.get("dismissal_reason_excerpt") or "")[:450],
            "operative_findings_conclusion_orders_excerpt": tail_paragraphs(
                row.get("operative_findings_conclusion_orders_excerpt") or "", 1800
            ),
            "remedies_orders_excerpt": tail_paragraphs(row.get("remedies_orders_excerpt") or "", 900),
            "full_dossier_second_pass_candidate": "yes" if high_risk else "no",
            "manual_review_status": "pending",
        })

    target = root / "output" / f"{year}_review_brief.csv"
    fields = list(briefs[0]) if briefs else ["year", "search_result_number", "era_citation"]
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(briefs)
    print(f"wrote {len(briefs)} review briefs to {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    build(args.root, args.year)
