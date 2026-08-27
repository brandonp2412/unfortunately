#!/usr/bin/env python3
"""Build compact, auditable per-case excerpts for manual ERA merits review.

The output is deliberately a review aid, not a final legal classification. It
extracts the document heading plus operative paragraphs likely to contain the
Authority's findings, conclusion, remedies, contribution, and orders so a
reviewer can read every search-result determination efficiently while retaining
links back to the full text and PDF.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from analyze_era import category_from_text, contribution_found, outcome_from_operative_text, serious_codes


OPERATIVE_TERMS = re.compile(
    r"\b(?:dismiss|constructive dismissal|personal grievance|justif|find|found|"
    r"conclud|determin|order|remed|reinstat|compensat|lost wages|reimburse|"
    r"contribut|section 124|s\.?\s*124|serious misconduct|gross misconduct|"
    r"summary dismissal|withdraw|discontinu|jurisdiction|costs?|penalt)\w*\b",
    re.I,
)
DISPOSITION_TERMS = re.compile(
    r"\b(?:unjustifiably dismissed|dismissal (?:was|is) unjustified|dismissal (?:was|is) justified|"
    r"personal grievance .*?(?:made out|established|upheld|succeeds?|fails?|dismissed)|"
    r"claim .*?(?:succeeds?|fails?|dismissed)|application .*?(?:granted|declined|dismissed)|"
    r"constructively dismissed|orders? (?:that|for)|I (?:find|conclude|determine|order|direct))\b",
    re.I,
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def numbered_paragraphs(text: str) -> list[str]:
    """Return numbered ERA paragraphs, with a conservative fallback for OCR text."""
    matches = list(re.finditer(r"(?m)^\s*\[(\d{1,4})\]\s*", text))
    if not matches:
        return [clean(p) for p in re.split(r"\n\s*\n", text) if clean(p)]
    out: list[str] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append(f"[{match.group(1)}] {clean(text[match.end():end])}")
    return out


def operative_excerpt(text: str, max_chars: int = 6500) -> str:
    """Select operative paragraphs while retaining later findings over submissions."""
    paras = numbered_paragraphs(text)
    if not paras:
        return clean(text[-max_chars:])

    start = max(0, len(paras) // 2)
    selected: list[tuple[int, str]] = []
    for i, para in enumerate(paras):
        if i >= start and OPERATIVE_TERMS.search(para):
            selected.append((i, para))
    for i in range(max(0, len(paras) - 5), len(paras)):
        selected.append((i, paras[i]))
    if len(selected) < 4:
        for i, para in enumerate(paras):
            if DISPOSITION_TERMS.search(para):
                selected.append((i, para))

    deduped: list[str] = []
    seen: set[int] = set()
    for i, para in sorted(selected):
        if i not in seen:
            seen.add(i)
            deduped.append(para)

    joined = " || ".join(deduped)
    if len(joined) > max_chars:
        joined = joined[-max_chars:]
        first_sep = joined.find(" || ")
        if first_sep >= 0:
            joined = joined[first_sep + 4 :]
    return joined


def first_reason_excerpt(text: str) -> str:
    compact = clean(text[:18000])
    patterns = (
        r"(?:summarily\s+)?dismissed\s+(?:for|because of|on the grounds? of)\s+.{0,500}",
        r"reason(?:s)?\s+for\s+(?:the\s+)?dismissal.{0,500}",
        r"alleg(?:ation|ed).{0,350}(?:misconduct|dismiss)",
    )
    for pattern in patterns:
        match = re.search(pattern, compact, re.I)
        if match:
            return match.group(0)[:650]
    return ""


def remedies_excerpt(text: str) -> str:
    paras = numbered_paragraphs(text)
    hits = [
        p for p in paras[-35:]
        if re.search(r"\b(?:reinstat|compensat|lost wages|reimburse|pay|award|remed|order)\w*\b|\$", p, re.I)
    ]
    return " || ".join(hits[-6:])[-3000:]


def candidate_category(text: str) -> str:
    head = clean(text[:5000]).lower()
    tail = clean(text[-12000:]).lower()
    base = category_from_text(text)
    if base != "possible_merits_determination":
        return base
    if "interim reinstatement" in head and any(
        phrase in tail for phrase in (
            "application for interim reinstatement is declined",
            "application for interim reinstatement is granted",
            "this determination resolves the claim for interim reinstatement",
        )
    ):
        return "procedural_interlocutory"
    if re.search(r"\b(?:costs?|penalt(?:y|ies)) determination\b", head):
        return "costs_follow_up"
    if re.search(r"\b(?:withdrawn|discontinued|want of prosecution)\b", head + " " + tail):
        return "withdrawal_or_non_prosecution_candidate"
    if "does not have jurisdiction" in tail and not re.search(
        r"unjustifiably dismissed|dismissal was (?:un)?justified", tail
    ):
        return "jurisdiction_only"
    return "possible_merits_determination"


def build(root: Path, year: int) -> Path:
    source = root / "output" / "initial_extraction.csv"
    rows = list(csv.DictReader(source.open(newline="")))
    out_rows = []
    for row in rows:
        text_path = root / row["local_text"]
        text = text_path.read_text(errors="replace") if text_path.exists() else ""
        alleged, confirmed, _ = serious_codes(text)
        contribution, pct = contribution_found(text)
        compact = clean(text)
        out_rows.append({
            "year": str(year),
            "search_result_number": row.get("search_result_number", ""),
            "era_citation": row.get("era_citation", ""),
            "case_name": row.get("case_name", ""),
            "decision_date": row.get("decision_date", ""),
            "pdf_url": row.get("pdf_url", ""),
            "local_text": row.get("local_text", ""),
            "text_chars": str(len(compact)),
            "candidate_document_category": candidate_category(text),
            "candidate_outcome": outcome_from_operative_text(text),
            "candidate_serious_misconduct_alleged": alleged,
            "candidate_era_confirmed_serious_misconduct": confirmed,
            "candidate_contribution": contribution,
            "candidate_contribution_percentage": pct,
            "dismissal_reason_excerpt": first_reason_excerpt(text),
            "operative_findings_conclusion_orders_excerpt": operative_excerpt(text),
            "remedies_orders_excerpt": remedies_excerpt(text),
            "manual_review_status": "pending",
            "manual_review_notes": "",
        })
    target = root / "output" / f"{year}_review_dossier.csv"
    fields = list(out_rows[0]) if out_rows else ["year", "search_result_number", "era_citation"]
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"wrote {len(out_rows)} review dossiers to {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    build(args.root, args.year)
