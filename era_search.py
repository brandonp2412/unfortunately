#!/usr/bin/env python3
"""ERA determination-search helpers for current result and PDF link formats."""
from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

BASE = "https://determinations.era.govt.nz"
SEARCH = BASE + "/determinations/DeterminationSearchForm"
RESULT_VIEW_RE = re.compile(r'href=["\']([^"\']*/determination/view/\d+)["\']', re.I)
PDF_LINK_RE = re.compile(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', re.I)
PAGE_START_RE = re.compile(r'(?:[?&]|&amp;)start=(\d+)', re.I)
PAGE_SIZE = 10
MAX_START = 5000


def fetch(url: str, attempts: int = 3) -> bytes:
    """Fetch one public ERA page with a bounded timeout and small retry budget."""
    request = Request(url, headers={"User-Agent": "ERA-research/1.0 (public-decision-analysis)"})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=20) as response:
                return response.read()
        except (TimeoutError, URLError):
            if attempt + 1 == attempts:
                raise
            time.sleep(1.0 + attempt)
    raise AssertionError("unreachable")


def extract_search_result_refs(html: str) -> list[str]:
    """Return canonical detail-page/PDF refs from one ERA search-result page."""
    refs: list[str] = []
    for value in RESULT_VIEW_RE.findall(html):
        ref = urljoin(BASE, value)
        if ref not in refs:
            refs.append(ref)
    for value in PDF_LINK_RE.findall(html):
        ref = urljoin(BASE, value)
        if ref not in refs:
            refs.append(ref)
    return refs


def extract_next_start(html: str, current_start: int) -> int | None:
    """Return the smallest advertised pagination offset after the current page."""
    candidates = sorted({int(value) for value in PAGE_START_RE.findall(html) if int(value) > current_start})
    return candidates[0] if candidates else None


def _cache_slug(keywords: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", keywords.lower()).strip("_") or "query"


def all_search_result_refs(root: Path, year: int, keywords: str) -> list[str]:
    """Return every first-seen determination reference for a year/query search.

    Pagination fails closed if a page repeats or stops yielding new result references.
    This prevents a changed/ignored ERA pagination parameter from silently looping to
    the hard limit and being mistaken for a complete search.
    """
    refs: list[str] = []
    page_dir = root / "data" / "search" / _cache_slug(keywords) / str(year)
    page_dir.mkdir(parents=True, exist_ok=True)
    start = 0
    seen_page_results: set[tuple[str, ...]] = set()

    while start < MAX_START:
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
        html = page.read_text(errors="replace")
        found = extract_search_result_refs(html)
        if not found:
            if start == 0 and not re.search(r"\b(?:no results|0 results)\b", html, re.I):
                raise RuntimeError(
                    f"ERA search returned no parseable result links for {year} / {keywords!r}; "
                    "refusing to treat this as a zero-result audit"
                )
            break

        signature = tuple(found)
        if signature in seen_page_results:
            raise RuntimeError(
                f"ERA pagination repeated a result page at start={start} for {year} / {keywords!r}; "
                "refusing to treat a non-advancing search as complete"
            )
        seen_page_results.add(signature)

        before = len(refs)
        for ref in found:
            if ref not in refs:
                refs.append(ref)
        if len(refs) == before:
            raise RuntimeError(
                f"ERA pagination yielded no new results at start={start} for {year} / {keywords!r}; "
                "refusing to treat a non-advancing search as complete"
            )

        if len(found) < PAGE_SIZE:
            break
        advertised_next = extract_next_start(html, start)
        next_start = advertised_next if advertised_next is not None else start + PAGE_SIZE
        if next_start <= start:
            raise RuntimeError(
                f"ERA pagination did not advance from start={start} for {year} / {keywords!r}"
            )
        start = next_start
    else:
        raise RuntimeError(
            f"ERA search exceeded the {MAX_START}-result pagination safety bound for {year} / {keywords!r}"
        )
    return refs


def resolve_pdf_url(ref: str, year: int, root: Path | None = None) -> str:
    """Resolve a search result/detail reference to its determination PDF URL."""
    if re.search(r"\.pdf(?:\?|$)", ref, re.I):
        return ref
    cache: Path | None = None
    if root is not None:
        cache = root / "data" / "detail" / f"{ref.rstrip('/').rsplit('/', 1)[-1]}.html"
        cache.parent.mkdir(parents=True, exist_ok=True)
    if cache is not None and cache.exists():
        html = cache.read_text(errors="replace")
    else:
        payload = fetch(ref)
        if cache is not None:
            cache.write_bytes(payload)
        html = payload.decode(errors="replace")
    links = [urljoin(BASE, value) for value in PDF_LINK_RE.findall(html)]
    if not links:
        raise RuntimeError(f"no PDF link found on ERA determination page {ref}")
    preferred = [
        link for link in links
        if str(year) in link and re.search(r"NZERA", link, re.I)
    ]
    return (preferred or links)[0]


def all_result_pdf_urls(root: Path, year: int, keywords: str) -> list[str]:
    """Search current ERA result pages and resolve each determination to a PDF URL."""
    refs = all_search_result_refs(root, year, keywords)
    urls: list[str] = []
    for ref in refs:
        url = resolve_pdf_url(ref, year, root)
        if url not in urls:
            urls.append(url)
    return urls
