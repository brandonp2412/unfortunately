#!/usr/bin/env python3
"""Build one explicit classification table for every downloaded result, 2020-25."""
from __future__ import annotations

import csv
import re
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def authority_serious_status(row: dict[str, str], root: Path) -> str:
    if row.get("serious_misconduct_alleged_binary") != "yes":
        return "not_alleged"
    text_path = root / row["local_text"]
    if not text_path.exists():
        text_path = root / "years" / row["year"] / row["local_text"]
    text = text_path.read_text(errors="replace").lower()
    tail = text[-18000:]
    yes = re.search(r"(?:found|find|concluded|conclusion).{0,180}(?:amounted to|was|were|constituted) serious misconduct|serious misconduct.{0,220}(?:was|were) established", tail, re.S)
    no = re.search(r"(?:did not|does not|not) amount(?:ed)? to serious misconduct|insufficient evidence.{0,120}serious misconduct|not established.{0,120}serious misconduct", tail, re.S)
    if yes and (not no or yes.start() > no.start()):
        return "confirmed_yes"
    if no:
        return "confirmed_no"
    return "authority_not_determined"


def main() -> None:
    root = Path(__file__).resolve().parent
    all_rows: list[dict[str, str]] = []
    for year in range(2020, 2026):
        if year == 2024:
            source = root / "output" / "all_search_results.csv"
        else:
            source = root / "years" / str(year) / "output" / f"{year}_final_categorized.csv"
        for row in rows(source):
            row["year"] = str(year)
            if year == 2024:
                row["document_category"] = "included_merits" if row.get("included_in_baseline") == "yes" else "excluded_or_nonmerits"
                row["classified_outcome"] = row.get("outcome", "mixed_unclear")
                row["classification_confidence"] = row.get("confidence", "reviewed")
                row["classification_status"] = "legal_reviewed_2024"
            else:
                row["document_category"] = row.get("initial_category", "possible_merits_determination")
                row["classified_outcome"] = row.get("final_outcome", "mixed_unclear")
                row["classification_confidence"] = row.get("final_confidence", "review_route")
                row["classification_status"] = "year_route_requires_operative_findings_review"
            # Allegation is a binary coding; uncertainty belongs only to the
            # separate ERA-confirmation field and to the outcome field.
            row["serious_misconduct_alleged_binary"] = "yes" if row.get("serious_misconduct_alleged") == "yes" else "no"
            row["authority_serious_misconduct_finding"] = authority_serious_status(row, root)
            row["serious_misconduct_review_status"] = "assistant_operative_text_review"
            all_rows.append(row)
    fields = ["year", "era_citation", "case_name", "pdf_url", "local_pdf", "local_text",
              "document_category", "classified_outcome", "classification_confidence",
              "classification_status", "serious_misconduct_alleged_binary",
              "authority_serious_misconduct_finding", "serious_misconduct_review_status", "contribution_percentage"]
    target = root / "output" / "combined_2020_2025_full_classification.csv"
    with target.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(all_rows)
    print(f"wrote {len(all_rows)} rows to {target}")


if __name__ == "__main__":
    main()
