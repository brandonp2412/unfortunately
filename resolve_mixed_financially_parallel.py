#!/usr/bin/env python3
"""Bounded-parallel runner for the mixed-outcome financial tie-breaker."""
from __future__ import annotations

import argparse
import csv
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from resolve_mixed_financially import (
    MONEY_RE,
    direction,
    fetch_pdf,
    money_value,
    order_window,
    pdf_text,
    units,
)

STOPWORDS = {
    "the", "and", "of", "for", "new", "zealand", "limited", "ltd", "pty",
    "company", "incorporated", "trust", "board", "services", "service",
    "group", "holdings", "first", "second", "applicant", "respondent",
}
CLAIM_WORDS = re.compile(
    r"\b(?:claim(?:ed|s)?|sought|seeks?|asking for|requested|salary|hourly rate|"
    r"paid approximately|offer(?:ed)?|bonus earned|conditional on|would have|"
    r"calculated at|calculation)\b",
    re.I,
)
AWARD_WORDS = re.compile(
    r"\b(?:ordered|order|must pay|shall pay|is to pay|are to pay|entitled|award(?:ed)?|"
    r"reimburse(?:ment|d)?|compensation|lost wages?|lost remuneration|arrears|"
    r"holiday pay|kiwisaver|special damages|interest on|penalty)\b",
    re.I,
)
NEGATION_WORDS = re.compile(
    r"\b(?:not be reimbursed|not entitled|no (?:monetary )?(?:award|remedy)|"
    r"decline(?:d)? to award|claim .*?(?:fails|dismissed|not made out))\b",
    re.I,
)
PAY_PHRASE = re.compile(
    r"(?P<payer>.{0,180}?)(?:is ordered to pay|are ordered to pay|must pay|shall pay|"
    r"is to pay|are to pay)(?P<recipient>.{0,220})",
    re.I,
)


def clean_tokens(name: str) -> set[str]:
    tokens = set(re.findall(r"[a-z][a-z'-]{2,}", name.lower()))
    return {token for token in tokens if token not in STOPWORDS and len(token) >= 4}


