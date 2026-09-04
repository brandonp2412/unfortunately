#!/usr/bin/env python3
"""Canonical ERA determination identity helpers."""
from __future__ import annotations

import re

ERA_PDF_RE = re.compile(
    r"/(20\d{2})/(?:[^/?#]*?)(20\d{2})[-_]NZERA[-_](\d+)\.pdf(?:[?#]|$)",
    re.I,
)
ERA_PDF_FALLBACK_RE = re.compile(r"/(20\d{2})[-_]NZERA[-_](\d+)\.pdf(?:[?#]|$)", re.I)


def citation_from_pdf_url(url: str) -> str:
    """Return a stable ``YYYY NZERA N`` citation when encoded in an ERA PDF URL."""
    match = ERA_PDF_RE.search(url or "")
    if match:
        path_year, citation_year, number = match.groups()
        if path_year != citation_year:
            raise ValueError(f"ERA PDF URL year mismatch: {url}")
        return f"{citation_year} NZERA {int(number)}"
    match = ERA_PDF_FALLBACK_RE.search(url or "")
    if match:
        year, number = match.groups()
        return f"{year} NZERA {int(number)}"
    return ""


def canonical_citation(stored: str, pdf_url: str) -> str:
    """Prefer source URL identity; fall back to the stored parsed citation."""
    return citation_from_pdf_url(pdf_url) or " ".join((stored or "").split())
