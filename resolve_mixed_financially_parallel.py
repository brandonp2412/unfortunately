#!/usr/bin/env python3
"""Bounded-parallel runner for the mixed-outcome financial tie-breaker."""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from resolve_mixed_financially import fetch_pdf, pdf_text, score_text


def blank_out(row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    original = row["classified_outcome"]
    out.update({
        "original_legal_outcome": original,
        "financial_tiebreak_applied": "no",
        "employee_money_awarded": "",
        "employee_money_adverse": "",
        "observable_net_money": "",
        "financial_evidence": "",
        "unallocated_money_units": "",
        "binary_outcome": original,
    })
    return out


def score_row(root: Path, row: dict[str, str]) -> dict[str, object]:
    citation = row["era_citation"].replace(" ", "_")
    cache = root / ".financial-cache"
    pdf = cache / "pdf" / f"{citation}.pdf"
    txt = cache / "text" / f"{citation}.txt"
    if not pdf.exists():
        fetch_pdf(row["pdf_url"], pdf)
    text = txt.read_text(errors="replace") if txt.exists() else pdf_text(pdf, txt)
    return score_text(text)


def resolve_parallel(root: Path, workers: int) -> list[dict[str, str]]:
    source = list(csv.DictReader((root / "output" / "combined_2020_2025_full_classification.csv").open(newline="")))
    result = [blank_out(row) for row in source]
    mixed_indices = [i for i, row in enumerate(source) if row["classified_outcome"] == "mixed_unclear"]
    print(f"Scoring {len(mixed_indices)} mixed rows with {workers} workers", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(score_row, root, source[i]): i for i in mixed_indices}
        done = 0
        for future in as_completed(futures):
            i = futures[future]
            scored = future.result()
            out = result[i]
            out["financial_tiebreak_applied"] = "yes"
            out["employee_money_awarded"] = f"{scored['employee_money_awarded']:.2f}"
            out["employee_money_adverse"] = f"{scored['employee_money_adverse']:.2f}"
            out["observable_net_money"] = f"{scored['observable_net_money']:.2f}"
            out["financial_evidence"] = str(scored["financial_evidence"])
            out["unallocated_money_units"] = str(scored["unallocated_money_units"])
            out["binary_outcome"] = str(scored["financial_binary_outcome"])
            done += 1
            if done % 20 == 0 or done == len(mixed_indices):
                print(f"Scored {done}/{len(mixed_indices)} mixed rows", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    rows = resolve_parallel(root, max(1, min(args.workers, 12)))
    target = root / "output" / "combined_2020_2025_binary_classification.csv"
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    mixed = [row for row in rows if row["financial_tiebreak_applied"] == "yes"]
    employee = sum(row["binary_outcome"] == "employee_win" for row in mixed)
    employer = sum(row["binary_outcome"] == "employer_win" for row in mixed)
    unallocated = sum(int(row["unallocated_money_units"] or 0) > 0 for row in mixed)
    print(f"Resolved {len(mixed)} mixed rows: {employee} employee wins, {employer} employer wins", flush=True)
    print(f"Mixed rows with unallocated dollar-bearing order text: {unallocated}", flush=True)


if __name__ == "__main__":
    main()
