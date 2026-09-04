#!/usr/bin/env python3
"""Audit ERA search recall by comparing the primary query with alternative phrases."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from analyze_era import all_result_urls

DEFAULT_TERMS = (
    "unjustified dismissal",
    "unjustifiably dismissed",
    "dismissal was not justified",
    "constructive dismissal",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--year-start", type=int, default=2010)
    parser.add_argument("--year-end", type=int, default=2025)
    parser.add_argument("--term", action="append", dest="terms")
    args = parser.parse_args()
    terms = tuple(args.terms or DEFAULT_TERMS)
    if "unjustified dismissal" not in terms:
        raise SystemExit("terms must include the primary 'unjustified dismissal' query")
    if args.year_start > args.year_end:
        raise SystemExit("year-start must not exceed year-end")

    root = args.root.resolve()
    cache_root = root / ".search-recall-cache"
    summary: list[dict[str, str]] = []
    candidates: list[dict[str, str]] = []

    for year in range(args.year_start, args.year_end + 1):
        results: dict[str, set[str]] = {}
        for term in terms:
            results[term] = set(all_result_urls(cache_root, year, term))
        primary = results["unjustified dismissal"]
        for term in terms:
            urls = results[term]
            additional = sorted(urls - primary)
            missing = sorted(primary - urls)
            summary.append({
                "year": str(year),
                "query": term,
                "search_hits": str(len(urls)),
                "additional_vs_primary": str(len(additional)),
                "primary_not_returned_by_query": str(len(missing)),
            })
            for url in additional:
                candidates.append({
                    "year": str(year),
                    "query": term,
                    "pdf_url": url,
                    "candidate_reason": "returned by alternate query but not primary query",
                })

    out = root / "output" / "recall"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "search_recall_summary.csv").open("w", newline="") as handle:
        fields = [
            "year", "query", "search_hits", "additional_vs_primary",
            "primary_not_returned_by_query",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary)
    with (out / "search_recall_candidates.csv").open("w", newline="") as handle:
        fields = ["year", "query", "pdf_url", "candidate_reason"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)

    extra = len({row["pdf_url"] for row in candidates})
    print(
        f"Recall audit complete for {args.year_start}-{args.year_end}: "
        f"{extra} unique alternate-query candidate URLs require scope review."
    )


if __name__ == "__main__":
    main()
