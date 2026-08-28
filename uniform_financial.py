#!/usr/bin/env python3
"""Score every substantive ERA dismissal determination with one financial rule.

Primary outcome rule (uniform for 2010-2025):
- positive observable money/remedy flow to the employee => employee_win
- zero observable recovery or money flowing only against the employee => employer_win
- if money flows both ways, net the quantified final orders and flag for source audit

The legal merits outcome is retained separately. Private legal fees not stated in
public determinations are not invented. The parser is deliberately conservative:
ambiguous order text is surfaced for direct source judgment rather than silently
forced into a result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

from apply_financial_audit import AUDITED_CONFIRMED, AUDITED_OVERRIDES, normalize_citation

MONEY_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)")
CLAIM_RE = re.compile(r"\b(?:claim(?:ed|s)?|sought|seeks?|asking for|requested|proposed|offer(?:ed)?)\b", re.I)
NEGATION_RE = re.compile(
    r"\b(?:not be reimbursed|not entitled|no (?:monetary )?(?:award|remedy)|"
    r"decline(?:d)? to award|decline(?:d)? to order|claim .*?(?:fails|dismissed|not made out)|"
    r"no order (?:is )?made)\b",
    re.I,
)
ORDER_VERB_RE = re.compile(r"\b(?:ordered|order|must pay|shall pay|is to pay|are to pay|I award|we award)\b", re.I)
MONEY_BENEFIT_RE = re.compile(
    r"\b(?:compensation|lost wages?|lost remuneration|reimbursement|arrears|wage arrears|"
    r"holiday pay|notice pay|backpay|back pay|remuneration|disbursements?|filing fee|costs?)\b",
    re.I,
)
PENALTY_RE = re.compile(r"\bpenalt(?:y|ies)\b", re.I)
CROWN_RE = re.compile(r"\b(?:crown|authority(?:'s)? (?:bank )?account|MBIE|IRD)\b", re.I)
QUESTION_RE = re.compile(r"^\s*(?:issue\s*[:\-]?\s*)?should\b|\?$", re.I)
ROLE_EMPLOYEE_RE = re.compile(r"\b(?:applicant|employee|claimant|worker)\b", re.I)
ROLE_EMPLOYER_RE = re.compile(r"\b(?:respondent|employer|company|business)\b", re.I)

STOPWORDS = {
    "the", "and", "of", "for", "new", "zealand", "limited", "ltd", "pty",
    "company", "incorporated", "trust", "board", "services", "service",
    "group", "holdings", "first", "second", "applicant", "respondent",
    "trading", "trades", "t/a", "department", "chief", "executive",
}


def clean(text: str) -> str:
    return " ".join((text or "").split())


def money_value(raw: str) -> float:
    return float(raw.replace(",", ""))


def party_tokens(name: str) -> tuple[set[str], set[str]]:
    parts = re.split(r"\s+v\s+", name or "", maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return set(), set()

    def tokens(part: str) -> set[str]:
        values = set(re.findall(r"[a-z][a-z'-]{2,}", part.lower()))
        return {v for v in values if len(v) >= 4 and v not in STOPWORDS}

    return tokens(parts[0]), tokens(parts[1])


def contains_party(text: str, tokens: set[str]) -> bool:
    lower = text.lower()
    return bool(tokens) and any(re.search(rf"\b{re.escape(token)}\b", lower) for token in tokens)


def order_window(text: str) -> str:
    lower = text.lower()
    starts: list[int] = []
    for pattern in (
        r"\n\s*orders?\s*\n",
        r"\n\s*remed(?:y|ies)\s*\n",
        r"\n\s*conclusion\s*\n",
        r"\n\s*determination\s*\n",
        r"\n\s*result\s*\n",
    ):
        starts.extend(m.start() for m in re.finditer(pattern, lower))
    if starts:
        start = max(starts)
        if len(text) - start >= 700:
            return text[start:]
    return text[-26000:]


def units(text: str) -> list[str]:
    text = text.replace("\r", "\n")
    parts = re.split(r"\n\s*\n|(?<=[.;:?])\s+(?=[A-Z\[])|(?=\[\d+\])", text)
    return [clean(part) for part in parts if clean(part)]


def explicit_named_payment(unit: str, case_name: str) -> str:
    employee, employer = party_tokens(case_name)
    compact = clean(unit)

    # "I order Alice to pay Bob ..."
    match = re.search(r"\b(?:I|we)\s+order\s+(.{1,140}?)\s+to\s+pay\s+(.{0,260})", compact, re.I)
    if match:
        payer, tail = match.group(1), match.group(2)
        if contains_party(payer, employee):
            return "negative"
        if contains_party(tail, employee):
            return "positive"
        if contains_party(tail, employer):
            return "negative"
        if contains_party(payer, employer):
            if CROWN_RE.search(tail) and not contains_party(tail, employee):
                return "neutral"
            if MONEY_BENEFIT_RE.search(tail):
                return "positive"

    # "Alice is ordered to pay Bob ..."
    match = re.search(
        r"(.{1,180}?)(?:is ordered to pay|are ordered to pay|must pay|shall pay|is to pay|are to pay)(.{0,280})",
        compact,
        re.I,
    )
    if match:
        payer, tail = match.group(1), match.group(2)
        if contains_party(payer, employee):
            return "negative"
        if contains_party(tail, employee):
            return "positive"
        if contains_party(tail, employer):
            return "negative"
        if contains_party(payer, employer):
            if CROWN_RE.search(tail) and not contains_party(tail, employee):
                return "neutral"
            if MONEY_BENEFIT_RE.search(tail):
                return "positive"
    return "neutral"


def direction(unit: str, case_name: str) -> str:
    """Return positive, negative or neutral for employee money flow."""
    s = clean(unit)
    lower = s.lower()
    explicit = bool(ORDER_VERB_RE.search(s))

    if NEGATION_RE.search(s):
        return "neutral"
    if QUESTION_RE.search(s) and not explicit:
        return "neutral"
    if CLAIM_RE.search(s) and not explicit and not re.search(r"\b(?:I|we)\s+(?:award|order)\b", s, re.I):
        return "neutral"

    named = explicit_named_payment(s, case_name)
    if named != "neutral":
        return named

    # Role-based adverse orders take precedence.
    if re.search(r"\b(?:applicant|employee|claimant|worker)\b.{0,110}\b(?:ordered|must|shall|is to|are to)\b.{0,45}\bpay\b", lower):
        return "negative"
    if re.search(r"\bcosts?\b.{0,90}\b(?:against|payable by|awarded against)\b.{0,60}\b(?:applicant|employee|claimant)\b", lower):
        return "negative"
    if re.search(r"\b(?:applicant|employee|claimant)\b.{0,90}\bpay(?:able)?\b.{0,90}\b(?:respondent|employer)\b", lower):
        return "negative"

    # Explicit recipient beats payer. Employer penalties to the Crown are neutral.
    if re.search(r"\b(?:respondent|employer)\b.{0,120}\b(?:ordered|must|shall|is to|are to)\b.{0,50}\bpay\b.{0,120}\b(?:applicant|employee|claimant)\b", lower):
        return "positive"
    if re.search(r"\b(?:awarded|payable|payment)\b.{0,60}\b(?:to|in favour of)\b.{0,50}\b(?:applicant|employee|claimant)\b", lower):
        return "positive"
    if re.search(r"\b(?:respondent|employer)\b.{0,100}\b(?:ordered|must|shall|is to|are to)\b.{0,45}\bpay\b", lower):
        if PENALTY_RE.search(s) and CROWN_RE.search(s) and not ROLE_EMPLOYEE_RE.search(s):
            return "neutral"
        if MONEY_BENEFIT_RE.search(s) and not (PENALTY_RE.search(s) and not ROLE_EMPLOYEE_RE.search(s)):
            return "positive"

    # Final remedy language without an explicit payer. This is employee-positive
    # unless it is merely a claim/question/negated award.
    if re.search(r"\b(?:I|we)\s+award\b", s, re.I) and MONEY_BENEFIT_RE.search(s):
        return "positive"
    if re.search(r"\b(?:entitled to|award(?:ed)?|award of)\b", s, re.I) and MONEY_BENEFIT_RE.search(s):
        return "positive"
    if MONEY_BENEFIT_RE.search(s) and MONEY_RE.search(s) and not CLAIM_RE.search(s):
        # Costs need a beneficiary/payer; other remedy heads naturally accrue to employee.
        if re.search(r"\bcosts?\b", lower) and not re.search(r"\b(?:in favour of|to|against|payable by|ordered to pay)\b", lower):
            return "neutral"
        if PENALTY_RE.search(s) and not ROLE_EMPLOYEE_RE.search(s):
            return "neutral"
        return "positive"
    return "neutral"


def monetary_signal(unit: str) -> bool:
    return bool(MONEY_BENEFIT_RE.search(unit) or PENALTY_RE.search(unit) or re.search(r"\bpay(?:ment|able)?\b", unit, re.I))


def score_text(text: str, case_name: str) -> dict[str, object]:
    window = order_window(text)
    positive_entries: list[tuple[float, str]] = []
    negative_entries: list[tuple[float, str]] = []
    positive_nonquant: list[str] = []
    negative_nonquant: list[str] = []
    unallocated: list[str] = []

    for unit in units(window):
        d = direction(unit, case_name)
        values = [money_value(raw) for raw in MONEY_RE.findall(unit)]
        if values:
            if d == "positive":
                positive_entries.extend((value, unit) for value in values)
            elif d == "negative":
                negative_entries.extend((value, unit) for value in values)
            elif monetary_signal(unit) and not CLAIM_RE.search(unit) and not NEGATION_RE.search(unit):
                unallocated.append(unit)
        elif monetary_signal(unit) and ORDER_VERB_RE.search(unit):
            if d == "positive":
                positive_nonquant.append(unit)
            elif d == "negative":
                negative_nonquant.append(unit)
            elif not CLAIM_RE.search(unit) and not NEGATION_RE.search(unit):
                unallocated.append(unit)

    def dedupe(entries: list[tuple[float, str]]) -> list[tuple[float, str]]:
        seen: set[tuple[float, str]] = set()
        out: list[tuple[float, str]] = []
        for amount, unit in entries:
            para = re.search(r"\[(\d+)\]", unit)
            normalized = re.sub(r"\s+", " ", unit.lower())
            key = (amount, f"p{para.group(1)}" if para else normalized[:400])
            if key not in seen:
                seen.add(key)
                out.append((amount, unit))
        return out

    positive_entries = dedupe(positive_entries)
    negative_entries = dedupe(negative_entries)
    pos = sum(amount for amount, _ in positive_entries)
    neg = sum(amount for amount, _ in negative_entries)
    has_pos = bool(positive_entries or positive_nonquant)
    has_neg = bool(negative_entries or negative_nonquant)

    if has_pos and not has_neg:
        outcome = "employee_win"
    elif has_neg and not has_pos:
        outcome = "employer_win"
    elif not has_pos and not has_neg:
        outcome = "employer_win"
    else:
        # A source audit will finalize both-direction cases. The provisional
        # numeric net is still useful for triage when all material amounts are quantified.
        outcome = "employee_win" if pos - neg > 0 else "employer_win"

    evidence = [u for _, u in positive_entries + negative_entries] + positive_nonquant + negative_nonquant
    return {
        "employee_money_awarded": pos,
        "employee_money_adverse": neg,
        "observable_net_money": pos - neg,
        "positive_money_signal": has_pos,
        "negative_money_signal": has_neg,
        "financial_binary_outcome": outcome,
        "both_sides_money": has_pos and has_neg,
        "unallocated_money_units": len(dict.fromkeys(unallocated)),
        "financial_evidence": " || ".join(dict.fromkeys(evidence))[-9000:],
        "unallocated_money_evidence": " || ".join(dict.fromkeys(unallocated))[-9000:],
        "order_excerpt": clean(window[-14000:]),
    }


def fetch_pdf(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "ERA-research/1.0 (public-decision-analysis)"})
    last_error: Exception | None = None
    for _ in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                target.write_bytes(response.read())
            return
        except Exception as exc:  # retry transient public-server failures
            last_error = exc
    assert last_error is not None
    raise last_error


def pdf_text(pdf: Path, txt: Path) -> str:
    txt.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=False)
    if not txt.exists() or txt.stat().st_size == 0:
        raise RuntimeError(f"pdftotext produced no text for {pdf} (status {completed.returncode})")
    return txt.read_text(errors="replace")


def load_year(root: Path, year: int) -> list[dict[str, str]]:
    if year <= 2019:
        path = root / "years" / str(year) / "output" / f"{year}_strict_classification.csv"
        rows = list(csv.DictReader(path.open(newline="")))
        return [
            {
                "year": row["year"],
                "source_row_id": row.get("search_result_number", ""),
                "era_citation": row.get("era_citation", ""),
                "case_name": row.get("case_name", ""),
                "pdf_url": row["pdf_url"],
                "legal_outcome": row["final_outcome"],
            }
            for row in rows
            if row.get("included_in_merits_denominator") == "yes"
        ]

    path = root / "output" / "combined_2020_2025_full_classification.csv"
    rows = list(csv.DictReader(path.open(newline="")))
    return [
        {
            "year": row["year"],
            "source_row_id": row.get("source_row_index", row.get("search_result_number", "")),
            "era_citation": row.get("era_citation", ""),
            "case_name": row.get("case_name", ""),
            "pdf_url": row["pdf_url"],
            "legal_outcome": row["classified_outcome"],
        }
        for row in rows
        if row.get("year") == str(year) and row.get("classified_outcome") != "excluded"
    ]


def score_row(root: Path, row: dict[str, str]) -> dict[str, str]:
    digest = hashlib.sha1(row["pdf_url"].encode()).hexdigest()
    cache = root / ".uniform-financial-cache" / row["year"]
    pdf = cache / "pdf" / f"{digest}.pdf"
    txt = cache / "text" / f"{digest}.txt"
    if not pdf.exists():
        fetch_pdf(row["pdf_url"], pdf)
    text = txt.read_text(errors="replace") if txt.exists() else pdf_text(pdf, txt)
    scored = score_text(text, row.get("case_name", ""))

    out = dict(row)
    out.update({
        "employee_money_awarded": f"{float(scored['employee_money_awarded']):.2f}",
        "employee_money_adverse": f"{float(scored['employee_money_adverse']):.2f}",
        "observable_net_money": f"{float(scored['observable_net_money']):.2f}",
        "positive_money_signal": "yes" if scored["positive_money_signal"] else "no",
        "negative_money_signal": "yes" if scored["negative_money_signal"] else "no",
        "financial_binary_outcome": str(scored["financial_binary_outcome"]),
        "both_sides_money": "yes" if scored["both_sides_money"] else "no",
        "unallocated_money_units": str(scored["unallocated_money_units"]),
        "financial_evidence": str(scored["financial_evidence"]),
        "unallocated_money_evidence": str(scored["unallocated_money_evidence"]),
        "order_excerpt": str(scored["order_excerpt"]),
        "prior_financial_audit": "none",
        "parser_audit_reason": "",
    })

    key = normalize_citation(row.get("era_citation", ""))
    override = AUDITED_OVERRIDES.get(key)
    if override is not None:
        awarded = float(override["employee_money_awarded"])
        adverse = float(override["employee_money_adverse"])
        out.update({
            "employee_money_awarded": f"{awarded:.2f}",
            "employee_money_adverse": f"{adverse:.2f}",
            "observable_net_money": f"{awarded - adverse:.2f}",
            "positive_money_signal": "yes" if awarded > 0 else "no",
            "negative_money_signal": "yes" if adverse > 0 else "no",
            "financial_binary_outcome": str(override["binary_outcome"]),
            "prior_financial_audit": "audited_override: " + str(override["note"]),
        })
    elif key in AUDITED_CONFIRMED:
        out["prior_financial_audit"] = "audited_confirmed: " + AUDITED_CONFIRMED[key]

    reasons: list[str] = []
    if out["prior_financial_audit"] == "none":
        if out["both_sides_money"] == "yes":
            reasons.append("both_sides_money")
        if int(out["unallocated_money_units"] or 0) > 0:
            reasons.append("unallocated_money")
        if out["legal_outcome"] == "employee_win" and out["financial_binary_outcome"] == "employer_win":
            reasons.append("legal_employee_win_financial_loss")
        if out["legal_outcome"] == "employer_win" and out["financial_binary_outcome"] == "employee_win":
            reasons.append("legal_employer_win_financial_win")
        if out["legal_outcome"] == "mixed_unclear" and out["positive_money_signal"] == "no" and out["negative_money_signal"] == "no":
            reasons.append("mixed_zero_recovery")
    out["parser_audit_reason"] = ";".join(dict.fromkeys(reasons))
    return out


def run_year(root: Path, year: int, workers: int) -> list[dict[str, str]]:
    source = load_year(root, year)
    result: list[dict[str, str] | None] = [None] * len(source)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(score_row, root, row): i for i, row in enumerate(source)}
        done = 0
        for future in as_completed(futures):
            result[futures[future]] = future.result()
            done += 1
            if done % 25 == 0 or done == len(source):
                print(f"{year}: scored {done}/{len(source)} substantive determinations", flush=True)
    return [row for row in result if row is not None]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 2010 <= args.year <= 2025:
        raise SystemExit("year must be 2010-2025")
    root = args.root.resolve()
    rows = run_year(root, args.year, min(max(args.workers, 1), 8))
    target_dir = root / "output" / "uniform_financial"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{args.year}.csv"
    if not rows:
        raise SystemExit(f"no substantive rows for {args.year}")
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    flagged = sum(bool(row["parser_audit_reason"]) for row in rows)
    print(f"{args.year}: wrote {len(rows)} rows; {flagged} require direct audit", flush=True)


if __name__ == "__main__":
    main()
