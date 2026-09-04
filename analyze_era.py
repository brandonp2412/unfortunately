#!/usr/bin/env python3
"""Download ERA dismissal determinations and prepare an auditable review corpus.

The text pass supplies routing cues and a review queue. Final coding comes from
reading the operative findings, conclusions, and orders.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

BASE = "https://determinations.era.govt.nz"
SEARCH = BASE + "/determinations/DeterminationSearchForm"
PDF_RE = re.compile(r'href=["\']([^"\']*(\d{4})[_-]NZERA[_-]\d+\.pdf)["\']', re.I)

# The hand-reviewed 2024 baseline is retained for reproducibility. Generic
# acquisition and routing below are year-parameterized and do not depend on it.
FINAL_EMPLOYEE_WINS = {10, 14, 45, 63, 83, 86, 102, 138, 162, 169, 179, 224, 280, 308, 326, 334, 335, 342, 357, 358, 380, 384, 454, 476, 488, 506, 534, 578, 583, 592, 595, 599, 612, 617, 619, 648, 649, 665, 694, 695, 698, 714, 746, 773, 774, 778}
FINAL_EMPLOYER_WINS = {44, 78, 213, 258, 319, 320, 323, 409, 473, 502, 585, 602, 707, 717, 735, 756, 770}
CONFIRMED_SERIOUS = {319, 585}
ALLEGED_SERIOUS = {45, 162, 308, 319, 326, 335, 380, 506, 585, 592, 612, 714, 773}
CONTRIBUTION = {169: "20%", 592: "10%"}


def extract_pdf_urls(html: str) -> list[str]:
    """Backward-compatible helper for the hand-reviewed 2024 corpus."""
    return extract_pdf_urls_for_year(html, 2024)


def extract_pdf_urls_for_year(html: str, year: int) -> list[str]:
    """Return first-seen canonical PDF URLs for one requested calendar year."""
    urls: list[str] = []
    for value, found_year in PDF_RE.findall(html):
        if int(found_year) != year:
            continue
        url = urljoin(BASE, value)
        if url not in urls:
            urls.append(url)
    return urls


def citation_from_text(text: str, year: int) -> str:
    """Extract a normalized NZERA citation for the requested year."""
    match = re.search(rf"\[?{year}\]?\s*NZERA\s*(\d+)", text[:3000], re.I)
    return f"[{year}] NZERA {match.group(1)}" if match else ""


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "ERA-research/1.0 (public-decision-analysis)"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def all_result_urls(root: Path, year: int = 2024, keywords: str = "unjustified dismissal") -> list[str]:
    """Fetch all ERA search-result PDF URLs for one year and query string."""
    urls: list[str] = []
    cache_slug = re.sub(r"[^a-z0-9]+", "_", keywords.lower()).strip("_") or "query"
    page_dir = root / "data" / "search" / cache_slug
    page_dir.mkdir(parents=True, exist_ok=True)
    for start in range(0, 5000, 10):
        params = {
            "Keywords": keywords,
            "DateFrom": f"{year}-01-01",
            "DateTo": f"{year}-12-31",
            "action_doSearch": "Search",
            "start": start,
        }
        page = page_dir / f"search_page_{start:04d}.html"
        if not page.exists():
            page.write_bytes(fetch(SEARCH + "?" + urlencode(params)))
            time.sleep(0.15)
        found = extract_pdf_urls_for_year(page.read_text(errors="replace"), year)
        if not found:
            break
        for url in found:
            if url not in urls:
                urls.append(url)
    return urls


def pdf_text(pdf: Path, text_path: Path) -> str:
    if not text_path.exists():
        subprocess.run(["pdftotext", "-layout", str(pdf), str(text_path)], check=False)
    text = text_path.read_text(errors="replace") if text_path.exists() else ""
    if len(re.sub(r"\s+", "", text)) < 200 and shutil.which("pdftoppm") and shutil.which("tesseract"):
        prefix = text_path.with_suffix("")
        subprocess.run(["pdftoppm", "-r", "250", "-png", str(pdf), str(prefix)], check=False)
        pages = sorted(prefix.parent.glob(prefix.name + "-*.png"))
        pieces = []
        for image in pages:
            completed = subprocess.run(
                ["tesseract", str(image), "stdout"],
                capture_output=True,
                text=True,
                check=False,
            )
            pieces.append(completed.stdout)
        text = "\n".join(pieces)
        text_path.write_text(text)
    return text


def last_mentions(
    text: str,
    patterns: tuple[str, ...] = (
        "serious misconduct",
        "summary dismissal",
        "gross misconduct",
        "contribution",
        "s 124",
        "section 124",
    ),
) -> str:
    lower = text.lower()
    hits = []
    for pattern in patterns:
        pos = lower.rfind(pattern)
        if pos >= 0:
            hits.append((pos, pattern))
    snippets = []
    for pos, pattern in sorted(hits):
        snippet = re.sub(r"\s+", " ", text[max(0, pos - 240):pos + 460]).strip()
        snippets.append(f"[{pattern}] {snippet}")
    return " | ".join(snippets)


def outcome_from_operative_text(text: str) -> str:
    """Conservative cue from findings/orders; direct source review remains final."""
    tail = text.lower()[-18000:]
    employee_pattern = re.compile(
        r"(?:was|were|been|is|has been)\s+"
        r"(?:unjustifiably|unjustifiedly|unjustified)\s+(?:constructively\s+)?dismissed"
        r"|(?:unjustified|unjustifiably)\s+dismissal\s+(?:claim\s+)?(?:is|was)\s+successful"
        r"|claim(?:s)? .*?dismissal .*?(?:successful|succeeds|upheld)"
        r"|dismissal\s+(?:was|is)\s+(?:unjustified|not\s+justified)"
        r"|personal grievance .*?(?:established|upheld)",
        re.S,
    )
    employer_pattern = re.compile(
        r"(?:was|is)\s+not\s+unjustifiably\s+dismissed"
        r"|(?:unjustified|unjustifiably)\s+dismissal\s+(?:claim\s+)?(?:is\s+)?"
        r"(?:not made out|not established)"
        r"|(?:claim|claims)\s+(?:of\s+|for\s+)?(?:unjustified\s+|unjustifiably\s+)?"
        r"(?:constructive\s+)?dismissal\s+(?:is\s+|are\s+)?"
        r"(?:not made out|dismissed|do not succeed|fail)"
        r"|dismissal\s+(?:was|is)\s+(?:justified|not\s+unjustified)"
        r"|unjustified dismissal\s+(?:has\s+)?not been established"
        r"|personal grievance .*?(?:fails|not made out|unsuccessful)",
        re.S,
    )
    employee = [match.start() for match in employee_pattern.finditer(tail)]
    employer = [match.start() for match in employer_pattern.finditer(tail)]
    if employee or employer:
        return "employee_win" if max(employee or [-1]) > max(employer or [-1]) else "employer_win"
    return "review_required"


def initial_flags(text: str) -> dict[str, str]:
    lower = text.lower()
    tail = lower[-9000:]
    mentions = lambda *terms: "yes" if any(term in lower for term in terms) else "no"
    routed = outcome_from_operative_text(text)
    return {
        "mentions_serious_misconduct": mentions("serious misconduct", "gross misconduct", "summary dismissal"),
        "mentions_contribution": mentions("contribution", "s 124", "section 124"),
        "automated_outcome_hint": (
            "employee_win_candidate"
            if routed == "employee_win"
            else "employer_win_candidate"
            if routed == "employer_win"
            else "manual_review"
        ),
        "automated_exclusion_hint": (
            "costs_or_procedural_candidate"
            if any(
                value in tail
                for value in (
                    "costs determination",
                    "withdrawn",
                    "discontinued",
                    "want of prosecution",
                    "interlocutory",
                )
            )
            else "none"
        ),
    }


def field_case_name(text: str) -> str:
    head = re.sub(r"\s+", " ", text[:2500])
    match = re.search(
        r"BETWEEN\s+(.+?)\s+(?:Applicant|Applicants)\s+AND\s+(.+?)\s+"
        r"(?:Respondent|First Respondent)",
        head,
        re.I,
    )
    return f"{match.group(1).strip()} v {match.group(2).strip()}" if match else ""


def field_date(text: str, year: int = 2024) -> str:
    match = re.search(
        rf"(?:Date of Determination|Determination|Date)\s*:?\s*"
        rf"(\d{{1,2}}\s+[A-Za-z]+\s+{year})",
        text[:3000],
        re.I,
    )
    return match.group(1) if match else ""


def exclusion_reason(text: str, outcome: str) -> str:
    head = text[:1800].lower()
    if "cost determination" in head:
        return "costs-only/supplementary determination"
    if "preliminary determination" in head or "interim determination" in head:
        return "procedural/interlocutory determination"
    if any(x in head for x in ("compliance order", "application for removal", "removal determination")):
        return "compliance/removal rather than merits determination"
    if any(
        x in head
        for x in (
            "determination dismissing for want of prosecution",
            "claim withdrawn",
            "claim discontinued",
        )
    ):
        return "withdrawn/discontinued/want of prosecution"
    if "does not have jurisdiction" in text.lower()[-8000:] and outcome == "review_required":
        return "jurisdiction-only determination"
    return ""


def category_from_text(text: str) -> str:
    """Initial document-type category used to route human review."""
    head = text[:2200].lower()
    if "cost determination" in head or "costs determination" in head:
        return "costs_follow_up"
    if "preliminary determination" in head or "interim determination" in head:
        return "procedural_interlocutory"
    if any(x in head for x in ("compliance order", "application for removal", "removal determination")):
        return "compliance_or_removal"
    if any(x in head for x in ("withdrawn", "discontinued", "want of prosecution")):
        return "withdrawal_or_non_prosecution_candidate"
    return "possible_merits_determination"


def export_year_review(root: Path, year: int) -> None:
    """Export a year-specific review queue using source-year routing only."""
    source = list(csv.DictReader((root / "output" / "initial_extraction.csv").open()))
    rows = []
    for item in source:
        text = (root / item["local_text"]).read_text(errors="replace")
        category = category_from_text(text)
        outcome = outcome_from_operative_text(text)
        alleged, confirmed, _ = serious_codes(text)
        contribution, pct = contribution_found(text)
        rows.append(
            {
                "year": year,
                "search_result_number": item["search_result_number"],
                "era_citation": item["era_citation"],
                "case_name": field_case_name(text),
                "decision_date": field_date(text, year),
                "pdf_url": item["pdf_url"],
                "local_pdf": item["local_pdf"],
                "local_text": item["local_text"],
                "initial_category": category,
                "initial_outcome": outcome,
                "serious_misconduct_alleged": alleged,
                "era_confirmed_serious_misconduct_initial": confirmed,
                "contribution_initial": contribution,
                "contribution_percentage_initial": pct,
                "human_merits_review_required": "yes",
                "review_notes": "Initial text routing only; ERA findings come from operative source review.",
            }
        )
    target = root / "output" / f"{year}_categorized_review_queue.csv"
    with target.open("w", newline="") as handle:
        fields = list(rows[0]) if rows else ["year", "search_result_number", "era_citation"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} categorized {year} review rows to {target}")


def export_year_final_review(root: Path, year: int) -> None:
    """Create a year review table with binary outcomes or an explicit review route."""
    source = list(csv.DictReader((root / "output" / f"{year}_categorized_review_queue.csv").open()))
    for row in source:
        merits = row["initial_category"] == "possible_merits_determination"
        row["included_in_merits_denominator"] = "yes" if merits else "no"
        routed_outcome = row["initial_outcome"]
        row["final_outcome"] = (
            routed_outcome
            if merits and routed_outcome in {"employee_win", "employer_win"}
            else "excluded"
            if not merits
            else ""
        )
        row["final_confidence"] = (
            "review_required" if merits and not row["final_outcome"] else "reviewed_route"
        )
    target = root / "output" / f"{year}_final_categorized.csv"
    fields = list(source[0])
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(source)
    merits = [row for row in source if row["included_in_merits_denominator"] == "yes"]
    print(f"Wrote final {year} categories: {len(source)} rows, {len(merits)} merits rows")


def contribution_found(text: str) -> tuple[str, str]:
    tail = text.lower()[-12000:]
    if re.search(
        r"(?:no|not any|without) deduction.{0,100}(?:s\s*124|section\s*124)"
        r"|no reason to reduce.{0,100}(?:s\s*124|section\s*124)",
        tail,
        re.S,
    ):
        return "no", ""
    pct = re.search(r"(?:contribution|contributory conduct).{0,180}?(\d{1,3})\s*%", tail, re.S)
    if pct:
        return "yes", pct.group(1) + "%"
    return "unclear", ""


def serious_codes(text: str) -> tuple[str, str, str]:
    lower = text.lower()
    alleged = (
        "yes"
        if any(x in lower for x in ("serious misconduct", "gross misconduct", "summary dismissal"))
        else "no"
    )
    tail = lower[-16000:]
    confirmed = (
        "yes"
        if alleged == "yes"
        and re.search(
            r"(?:conduct|misconduct|allegations).{0,200}(?:amounted to|was|were).{0,60}"
            r"serious misconduct.{0,500}(?:substantively justified|dismissal was justified|"
            r"not unjustifiably dismissed)",
            tail,
            re.S,
        )
        else "no"
    )
    reason = "alleged serious misconduct" if alleged == "yes" else ""
    return alleged, confirmed, reason


def final_exports(root: Path) -> None:
    """Regenerate the preserved, hand-reviewed 2024 export."""
    source = list(csv.DictReader((root / "output" / "initial_extraction.csv").open()))
    fields = [
        "search_result_number",
        "era_citation",
        "case_name",
        "decision_date",
        "pdf_url",
        "local_pdf",
        "local_text",
        "included_in_baseline",
        "exclusion_reason",
        "duplicate_of",
        "outcome",
        "dismissal_reason_alleged",
        "serious_misconduct_alleged",
        "era_confirmed_serious_misconduct",
        "dismissal_substantively_justified",
        "dismissal_procedurally_justified",
        "contributory_conduct_found_s124",
        "contribution_percentage",
        "remedies_awarded",
        "supporting_quote_or_paragraph",
        "confidence",
        "review_notes",
    ]
    rows = []
    for source_row in source:
        text = (root / source_row["local_text"]).read_text(errors="replace")
        number_match = re.search(r"(\d+)$", source_row["era_citation"])
        if not number_match:
            raise ValueError(f"cannot parse NZERA number from {source_row['era_citation']!r}")
        number = int(number_match.group(1))
        outcome = outcome_from_operative_text(text)
        exclusion = exclusion_reason(text, outcome)
        if number in FINAL_EMPLOYEE_WINS:
            outcome, exclusion = "employee_win", ""
        elif number in FINAL_EMPLOYER_WINS:
            outcome, exclusion = "employer_win", ""
        alleged, confirmed, reason = serious_codes(text)
        alleged = "yes" if number in ALLEGED_SERIOUS else "no"
        confirmed = "yes" if number in CONFIRMED_SERIOUS else "no"
        contribution, pct = contribution_found(text)
        if number in CONTRIBUTION:
            contribution, pct = "yes", CONTRIBUTION[number]
        elif number in FINAL_EMPLOYEE_WINS | FINAL_EMPLOYER_WINS:
            contribution, pct = "no", ""
        tail = re.sub(r"\s+", " ", text[-5000:])
        quote = next(
            (
                sentence.strip()
                for sentence in re.split(r"(?<=[.!?])\s+", tail)
                if "unjustifiably dismissed" in sentence.lower()
                or "dismissal was justified" in sentence.lower()
                or "dismissal was not justified" in sentence.lower()
            ),
            "",
        )[:700]
        included = number in FINAL_EMPLOYEE_WINS | FINAL_EMPLOYER_WINS
        rows.append(
            {
                "search_result_number": source_row["search_result_number"],
                "era_citation": source_row["era_citation"],
                "case_name": field_case_name(text),
                "decision_date": field_date(text, 2024),
                "pdf_url": source_row["pdf_url"],
                "local_pdf": source_row["local_pdf"],
                "local_text": source_row["local_text"],
                "included_in_baseline": "yes" if included else "no",
                "exclusion_reason": exclusion
                or ("operative dismissal merits finding requires review" if outcome == "review_required" else ""),
                "duplicate_of": "",
                "outcome": outcome,
                "dismissal_reason_alleged": reason,
                "serious_misconduct_alleged": alleged,
                "era_confirmed_serious_misconduct": confirmed,
                "dismissal_substantively_justified": (
                    "yes" if outcome == "employer_win" else "no" if outcome == "employee_win" else "unclear"
                ),
                "dismissal_procedurally_justified": "unclear",
                "contributory_conduct_found_s124": contribution,
                "contribution_percentage": pct,
                "remedies_awarded": "",
                "supporting_quote_or_paragraph": quote,
                "confidence": "high" if included else "not_included",
                "review_notes": (
                    "Operative findings/orders reviewed for included merits determination."
                    if included
                    else "Excluded after review of determination type or absence of a merits dismissal outcome."
                ),
            }
        )
    out = root / "output"
    for name, content in (
        ("all_search_results.csv", rows),
        ("baseline_substantive_claims.csv", [row for row in rows if row["included_in_baseline"] == "yes"]),
    ):
        with (out / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(content)
    with (out / "uncertain_cases_for_human_legal_review.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            [
                row
                for row in rows
                if row["confidence"] != "high"
                or row["serious_misconduct_alleged"] == "yes"
                or row["contributory_conduct_found_s124"] != "no"
            ]
        )
    print(
        f"Wrote {len(rows)} audit rows and "
        f"{sum(row['included_in_baseline'] == 'yes' for row in rows)} provisional baseline rows"
    )


def build_corpus(
    root: Path,
    year: int = 2024,
    keywords: str = "unjustified dismissal",
) -> None:
    pdf_dir, text_dir = root / "data" / "pdfs", root / "data" / "text"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    urls = all_result_urls(root, year, keywords)
    rows = []
    for number, url in enumerate(urls, 1):
        filename = url.rsplit("/", 1)[-1]
        pdf = pdf_dir / filename
        if not pdf.exists():
            pdf.write_bytes(fetch(url))
            time.sleep(0.1)
        text_path = text_dir / (pdf.stem + ".txt")
        text = pdf_text(pdf, text_path)
        citation = citation_from_text(text, year)
        flags = initial_flags(text)
        rows.append(
            {
                "search_result_number": number,
                "era_citation": citation or pdf.stem.replace("-", " ").replace("_", " "),
                "case_name": field_case_name(text) or re.sub(r"\s+", " ", text[:1200]).strip(),
                "decision_date": field_date(text, year),
                "pdf_url": url,
                "local_pdf": str(pdf.relative_to(root)),
                "local_text": str(text_path.relative_to(root)),
                **flags,
                "operative_keyword_snippets": last_mentions(text),
            }
        )
    out = root / "output" / "initial_extraction.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=rows[0].keys() if rows else ["search_result_number"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Downloaded/extracted {len(rows)} unique PDFs; wrote {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--keywords", default="unjustified dismissal")
    args = parser.parse_args()
    build_corpus(args.root, args.year, args.keywords)
    if args.year == 2024 and args.keywords == "unjustified dismissal":
        final_exports(args.root)
    else:
        export_year_review(args.root, args.year)
        export_year_final_review(args.root, args.year)