def party_tokens(case_name: str) -> tuple[set[str], set[str]]:
    parts = re.split(r"\s+v\s+", case_name, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return set(), set()
    return clean_tokens(parts[0]), clean_tokens(parts[1])


def contains_party(text: str, tokens: set[str]) -> bool:
    lower = text.lower()
    return any(re.search(rf"\b{re.escape(token)}\b", lower) for token in tokens)


def party_direction(unit: str, case_name: str) -> str:
    """Infer money direction when orders use party names rather than role labels."""
    base = direction(unit)
    if base != "neutral":
        return base
    if NEGATION_WORDS.search(unit):
        return "neutral"

    employee, employer = party_tokens(case_name)
    match = PAY_PHRASE.search(unit)
    if match:
        payer = match.group("payer")
        recipient = match.group("recipient")
        payer_employee = contains_party(payer, employee)
        payer_employer = contains_party(payer, employer)
        recipient_employee = contains_party(recipient, employee)
        recipient_employer = contains_party(recipient, employer)
        if payer_employer or recipient_employee:
            return "employee_positive"
        if payer_employee or recipient_employer:
            return "employee_negative"

    lower = unit.lower()
    if contains_party(unit, employee) and AWARD_WORDS.search(unit) and not CLAIM_WORDS.search(unit):
        if not re.search(r"\b(?:pay|costs?).{0,70}(?:respondent|employer)\b", lower):
            return "employee_positive"
    if contains_party(unit, employer) and re.search(r"\bcosts?\b", lower) and re.search(r"\bawarded\b|\bpayable\b", lower):
        return "employee_negative"
    return "neutral"


def default_order_direction(window: str, case_name: str) -> str:
    """Find a named payment instruction that governs following bullet-list amounts."""
    employee, employer = party_tokens(case_name)
    compact = " ".join(window.split())
    for match in PAY_PHRASE.finditer(compact):
        payer = match.group("payer")[-180:]
        recipient = match.group("recipient")[:220]
        if contains_party(payer, employer) or contains_party(recipient, employee):
            return "employee_positive"
        if contains_party(payer, employee) or contains_party(recipient, employer):
            return "employee_negative"
    if re.search(r"respondent.{0,100}(?:ordered|must|shall|is to).{0,40}pay.{0,100}applicant", compact, re.I):
        return "employee_positive"
    if re.search(r"applicant.{0,100}(?:ordered|must|shall|is to).{0,40}pay.{0,100}respondent", compact, re.I):
        return "employee_negative"
    return "neutral"


def continuation_award(unit: str) -> bool:
    """True for an order-list component rather than a historical/claimed figure."""
    if NEGATION_WORDS.search(unit):
        return False
    if CLAIM_WORDS.search(unit) and not re.search(r"\b(?:ordered|must pay|shall pay|is to pay|are to pay)\b", unit, re.I):
        return False
    if AWARD_WORDS.search(unit):
        return True
    return bool(re.match(r"^\s*(?:\(?[a-zivx]+\)?[.)]?|\(?\d+\)?[.)])\s+", unit, re.I))


def materially_unallocated(unit: str) -> bool:
    if NEGATION_WORDS.search(unit):
        return False
    if CLAIM_WORDS.search(unit) and not AWARD_WORDS.search(unit):
        return False
    return bool(AWARD_WORDS.search(unit))


def dedupe(entries: list[tuple[float, str]]) -> list[tuple[float, str]]:
    seen: set[tuple[float, str]] = set()
    result: list[tuple[float, str]] = []
    for amount, unit in entries:
        para = re.search(r"\[(\d+)\]", unit)
        key_text = f"p{para.group(1)}" if para else re.sub(r"\s+", " ", unit.lower())[:320]
        key = (amount, key_text)
        if key not in seen:
            seen.add(key)
            result.append((amount, unit))
    return result


def score_case(text: str, case_name: str) -> dict[str, object]:
    window = order_window(text)
    default = default_order_direction(window, case_name)
    positives: list[tuple[float, str]] = []
    negatives: list[tuple[float, str]] = []
    unresolved: list[str] = []

    for unit in units(window):
        amounts = [money_value(value) for value in MONEY_RE.findall(unit)]
        if not amounts:
            continue
        d = party_direction(unit, case_name)
        if d == "neutral" and default != "neutral" and continuation_award(unit):
            d = default
        if d == "employee_positive":
            positives.extend((amount, unit) for amount in amounts)
        elif d == "employee_negative":
            negatives.extend((amount, unit) for amount in amounts)
        elif materially_unallocated(unit):
            unresolved.append(unit)

    positives = dedupe(positives)
    negatives = dedupe(negatives)
    positive_total = sum(amount for amount, _ in positives)
    negative_total = sum(amount for amount, _ in negatives)

    if positives and not negatives:
        outcome = "employee_win"
    elif negatives and not positives:
        outcome = "employer_win"
    elif positives and negatives:
        outcome = "employee_win" if positive_total - negative_total > 0 else "employer_win"
    else:
        outcome = "employer_win"

    return {
        "employee_money_awarded": positive_total,
        "employee_money_adverse": negative_total,
        "observable_net_money": positive_total - negative_total,
        "financial_binary_outcome": outcome,
        "financial_evidence": " || ".join([u for _, u in positives + negatives][-8:])[:7000],
        "unallocated_money_units": len(unresolved),
        "unallocated_money_evidence": " || ".join(unresolved[-8:])[:7000],
        "both_sides_money": "yes" if positives and negatives else "no",
    }


def blank_out(row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    original = row["classified_outcome"]
    out.update({
        "original_legal_outcome": original,
        "financial_tiebreak_applied": "no",
        "employee_money_awarded": "",
        "employee_money_adverse": "",
        "observable_net_money": "",
        "financial_evidence": "",
        "unallocated_money_units": "",
        "unallocated_money_evidence": "",
        "both_sides_money": "",
        "binary_outcome": original,
    })
    return out


def score_row(root: Path, row: dict[str, str]) -> dict[str, object]:
    citation = row["era_citation"].replace(" ", "_")
    cache = root / ".financial-cache"
    pdf = cache / "pdf" / f"{citation}.pdf"
    txt = cache / "text" / f"{citation}.txt"
    if not pdf.exists():
        fetch_pdf(row["pdf_url"], pdf)
    text = txt.read_text(errors="replace") if txt.exists() else pdf_text(pdf, txt)
    return score_case(text, row.get("case_name", ""))


def resolve_parallel(root: Path, workers: int) -> list[dict[str, str]]:
    source = list(csv.DictReader((root / "output" / "combined_2020_2025_full_classification.csv").open(newline="")))
    result = [blank_out(row) for row in source]
    mixed_indices = [i for i, row in enumerate(source) if row["classified_outcome"] == "mixed_unclear"]
    print(f"Scoring {len(mixed_indices)} mixed rows with {workers} workers", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(score_row, root, source[i]): i for i in mixed_indices}
        done = 0
        for future in as_completed(futures):
            i = futures[future]
            scored = future.result()
            out = result[i]
            out["financial_tiebreak_applied"] = "yes"
            out["employee_money_awarded"] = f"{scored['employee_money_awarded']:.2f}"
            out["employee_money_adverse"] = f"{scored['employee_money_adverse']:.2f}"
            out["observable_net_money"] = f"{scored['observable_net_money']:.2f}"
            out["financial_evidence"] = str(scored["financial_evidence"])
            out["unallocated_money_units"] = str(scored["unallocated_money_units"])
            out["unallocated_money_evidence"] = str(scored["unallocated_money_evidence"])
            out["both_sides_money"] = str(scored["both_sides_money"])
            out["binary_outcome"] = str(scored["financial_binary_outcome"])
            done += 1
            if done % 20 == 0 or done == len(mixed_indices):
                print(f"Scored {done}/{len(mixed_indices)} mixed rows", flush=True)
    return result


def write_review_queues(root: Path, rows: list[dict[str, str]]) -> tuple[int, int, int]:
    flagged = [
        row for row in rows
        if row["financial_tiebreak_applied"] == "yes" and int(row["unallocated_money_units"] or 0) > 0
    ]
    high_risk = [
        row for row in rows
        if row["financial_tiebreak_applied"] == "yes"
        and (int(row["unallocated_money_units"] or 0) > 0 or row.get("both_sides_money") == "yes")
    ]
    outcome_changing = [
        row for row in high_risk
        if row["binary_outcome"] == "employer_win" or row.get("both_sides_money") == "yes"
    ]
    fields = [
        "year", "era_citation", "case_name", "pdf_url", "original_legal_outcome",
        "employee_money_awarded", "employee_money_adverse", "observable_net_money",
        "binary_outcome", "both_sides_money", "unallocated_money_units",
        "financial_evidence", "unallocated_money_evidence",
    ]
    for name, selected in (
        ("mixed_financial_review_queue.csv", flagged),
        ("mixed_financial_high_risk.csv", high_risk),
        ("mixed_financial_outcome_changing_review.csv", outcome_changing),
    ):
        with (root / "output" / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows({key: row.get(key, "") for key in fields} for row in selected)
    return len(flagged), len(high_risk), len(outcome_changing)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    rows = resolve_parallel(root, max(1, min(args.workers, 12)))
    target = root / "output" / "combined_2020_2025_binary_classification.csv"
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    mixed = [row for row in rows if row["financial_tiebreak_applied"] == "yes"]
    employee = sum(row["binary_outcome"] == "employee_win" for row in mixed)
    employer = sum(row["binary_outcome"] == "employer_win" for row in mixed)
    unallocated, high_risk, outcome_changing = write_review_queues(root, rows)
    print(f"Resolved {len(mixed)} mixed rows: {employee} employee wins, {employer} employer wins", flush=True)
    print(f"Materially unallocated money rows: {unallocated}", flush=True)
    print(f"High-risk monetary rows (unallocated or both-sides): {high_risk}", flush=True)
    print(f"Outcome-changing review rows: {outcome_changing}", flush=True)


if __name__ == "__main__":
    main()
