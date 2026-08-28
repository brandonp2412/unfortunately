#!/usr/bin/env python3
"""Apply one dismissal-merits denominator rule to every ERA search result.

A determination is in scope only when it itself finally resolves the dismissal or
constructive-dismissal claim.  A merits finding that no dismissal occurred (or
that constructive dismissal failed) is an in-scope employer win.  Interim,
time-limit/leave, removal, costs, compliance, withdrawal, and other preliminary
rulings are out of scope.

The parser routes obvious cases and emits an audit reason for every case where
source judgment is still required.  It never treats an old route as conclusive
when the operative findings conflict with it.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from finalize_legacy_strict import CODE_TO_STATE, EXPECTED_ROWS, YEAR_CODES
from uniform_financial import fetch_pdf, pdf_text

EMPLOYEE_PATTERNS = [
    r"\b(?:was|were|has been|had been) unjustifiabl(?:y|e) dismissed\b",
    r"\bdismissal (?:was|is) unjustified\b",
    r"\bunjustified dismissal (?:grievance|claim).{0,100}\b(?:succeeds?|established|made out|upheld)\b",
    r"\bpersonal grievance.{0,120}\bunjustified dismissal\b",
    r"\b(?:was|were) constructively dismissed\b",
    r"\bconstructive dismissal (?:grievance|claim).{0,100}\b(?:succeeds?|established|made out|upheld)\b",
]
EMPLOYER_PATTERNS = [
    r"\b(?:was|were|has been|had been) justifiabl(?:y|e) dismissed\b",
    r"\bdismissal (?:was|is) justified\b",
    r"\bnot unjustifiabl(?:y|e) dismissed\b",
    r"\bunjustified dismissal (?:grievance|claim).{0,120}\b(?:fails?|does not succeed|not established|not made out|dismissed)\b",
    r"\bconstructive dismissal (?:grievance|claim).{0,120}\b(?:fails?|does not succeed|not established|not made out|dismissed)\b",
    r"\bnot constructively dismissed\b",
    r"\b(?:was|were) not dismissed\b",
    r"\bno dismissal (?:occurred|took place)\b",
    r"\b(?:did not|had not) dismiss(?:ed)?\b",
    r"\bfair and reasonable employer.{0,180}\bdismiss",
    r"\bdismiss.{0,180}\bfair and reasonable employer",
]

# These are useful only when there is no final merits finding.  Procedural words
# often appear in a merits decision's history, so a strong merits result wins.
PROCEDURAL_PATTERNS = [
    r"\binterim reinstatement\b",
    r"\bapplication for interim\b",
    r"\bleave to (?:raise|bring|pursue|proceed with) (?:a )?(?:personal )?grievance\b",
    r"\bextension of time\b",
    r"\bexceptional circumstances.{0,160}\b(?:90|ninety)[- ]day",
    r"\bgrievance.{0,100}\bnot raised (?:within|in) (?:the )?(?:90|ninety)[- ]day",
    r"\b(?:removed?|removal) to (?:the )?employment court\b",
    r"\bnon[- ]publication\b|\bsuppression (?:order|application)\b",
    r"\b(?:strike ?out|struck out)\b",
    r"\bwant of prosecution\b",
    r"\bjoinder\b",
    r"\bvenue\b",
    r"\bcompliance order\b|\bapplication for compliance\b",
    r"\bsubstantive (?:claim|grievance|matter|issues?).{0,140}\b(?:later|future|remain|yet to be|will be)\b",
    r"\b(?:will|is to) (?:be )?(?:investigated|heard|determined) (?:at|on|in) (?:a )?(?:later|future|separate)\b",
]
COSTS_ONLY_PATTERNS = [
    r"\b(?:costs?|disbursements?) (?:are|is|were) (?:reserved|awarded|ordered)\b",
    r"\bcontribution to (?:legal )?costs\b",
]
WITHDRAWAL_PATTERNS = [r"\bwithdrawn\b", r"\bdiscontinued\b", r"\bsettled\b"]
DISADVANTAGE_ONLY = [
    r"\bunjustified disadvantage\b",
    r"\bwarning\b",
    r"\bsuspension\b",
    r"\bwage arrears\b|\bholiday pay\b|\bunpaid wages\b",
]


def clean(value: str) -> str:
    return " ".join((value or "").split())


def units(text: str) -> list[str]:
    compact = (text or "").replace("\r", "\n")
    parts = re.split(r"\|\||\n\s*\n|(?=\[\d+\])", compact)
    return [clean(part) for part in parts if clean(part)]


def last_match(text: str, patterns: list[str]) -> tuple[int, str]:
    lower = text.lower()
    best = (-1, "")
    for pattern in patterns:
        for match in re.finditer(pattern, lower, re.I | re.S):
            if match.start() > best[0]:
                best = (match.start(), clean(text[match.start(): min(len(text), match.end() + 260)]))
    return best


def legal_result(text: str) -> tuple[str, str]:
    """Return employee_win/employer_win/unclear and supporting fragment."""
    emp = last_match(text, EMPLOYEE_PATTERNS)
    er = last_match(text, EMPLOYER_PATTERNS)
    if emp[0] < 0 and er[0] < 0:
        return "unclear", ""
    if emp[0] > er[0]:
        # Guard against phrases such as "not ... unjustifiably dismissed" where
        # the positive substring is embedded in an employer-win finding.
        nearby = text[max(0, emp[0] - 30):emp[0] + 220].lower()
        if re.search(r"\bnot\b.{0,45}\bunjustifiabl", nearby):
            return "employer_win", clean(nearby)
        return "employee_win", emp[1]
    return "employer_win", er[1]


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.I | re.S) for pattern in patterns)


def classify_scope(text: str, prior_category: str, prior_outcome: str) -> dict[str, str]:
    text = clean(text)
    result, support = legal_result(text)
    procedural = has_any(text, PROCEDURAL_PATTERNS)
    withdrawn = has_any(text, WITHDRAWAL_PATTERNS)
    costs = has_any(text, COSTS_ONLY_PATTERNS)
    disadvantage = has_any(text, DISADVANTAGE_ONLY)

    prior_included = prior_category == "included_merits" or prior_category == "possible_merits_determination"
    prior_no_dismissal = prior_category == "excluded_no_dismissal_merits"
    clearly_excluded_prior = prior_category in {
        "excluded_costs_follow_up", "excluded_procedural_interlocutory",
        "excluded_withdrawn_discontinued", "excluded_want_of_prosecution",
        "excluded_compliance_removal", "excluded_jurisdiction_only",
        "excluded_duplicate_follow_up", "excluded_other_nonmerits",
        "costs_follow_up", "procedural_interlocutory",
        "withdrawal_or_non_prosecution_candidate", "compliance_or_removal",
        "jurisdiction_only",
    }

    audit: list[str] = []
    if clearly_excluded_prior:
        # Prior case-level review says procedural/non-merits. A strong apparent
        # merits sentence may be a quotation of the earlier decision, so surface it.
        if result != "unclear":
            audit.append("excluded_prior_contains_merits_result")
        return {
            "scope_included": "no",
            "scope_reason": prior_category,
            "legal_dismissal_result": "excluded",
            "scope_support": support,
            "scope_audit_reason": ";".join(audit),
        }

    if prior_no_dismissal:
        if result == "employer_win":
            return {
                "scope_included": "yes",
                "scope_reason": "dismissal_claim_resolved_against_employee",
                "legal_dismissal_result": "employer_win",
                "scope_support": support,
                "scope_audit_reason": "",
            }
        if result == "employee_win":
            return {
                "scope_included": "yes",
                "scope_reason": "dismissal_claim_resolved_for_employee",
                "legal_dismissal_result": "employee_win",
                "scope_support": support,
                "scope_audit_reason": "prior_no_dismissal_conflicts_with_merits_result",
            }
        # If the prior no-dismissal bucket has no actual dismissal resolution,
        # it usually represents disadvantage/wages/ongoing employment.
        return {
            "scope_included": "no",
            "scope_reason": "no_final_dismissal_resolution",
            "legal_dismissal_result": "excluded",
            "scope_support": "",
            "scope_audit_reason": "" if disadvantage else "no_dismissal_prior_without_clear_resolution",
        }

    if prior_included:
        if result != "unclear":
            # Strong procedural language after the merits phrase is suspicious:
            # the apparent merits sentence may merely describe allegations/history.
            result_pos = max(last_match(text, EMPLOYEE_PATTERNS)[0], last_match(text, EMPLOYER_PATTERNS)[0])
            proc_pos = last_match(text, PROCEDURAL_PATTERNS)[0]
            if procedural and proc_pos > result_pos >= 0:
                audit.append("procedural_finding_after_merits_signal")
            return {
                "scope_included": "yes",
                "scope_reason": "final_dismissal_merits",
                "legal_dismissal_result": result,
                "scope_support": support,
                "scope_audit_reason": ";".join(audit),
            }
        if procedural or withdrawn:
            return {
                "scope_included": "no",
                "scope_reason": "procedural_without_final_dismissal_result",
                "legal_dismissal_result": "excluded",
                "scope_support": "",
                "scope_audit_reason": "prior_included_reclassified_procedural",
            }
        # A prior merits row without a detectable final result needs direct judgment.
        return {
            "scope_included": "yes",
            "scope_reason": "prior_merits_requires_source_confirmation",
            "legal_dismissal_result": prior_outcome if prior_outcome in {"employee_win", "employer_win"} else "unclear",
            "scope_support": "",
            "scope_audit_reason": "included_without_clear_final_result",
        }

    # Unknown routes are never silently included.
    return {
        "scope_included": "no",
        "scope_reason": "unclassified_nonmerits_route",
        "legal_dismissal_result": "excluded",
        "scope_support": "",
        "scope_audit_reason": "unknown_prior_route",
    }


def load_legacy(root: Path, year: int) -> list[dict[str, str]]:
    outdir = root / "years" / str(year) / "output"
    initial = list(csv.DictReader((outdir / "initial_extraction.csv").open(newline="")))
    dossier = list(csv.DictReader((outdir / f"{year}_review_dossier.csv").open(newline="")))
    expected = EXPECTED_ROWS[year]
    if len(initial) != expected or len(dossier) != expected:
        raise RuntimeError(f"{year}: acquisition count mismatch")
    by_url = {row["pdf_url"]: row for row in dossier}
    codes = YEAR_CODES[year]
    rows: list[dict[str, str]] = []
    for idx, source in enumerate(initial):
        d = by_url[source["pdf_url"]]
        prior_category, prior_outcome = CODE_TO_STATE[codes[idx]]
        text = d.get("operative_findings_conclusion_orders_excerpt", "") or d.get("remedies_orders_excerpt", "")
        classified = classify_scope(text, prior_category, prior_outcome)
        rows.append({
            "year": str(year),
            "source_row_id": source.get("search_result_number", str(idx + 1)),
            "era_citation": source.get("era_citation", ""),
            "case_name": source.get("case_name", ""),
            "pdf_url": source["pdf_url"],
            "prior_category": prior_category,
            "prior_outcome": prior_outcome,
            "operative_excerpt": clean(text),
            **classified,
        })
    return rows


def recent_text(root: Path, row: dict[str, str]) -> str:
    digest = hashlib.sha1(row["pdf_url"].encode()).hexdigest()
    cache = root / ".uniform-scope-cache" / row["year"]
    pdf = cache / "pdf" / f"{digest}.pdf"
    txt = cache / "text" / f"{digest}.txt"
    if not pdf.exists():
        fetch_pdf(row["pdf_url"], pdf)
    text = txt.read_text(errors="replace") if txt.exists() else pdf_text(pdf, txt)
    # The final 30k chars are broad enough to contain findings/remedies but avoid
    # most introductory allegation/claim material.
    return text[-30000:]


def classify_recent_row(root: Path, row: dict[str, str], idx: int) -> dict[str, str]:
    text = recent_text(root, row)
    prior_category = row.get("document_category", "")
    prior_outcome = row.get("classified_outcome", "")
    classified = classify_scope(text, prior_category, prior_outcome)
    return {
        "year": row["year"],
        "source_row_id": str(idx + 1),
        "era_citation": row.get("era_citation", ""),
        "case_name": row.get("case_name", ""),
        "pdf_url": row["pdf_url"],
        "prior_category": prior_category,
        "prior_outcome": prior_outcome,
        "operative_excerpt": clean(text[-16000:]),
        **classified,
    }


def load_recent(root: Path, year: int, workers: int) -> list[dict[str, str]]:
    source = list(csv.DictReader((root / "output" / "combined_2020_2025_full_classification.csv").open(newline="")))
    selected = [(idx, row) for idx, row in enumerate(source) if row["year"] == str(year)]
    result: list[dict[str, str] | None] = [None] * len(selected)
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as pool:
        futures = {pool.submit(classify_recent_row, root, row, idx): pos for pos, (idx, row) in enumerate(selected)}
        done = 0
        for future in as_completed(futures):
            result[futures[future]] = future.result()
            done += 1
            if done % 25 == 0 or done == len(selected):
                print(f"{year}: scope-scored {done}/{len(selected)} search results", flush=True)
    return [row for row in result if row is not None]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.year <= 2019:
        rows = load_legacy(root, args.year)
    else:
        rows = load_recent(root, args.year, args.workers)
    target_dir = root / "output" / "uniform_scope"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{args.year}.csv"
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    included = sum(row["scope_included"] == "yes" for row in rows)
    flagged = sum(bool(row["scope_audit_reason"]) for row in rows)
    print(f"{args.year}: rows={len(rows)} included={included} scope_audit={flagged}", flush=True)


if __name__ == "__main__":
    main()
