#!/usr/bin/env python3
"""Acquire pre-2020 ERA search results and build source-review dossiers.

Older ERA determinations use legacy PDF names such as ``aa-528_10.pdf`` alongside
neutral-citation filenames. This module handles both formats, writes the raw
``initial_extraction.csv`` audit table, and builds a manual-review dossier. Final
legal classifications come from the source-review workflow.
"""
from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path
from urllib.parse import urlencode, urljoin

import analyze_era
from build_review_dossier import build as build_review_dossier


BASE = analyze_era.BASE
SEARCH = analyze_era.SEARCH
PDF_RE = re.compile(
    r'href=["\']([^"\']*/assets/elawpdf/(\d{4})/[^"\']+\.pdf)["\']',
    re.I,
)
CITATION_RE = re.compile(r"\[?(\d{4})\]?\s*NZERA\s*(\d+)", re.I)


def extract_pdf_urls_for_year(html: str, year: int) -> list[str]:
    """Return first-seen ERA PDF URLs belonging to the requested year."""
    urls: list[str] = []
    for value, found_year in PDF_RE.findall(html):
        if int(found_year) != year:
            continue
        url = urljoin(BASE, value)
        if url not in urls:
            urls.append(url)
    return urls


def field_citation(text: str, year: int, fallback_stem: str = "") -> str:
    """Extract a neutral citation, or preserve the legacy ERA decision number."""
    match = CITATION_RE.search(text[:4000])
    if match and int(match.group(1)) == year:
        return f"[{year}] NZERA {match.group(2)}"

    filename_match = re.search(rf"{year}[_-]NZERA[_-](\d+)", fallback_stem, re.I)
    if filename_match:
        return f"[{year}] NZERA {filename_match.group(1)}"

    legacy_match = re.search(r"([a-z]{1,4})[-_](\d+[a-z]?)[-_](\d{2})$", fallback_stem, re.I)
    if legacy_match and int(legacy_match.group(3)) == year % 100:
        return f"{legacy_match.group(1).upper()} {legacy_match.group(2).upper()}/{legacy_match.group(3)}"

    return fallback_stem.replace("-", " ").replace("_", " ")


def field_date(text: str, year: int) -> str:
    match = re.search(
        rf"(?:Date of Determination|Determination|Date)\s*:?\s*(\d{{1,2}}\s+[A-Za-z]+\s+{year})",
        text[:5000],
        re.I,
    )
    return match.group(1) if match else ""


def all_result_urls(root: Path, year: int) -> list[str]:
    """Fetch every result page and preserve first-seen unique PDF URLs."""
    urls: list[str] = []
    for start in range(0, 2000, 10):
        params = {
            "Keywords": "unjustified dismissal",
            "DateFrom": f"{year}-01-01",
            "DateTo": f"{year}-12-31",
            "action_doSearch": "Search",
            "start": start,
        }
        page = root / "data" / f"search_page_{start:03d}.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        if not page.exists():
            page.write_bytes(analyze_era.fetch(SEARCH + "?" + urlencode(params)))
            time.sleep(0.15)
        found = extract_pdf_urls_for_year(page.read_text(errors="replace"), year)
        if not found:
            break
        for url in found:
            if url not in urls:
                urls.append(url)
    return urls


def build_corpus(root: Path, year: int) -> None:
    pdf_dir = root / "data" / "pdfs"
    text_dir = root / "data" / "text"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    urls = all_result_urls(root, year)
    rows: list[dict[str, object]] = []
    for number, url in enumerate(urls, 1):
        filename = url.rsplit("/", 1)[-1]
        pdf = pdf_dir / filename
        if not pdf.exists():
            pdf.write_bytes(analyze_era.fetch(url))
            time.sleep(0.1)
        text_path = text_dir / (pdf.stem + ".txt")
        text = analyze_era.pdf_text(pdf, text_path)
        flags = analyze_era.initial_flags(text)
        rows.append({
            "search_result_number": number,
            "era_citation": field_citation(text, year, pdf.stem),
            "case_name": analyze_era.field_case_name(text),
            "decision_date": field_date(text, year),
            "pdf_url": url,
            "local_pdf": str(pdf.relative_to(root)),
            "local_text": str(text_path.relative_to(root)),
            **flags,
            "operative_keyword_snippets": analyze_era.last_mentions(text),
        })

    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    initial = output / "initial_extraction.csv"
    fields = list(rows[0]) if rows else ["search_result_number", "era_citation", "pdf_url"]
    with initial.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    build_review_dossier(root, year)
    print(f"Downloaded/extracted {len(rows)} unique PDFs; wrote {initial}")
    print("No final legal classification was generated; every dossier row requires manual review.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    build_corpus(args.root, args.year)
