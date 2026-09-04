#!/usr/bin/env python3
"""Audit ERA search recall by comparing the primary query with alternative phrases."""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from era_search import all_search_result_refs

DEFAULT_TERMS = (
    "unjustified dismissal",
    "unjustifiably dismissed",
    "dismissal was not justified",
    "constructive dismissal",
)
DEFAULT_WORKERS = 4


def collect_results(
    cache_root: Path,
    years: range,
    terms: tuple[str, ...],
    workers: int,
) -> dict[int, dict[str, set[str]]]:
    """Run independent year/query searches concurrently with a small worker cap."""
    if workers < 1:
        raise ValueError("workers must be at least 1")

    results: dict[int, dict[str, set[str]]] = {year: {} for year in years}
    jobs = [(year, term) for year in years for term in terms]
    with ThreadPoolExecutor(max_workers=min(workers, len(jobs))) as executor:
        futures = {
            executor.submit(all_search_result_refs, cache_root, year, term): (year, term)
            for year, term in jobs
        }
        for future in as_completed(futures):
            year, term = futures[future]
            refs = set(future.result())
            results[year][term] = refs
            print(f"{year} / {term}: {len(refs)} hits", flush=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--year-start", type=int, default=2010)
    parser.add_argument("--year-end", type=int, default=2025)
    parser.add_argument("--term", action="append", dest="terms")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    terms = tuple(args.terms or DEFAULT_TERMS)
    if "unjustified dismissal" not in terms:
        raise SystemExit("terms must include the primary 'unjustified dismissal' query")
    if args.year_start > args.year_end:
        raise SystemExit("year-start must not exceed year-end")
    if args.workers < 1:
        raise SystemExit("workers must be at least 1")

    root = args.root.resolve()
    cache_root = root / ".search-recall-cache-v2"
    years = range(args.year_start, args.year_end + 1)
    results_by_year = collect_results(cache_root, years, terms, args.workers)
    summary: list[dict[str, str]] = []
    candidates: list[dict[str, str]] = []

    for year in years:
        results = results_by_year[year]
        primary = results["unjustified dismissal"]
        if not primary:
            raise RuntimeError(f"primary ERA query unexpectedly returned zero results for {year}")
        for term in terms:
            refs = results[term]
            additional = sorted(refs - primary)
            missing = sorted(primary - refs)
            summary.append({
                "year": str(year),
                "query": term,
                "search_hits": str(len(refs)),
                "additional_vs_primary": str(len(additional)),
                "primary_not_returned_by_query": str(len(missing)),
            })
            for ref in additional:
                candidates.append({
                    "year": str(year),
                    "query": term,
                    "determination_ref": ref,
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
        fields = ["year", "query", "determination_ref", "candidate_reason"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)

    extra = len({row["determination_ref"] for row in candidates})
    print(
        f"Recall audit complete for {args.year_start}-{args.year_end}: "
        f"{extra} unique alternate-query candidate determinations require scope review."
    )


if __name__ == "__main__":
    main()
