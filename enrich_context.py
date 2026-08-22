#!/usr/bin/env python3
"""Add explicitly stated worker/workplace context to the combined export.

This is deliberately conservative: no ethnicity, gender, salary, occupation,
or other attribute is inferred from a name, pronoun, employer, or job title.
Unstated facts are recorded as ``not_stated`` and every non-empty extraction
gets a short source excerpt for audit.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "output" / "combined_2020_2025_full_classification.csv"
TARGET = ROOT / "output" / "combined_2020_2025_context_enriched.csv"

ETHNICITY = re.compile(
    r"\b(M[aā]ori|P[aā]keh[aā]|Samoan|Tongan|Niuean|Cook Island(?:er| Māori)?|Indian|Chinese|Korean|Filipino|Fijian|Pacific Island(?:er)?|Asian|European|African|M[eē]tisse?)\b",
    re.I,
)
SALARY = re.compile(
    r"(?P<prefix>(?:salary|wage|pay|rate|remuneration|earned)\D{0,35})"
    r"(?P<amount>\$\s?[0-9][0-9,]*(?:\.[0-9]+)?)\s*"
    r"(?:(?:per\s+)?(?P<unit>hour|hr|week|fortnight|month|year|annum|p\.a\.))",
    re.I,
)
GENDER = re.compile(r"\b(male|female|man|woman|non[- ]binary|gender diverse)\b", re.I)


def text_for(row: dict[str, str]) -> str:
    candidates = [ROOT / row.get("local_text", "")]
    year = row.get("year", "")
    candidates.append(ROOT / "years" / year / row.get("local_text", ""))
    for path in candidates:
        if path.exists():
            return path.read_text(errors="replace")
    return ""


def first_value(pattern: re.Pattern[str], text: str) -> tuple[str, str]:
    match = pattern.search(text)
    if not match:
        return "not_stated", ""
    start = max(0, match.start() - 90)
    end = min(len(text), match.end() + 90)
    return match.group(1), re.sub(r"\s+", " ", text[start:end]).strip()


def context_value(pattern: re.Pattern[str], text: str) -> tuple[str, str]:
    value, excerpt = first_value(pattern, text)
    return value.lower() if value != "not_stated" else value, excerpt


def party_context_value(pattern: re.Pattern[str], text: str) -> tuple[str, str]:
    """Accept an attribute only when its nearby text names the employee side."""
    for match in pattern.finditer(text):
        window = text[max(0, match.start() - 220):match.end() + 100].lower()
        if re.search(r"\b(employee|claimant|applicant|worker)\b", window):
            excerpt = re.sub(r"\s+", " ", window).strip()
            return match.group(1).lower(), excerpt
    return "not_stated", ""


def salary_values(text: str) -> tuple[str, str, str, str, str, str]:
    matches = list(SALARY.finditer(text))
    if not matches:
        return "not_stated", "not_stated", "", "not_stated", "not_stated", "not_stated"
    raw_values = []
    annual_values = []
    for match in matches[:20]:
        amount = float(match.group("amount").replace("$", "").replace(",", "").strip())
        unit = (match.group("unit") or "").lower()
        multiplier = {"hour": 40 * 52, "hr": 40 * 52, "week": 52,
                      "fortnight": 26, "month": 12, "year": 1,
                      "annum": 1, "p.a.": 1}.get(unit)
        raw_values.append(amount)
        if multiplier is not None:
            annual_values.append(amount * multiplier)
    raw_text = "; ".join(m.group(0) for m in matches[:5])
    return (str(min(raw_values)), str(max(raw_values)), raw_text,
            str(min(annual_values)), str(max(annual_values)), "annualized_nzd_assumed")


def collar(text: str) -> tuple[str, str]:
    groups = {
        "blue_collar": r"\b(builder|carpenter|mechanic|driver|labourer|laborer|cleaner|warehouse|factory|machinist|tradesperson|plumber|electrician)\b",
        "white_collar": r"\b(manager|accountant|engineer|consultant|analyst|administrator|office|lawyer|teacher|professional|executive)\b",
        "pink_collar": r"\b(nurse|caregiver|care worker|retail assistant|receptionist|childcare|hospitality|hairdresser)\b",
    }
    for label, pattern in groups.items():
        match = re.search(pattern, text, re.I)
        if match:
            excerpt = re.sub(r"\s+", " ", text[max(0, match.start() - 80):match.end() + 100]).strip()
            return label, excerpt
    return "not_stated", ""


def industry(text: str) -> tuple[str, str]:
    groups = {
        "healthcare": r"\b(hospital|healthcare|health care|rest home|aged care|nursing home|medical)\b",
        "education": r"\b(school|university|college|early childhood|kindergarten|education)\b",
        "hospitality": r"\b(hotel|restaurant|cafe|caf[eé]|bar|hospitality)\b",
        "construction": r"\b(construction|building site|builder|civil works)\b",
        "retail": r"\b(retail|shop|store|supermarket)\b",
        "transport": r"\b(transport|trucking|logistics|courier|taxi)\b",
        "public_sector": r"\b(council|ministry|government department|public service|crown)\b",
    }
    for label, pattern in groups.items():
        match = re.search(pattern, text, re.I)
        if match:
            excerpt = re.sub(r"\s+", " ", text[max(0, match.start() - 80):match.end() + 100]).strip()
            return label, excerpt
    return "not_stated", ""


def representation(text: str) -> tuple[str, str]:
    # Party attribution is not reliable in every PDF, so record one
    # side-agnostic representation signal rather than assigning it to both
    # employee and employer.
    pattern = re.compile(r"\b(counsel|solicitor|lawyer|union representative|advocate|self[- ]represented)\b", re.I)
    match = pattern.search(text)
    if not match:
        return "not_stated", ""
    excerpt = re.sub(r"\s+", " ", text[max(0, match.start() - 100):match.end() + 120]).strip()
    value = "self_represented" if "self" in match.group(0).lower() else "professional_or_union_representative"
    return value, excerpt


def main() -> None:
    with SOURCE.open(newline="") as f:
        rows = list(csv.DictReader(f))
    additions = [
        "employee_ethnicity_stated", "employee_ethnicity_source", "employee_gender_stated", "employee_gender_source",
        "salary_min_numeric", "salary_max_numeric", "salary_text_stated",
        "salary_annual_min_nzd_assumed", "salary_annual_max_nzd_assumed", "salary_normalization_status",
        "occupation_collar_category", "collar_source",
        "industry_category", "industry_source", "representation_stated_in_decision", "representation_source",
        "attribute_extraction_status",
    ]
    for row in rows:
        text = text_for(row)
        ethnicity, ethnicity_source = party_context_value(ETHNICITY, text)
        gender, gender_source = party_context_value(GENDER, text)
        salary_min, salary_max, salary_text, annual_min, annual_max, salary_status = salary_values(text)
        collar_value, collar_source = collar(text)
        industry_value, industry_source = industry(text)
        rep, rep_source = representation(text)
        row.update({
            "employee_ethnicity_stated": ethnicity,
            "employee_ethnicity_source": ethnicity_source,
            "employee_gender_stated": gender,
            "employee_gender_source": gender_source,
            "salary_min_numeric": salary_min,
            "salary_max_numeric": salary_max,
            "salary_text_stated": salary_text,
            "salary_annual_min_nzd_assumed": annual_min,
            "salary_annual_max_nzd_assumed": annual_max,
            "salary_normalization_status": salary_status,
            "occupation_collar_category": collar_value,
            "collar_source": collar_source,
            "industry_category": industry_value,
            "industry_source": industry_source,
            "representation_stated_in_decision": rep,
            "representation_source": rep_source,
            "attribute_extraction_status": "regex_initial_pass_requires_review",
        })
    fields = list(rows[0]) if rows else []
    for field in additions:
        if field not in fields:
            fields.append(field)
    with TARGET.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {TARGET}")


if __name__ == "__main__":
    main()
