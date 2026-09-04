#!/usr/bin/env python3
"""Resolve queued legal-merits outcomes only from explicit ERA source findings.

This deliberately does not inspect monetary outcomes. A queued determination is
promoted only when a narrow explicit-finding matcher and the broader legal-text
classifier agree inside the final Outcome/Conclusion/Result/Determination/Orders
section of the source determination.
"""
from __future__ import annotations

import argparse
import csv
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from analyze_era import fetch, outcome_from_operative_text, pdf_text
from era_identity import canonical_citation

BINARY = {"employee_win", "employer_win"}
DEFAULT_WORKERS = 6
OPERATIVE_HEADING_RE = re.compile(
    r"(?im)^[ \t]*(?:outcome|conclusion|result|determination|orders?)\b(?:[ \t]*:)?(?:[ \t]*\[\d+\])?"
)

STRICT_EMPLOYEE = re.compile(
    r"(?:dismissal|termination)\s+(?:was|is)\s+(?:unjustified|unjustifiable|not\s+justified)"
    r"|(?:was|were|is|has\s+been)\s+unjustifiably\s+(?:constructively\s+)?dismissed"
    r"|unjustified\s+dismissal\s+(?:claim\s+)?(?:is|was)\s+(?:established|successful|upheld)"
    r"|(?:claim|grievance)\s+(?:for|of)\s+(?:unjustified\s+)?dismissal\s+"
    r"(?:is|was)\s+(?:established|successful|upheld)",
    re.I | re.S,
)
STRICT_EMPLOYER = re.compile(
    r"(?:dismissal|termination)\s+(?:was|is)\s+(?:justified|not\s+unjustified)"
    r"|(?:was|is)\s+not\s+unjustifiably\s+(?:constructively\s+)?dismissed"
    r"|unjustified\s+dismissal\s+(?:claim\s+)?(?:is|was|has\s+been)\s+"
    r"(?:not\s+established|not\s+made\s+out|unsuccessful|dismissed)"
    r"|(?:claim|grievance)\s+(?:for|of)\s+(?:unjustified\s+)?dismissal\s+"
    r"(?:fails|failed|is\s+dismissed|was\s+dismissed|is\s+not\s+made\s+out)",
    re.I | re.S,
)


def normalize_excerpt(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def final_operative_section(text: str) -> str:
    """Return the last explicit operative section in the final 18k source characters."""
    tail = text[-18000:]
    headings = list(OPERATIVE_HEADING_RE.finditer(tail))
    if not headings:
        return ""
    section = tail[headings[-1].start():]
    return section if len(section) >= 40 else ""


def strict_operative_match(text: str) -> tuple[str, str]:
    """Return the last narrow legal-finding cue and its evidence in supplied text."""
    matches: list[tuple[int, int, str]] = []
    for pattern, outcome in (
        (STRICT_EMPLOYEE, "employee_win"),
        (STRICT_EMPLOYER, "employer_win"),
    ):
        for match in pattern.finditer(text):
            matches.append((match.start(), match.end(), outcome))
    if not matches:
        return "review_required", ""
    start, end, outcome = max(matches, key=lambda item: item[0])
    excerpt = text[max(0, start - 260):min(len(text), end + 360)]
    return outcome, normalize_excerpt(excerpt)


def resolve_text(text: str) -> tuple[str, str, str]:
    section = final_operative_section(text)
    if not section:
        return "review_required", "no_explicit_final_operative_section", ""
    routed = outcome_from_operative_text(section)
    strict, evidence = strict_operative_match(section)
    if routed in BINARY and strict == routed and evidence:
        return routed, "explicit_source_cue_agreement", evidence
    if routed in BINARY and strict in BINARY and routed != strict:
        return "review_required", "classifier_disagreement", evidence
    if routed in BINARY:
        return "review_required", "broad_cue_without_strict_confirmation", evidence
    if strict in BINARY:
        return "review_required", "strict_cue_without_broad_confirmation", evidence
    return "review_required", "no_explicit_binary_source_cue_in_final_section", ""


def resolve_row(cache_root: Path, row: dict[str, str]) -> dict[str, str]:
    citation = canonical_citation(row.get("era_citation", ""), row["pdf_url"])
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", citation or row["pdf_url"]).strip("_")
    pdf = cache_root / "pdf" / f"{slug}.pdf"
    text_path = cache_root / "text" / f"{slug}.txt"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    if not pdf.exists():
        pdf.write_bytes(fetch(row["pdf_url"]))
    text = pdf_text(pdf, text_path)
    outcome, status, evidence = resolve_text(text)
    return {
        "year": row.get("year", ""),
        "era_citation": citation,
        "case_name": row.get("case_name", ""),
        "pdf_url": row["pdf_url"],
        "legal_outcome": outcome if outcome in BINARY else "",
        "source_resolution_status": status,
        "evidence_excerpt": evidence,
    }


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "year", "era_citation", "case_name", "pdf_url", "legal_outcome",
        "source_resolution_status", "evidence_excerpt",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("workers must be at least 1")

    root = args.root.resolve()
    queue_path = root / "output" / "headline" / "legal_review_queue.csv"
    output_path = root / "output" / "headline" / "legal_source_resolutions.csv"
    if not queue_path.exists():
        raise SystemExit(f"missing {queue_path}; run build_outcome_summaries.py first")
    queue = list(csv.DictReader(queue_path.open(newline="")))
    cache_root = root / ".legal-source-cache"

    results: dict[str, dict[str, str]] = {}
    if queue:
        with ThreadPoolExecutor(max_workers=min(args.workers, len(queue))) as executor:
            futures = {executor.submit(resolve_row, cache_root, row): row for row in queue}
            for future in as_completed(futures):
                result = future.result()
                results[result["pdf_url"]] = result
                print(
                    f"{result['year']} {result['era_citation']}: "
                    f"{result['legal_outcome'] or 'review_required'} "
                    f"({result['source_resolution_status']})",
                    flush=True,
                )

    rows = sorted(results.values(), key=lambda row: (row.get("year", ""), row.get("era_citation", ""), row["pdf_url"]))
    write_results(output_path, rows)
    resolved = sum(row.get("legal_outcome") in BINARY for row in rows)
    ambiguous = sum(not row.get("legal_outcome") for row in rows)
    print(f"Source review results: {resolved} resolved, {ambiguous} still ambiguous, {len(rows)} total reviewed")


if __name__ == "__main__":
    main()
