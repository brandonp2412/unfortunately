#!/usr/bin/env python3
"""Canonical ERA determination identity helpers."""
from __future__ import annotations

import re

PATH_YEAR_RE = re.compile(r"/(20\d{2})/")
MODERN_ERA_PDF_RE = re.compile(
    r"/(20\d{2})[-_]NZERA(?:[-_]([A-Za-z]+))?[-_](\d+)(?:[-_][A-Za-z0-9]+)*\.pdf(?:[?#]|$)",
    re.I,
)
LEGACY_ERA_PDF_RE = re.compile(r"/([a-z]{2})-(\d+[a-z]?)[-_](\d{2})\.pdf(?:[?#]|$)", re.I)


def _path_year(url: str) -> int | None:
    match = PATH_YEAR_RE.search(url or "")
    return int(match.group(1)) if match else None


def _validated_source_year(url: str, source_year: int) -> int:
    path_year = _path_year(url)
    if path_year is not None and path_year != source_year:
        raise ValueError(f"ERA PDF URL year mismatch: {url}")
    return source_year


def determination_year_from_pdf_url(url: str) -> int | None:
    """Return the determination year encoded by an ERA PDF URL."""
    modern = MODERN_ERA_PDF_RE.search(url or "")
    if modern:
        return _validated_source_year(url, int(modern.group(1)))
    legacy = LEGACY_ERA_PDF_RE.search(url or "")
    if legacy:
        return _validated_source_year(url, 2000 + int(legacy.group(3)))
    return _path_year(url)


def citation_from_pdf_url(url: str) -> str:
    """Return the ERA citation encoded in a modern/regional or legacy source PDF URL."""
    modern = MODERN_ERA_PDF_RE.search(url or "")
    if modern:
        year, venue, number = modern.groups()
        _validated_source_year(url, int(year))
        venue_part = f" {venue.title()}" if venue else ""
        return f"{year} NZERA{venue_part} {int(number)}"

    legacy = LEGACY_ERA_PDF_RE.search(url or "")
    if legacy:
        venue, number, short_year = legacy.groups()
        _validated_source_year(url, 2000 + int(short_year))
        return f"{venue.upper()} {number.upper()}/{short_year}"
    return ""


def canonical_citation(stored: str, pdf_url: str) -> str:
    """Prefer source URL identity; fall back to the stored parsed citation."""
    return citation_from_pdf_url(pdf_url) or " ".join((stored or "").split())
