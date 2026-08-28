#!/usr/bin/env python3
"""Resolve review-routed ERA merits cases to binary financial outcomes.

Existing employee/employer legal outcomes pass through unchanged. Review-routed
merits cases use observable monetary orders: employee-side recovery minus money
or costs ordered against the employee. A positive net is an employee win; zero
or negative is an employer win.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

MONEY_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)")
ROLE_EMPLOYEE = r"(?:applicant|employee|claimant|worker)"
ROLE_EMPLOYER = r"(?:respondent|employer|company|business)"


def money_value(raw: str) -> float:
    return float(raw.replace(",", ""))


def clean(text: str) -> str:
    return " ".join((text or "").split())


def order_window(text: str) -> str:
    """Prefer the final remedies/orders portion to avoid claimed amounts."""
    lower = text.lower()
    starts: list[int] = []
    for pattern in (
        r"\n\s*orders?\s*\n",
        r"\n\s*remed(?:y|ies)\s*\n",
        r"\n\s*conclusion\s*\n",
        r"\n\s*determination\s*\n",
    ):
        starts.extend(m.start() for m in re.finditer(pattern, lower))
    if starts:
        start = max(starts)
        # If the last heading is too close to EOF (e.g. footer/table of contents),
        # retain a wider tail instead.
        if len(text) - start >= 1200:
            return text[start:]
    return text[-18000:]


def units(text: str) -> list[str]:
    compact = text.replace("\r", "\n")
    parts = re.split(r"\n\s*\n|(?<=[.;:])\s+(?=[A-Z\[])|(?=\[\d+\])", compact)
    return [clean(part) for part in parts if "$" in part and clean(part)]


def direction(unit: str) -> str:
    """Return employee_positive, employee_negative, or neutral."""
    s = unit.lower()

    # Explicit adverse orders against the employee/applicant take precedence.
    if re.search(ROLE_EMPLOYEE + r".{0,90}(?:ordered|order|must|is to|shall).{0,35}pay", s):
        return "employee_negative"
    if re.search(r"costs?.{0,70}(?:against|payable by|awarded against).{0,50}" + ROLE_EMPLOYEE, s):
        return "employee_negative"
    if re.search(ROLE_EMPLOYEE + r".{0,70}(?:pay|payable).{0,70}" + ROLE_EMPLOYER, s):
        return "employee_negative"

    # Explicit payments by the employer/respondent are employee-positive.
    if re.search(ROLE_EMPLOYER + r".{0,90}(?:ordered|order|must|is to|shall).{0,35}pay", s):
        return "employee_positive"
    if re.search(ROLE_EMPLOYER + r".{0,70}(?:pay|payable).{0,70}" + ROLE_EMPLOYEE, s):
        return "employee_positive"
    if re.search(r"(?:awarded|payable|payment).{0,45}(?:to|in favour of).{0,35}" + ROLE_EMPLOYEE, s):
        return "employee_positive"

    # Remedy language in an orders/remedies window is normally money for the
    # employee unless the unit expressly says otherwise.
    if re.search(r"\b(?:lost wages?|lost remuneration|compensation|reimbursement|arrears|holiday pay|wage arrears|notice pay)\b", s):
        if not re.search(r"\b(?:claim(?:ed)?|sought|seeks?|asking for)\b", s):
            return "employee_positive"

    # Costs language with an explicit applicant/employee beneficiary.
    if "cost" in s and re.search(r"(?:to|in favour of).{0,35}" + ROLE_EMPLOYEE, s):
        return "employee_positive"
    return "neutral"


def score_text(text: str) -> dict[str, object]:
    window = order_window(text)
    positives: list[tuple[float, str]] = []
    negatives: list[tuple[float, str]] = []
    neutrals: list[str] = []
    for unit in units(window):
        amounts = [money_value(value) for value in MONEY_RE.findall(unit)]
        if not amounts:
            continue
        d = direction(unit)
        if d == "employee_positive":
            positives.extend((amount, unit) for amount in amounts)
        elif d == "employee_negative":
            negatives.extend((amount, unit) for amount in amounts)
        else:
            neutrals.append(unit)

    # Deduplicate exact repeated order sentences/amounts.
    positives = list(dict.fromkeys(positives))
    negatives = list(dict.fromkeys(negatives))
    positive_total = sum(amount for amount, _ in positives)
    negative_total = sum(amount for amount, _ in negatives)
    net = positive_total - negative_total
    evidence_units = [u for _, u in positives + negatives]
    if not evidence_units:
        evidence_units = neutrals[-3:]
    return {
        "employee_money_awarded": positive_total,
        "employee_money_adverse": negative_total,
        "observable_net_money": net,
        "financial_binary_outcome": "employee_win" if net > 0 else "employer_win",
        "financial_evidence": " || ".join(evidence_units[-6:])[:5000],
        "unallocated_money_units": len(neutrals),
    }


def fetch_pdf(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "ERA-research/1.0 (public-decision-analysis)"})
    with urlopen(request, timeout=90) as response:
        target.write_bytes(response.read())


def pdf_text(pdf: Path, txt: Path) -> str:
    txt.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
    return txt.read_text(errors="replace")


def resolve(root: Path) -> list[dict[str, str]]:
    recent_path = root / "output" / "combined_2020_2025_full_classification.csv"
    rows = list(csv.DictReader(recent_path.open(newline="")))
    result: list[dict[str, str]] = []
    cache = root / ".financial-cache"

    for row in rows:
        out = dict(row)
        original = row["classified_outcome"]
        out["original_legal_outcome"] = original
        out["financial_tiebreak_applied"] = "no"
        out["employee_money_awarded"] = ""
        out["employee_money_adverse"] = ""
        out["observable_net_money"] = ""
        out["financial_evidence"] = ""
        out["unallocated_money_units"] = ""
        out["binary_outcome"] = original

        if original not in {"employee_win", "employer_win", "excluded"}:
            citation = row["era_citation"].replace(" ", "_")
            pdf = cache / "pdf" / f"{citation}.pdf"
            txt = cache / "text" / f"{citation}.txt"
            if not pdf.exists():
                fetch_pdf(row["pdf_url"], pdf)
            text = txt.read_text(errors="replace") if txt.exists() else pdf_text(pdf, txt)
            scored = score_text(text)
            out["financial_tiebreak_applied"] = "yes"
            out["employee_money_awarded"] = f"{scored['employee_money_awarded']:.2f}"
            out["employee_money_adverse"] = f"{scored['employee_money_adverse']:.2f}"
            out["observable_net_money"] = f"{scored['observable_net_money']:.2f}"
            out["financial_evidence"] = str(scored["financial_evidence"])
            out["unallocated_money_units"] = str(scored["unallocated_money_units"])
            out["binary_outcome"] = str(scored["financial_binary_outcome"])
        result.append(out)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    rows = resolve(root)
    target = root / "output" / "combined_2020_2025_binary_classification.csv"
    fields = list(rows[0]) if rows else []
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    resolved = [row for row in rows if row["financial_tiebreak_applied"] == "yes"]
    employee = sum(row["binary_outcome"] == "employee_win" for row in resolved)
    employer = sum(row["binary_outcome"] == "employer_win" for row in resolved)
    neutral_money = sum(int(row["unallocated_money_units"] or 0) > 0 for row in resolved)
    print(f"Resolved {len(resolved)} review-routed rows: {employee} employee wins, {employer} employer wins")
    print(f"Rows with unallocated dollar-bearing order text: {neutral_money}")


if __name__ == "__main__":
    main()
