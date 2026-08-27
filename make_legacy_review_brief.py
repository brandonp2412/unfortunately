#!/usr/bin/env python3
"""Compress review dossiers into readable first-pass and micro review ledgers.

These files do not classify cases. They keep operative material for human review
and route ambiguous/high-risk rows back to the larger dossier or source PDF.
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


def compact_part(value: str, max_chars: int) -> str:
    value = value.strip()
    if len(value) <= max_chars:
        return value
    head = min(90, max_chars // 3)
    return value[:head].rstrip() + " … " + value[-(max_chars - head - 3):].lstrip()


def micro_operative(value: str, max_chars: int = 520) -> str:
    parts = [part.strip() for part in value.split(" || ") if part.strip()]
    if not parts:
        return compact_part(value, max_chars)
    selected = parts[-2:]
    each = max(180, (max_chars - 4) // len(selected))
    return " || ".join(compact_part(part, each) for part in selected)[-max_chars:]


def contribution_hit(row: dict[str, str]) -> bool:
    """Route actual contribution/s 124 references, not mere absence of a finding."""
    if row.get("candidate_contribution") == "yes":
        return True
    operative = (row.get("operative_findings_conclusion_orders_excerpt") or "").lower()
    remedies = (row.get("remedies_orders_excerpt") or "").lower()
    combined = operative + " " + remedies
    return any(term in combined for term in ("contribut", "s 124", "s.124", "section 124"))


def build(root: Path, year: int) -> Path:
    source = root / "output" / f"{year}_review_dossier.csv"
    with source.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    briefs = []
    micros = []
    for row in rows:
        contribution_requires_review = contribution_hit(row)
        high_risk = any((
            row.get("candidate_document_category") == "possible_merits_determination"
            and row.get("candidate_outcome") == "mixed_unclear",
            row.get("candidate_serious_misconduct_alleged") == "yes",
            contribution_requires_review,
            int(row.get("text_chars") or 0) < 1000,
        ))
        brief = {
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
            "contribution_or_s124_text_hit": "yes" if contribution_requires_review else "no",
            "dismissal_reason_excerpt": (row.get("dismissal_reason_excerpt") or "")[:450],
            "operative_findings_conclusion_orders_excerpt": tail_paragraphs(
                row.get("operative_findings_conclusion_orders_excerpt") or "", 1800
            ),
            "remedies_orders_excerpt": tail_paragraphs(row.get("remedies_orders_excerpt") or "", 900),
            "full_dossier_second_pass_candidate": "yes" if high_risk else "no",
            "manual_review_status": "pending",
        }
        briefs.append(brief)
        micros.append({
            "year": str(year),
            "search_result_number": row.get("search_result_number", ""),
            "era_citation": row.get("era_citation", ""),
            "case_name": compact_part(row.get("case_name", "") or "", 120),
            "candidate_document_category": row.get("candidate_document_category", ""),
            "candidate_outcome": row.get("candidate_outcome", ""),
            "serious_alleged_candidate": row.get("candidate_serious_misconduct_alleged", ""),
            "contribution_text_hit": "yes" if contribution_requires_review else "no",
            "reason": compact_part(row.get("dismissal_reason_excerpt", "") or "", 180),
            "operative": micro_operative(row.get("operative_findings_conclusion_orders_excerpt", "") or "", 520),
            "remedies": compact_part(tail_paragraphs(row.get("remedies_orders_excerpt", "") or "", 350), 220),
            "second_pass_candidate": "yes" if high_risk else "no",
        })

    output = root / "output"
    target = output / f"{year}_review_brief.csv"
    fields = list(briefs[0]) if briefs else ["year", "search_result_number", "era_citation"]
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(briefs)

    micro_target = output / f"{year}_review_micro.csv"
    micro_fields = list(micros[0]) if micros else ["year", "search_result_number", "era_citation"]
    with micro_target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=micro_fields)
        writer.writeheader()
        writer.writerows(micros)

    print(f"wrote {len(briefs)} review briefs to {target}")
    print(f"wrote {len(micros)} micro review rows to {micro_target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    build(args.root, args.year)
