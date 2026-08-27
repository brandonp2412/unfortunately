#!/usr/bin/env python3
"""Fail unless a legacy ERA year has been completely and audibly human-reviewed."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


INCLUDED_CATEGORY = "included_merits"
EXCLUDED_CATEGORIES = {
    "excluded_costs_follow_up",
    "excluded_procedural_interlocutory",
    "excluded_withdrawn_discontinued",
    "excluded_want_of_prosecution",
    "excluded_compliance_removal",
    "excluded_jurisdiction_only",
    "excluded_duplicate_follow_up",
    "excluded_no_dismissal_merits",
    "excluded_other_nonmerits",
}
OUTCOMES = {"employee_win", "employer_win", "mixed_unclear"}
YES_NO = {"yes", "no"}
YES_NO_UNCLEAR = {"yes", "no", "unclear"}
JUSTIFICATION = {"yes", "no", "mixed", "unclear", "not_applicable"}
CONFIDENCE = {"high", "medium", "low"}
SERIOUS_FINDING = {"yes", "no", "not_alleged", "unclear"}
CONDUCT_FINDING = {"yes", "no", "not_applicable", "unclear"}


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def require(errors: list[str], ok: bool, label: str, message: str) -> None:
    if not ok:
        errors.append(f"{label}: {message}")


def validate(root: Path, year: int) -> list[str]:
    initial = load(root / "output" / "initial_extraction.csv")
    brief = load(root / "output" / f"{year}_review_brief.csv")
    review = load(root / "output" / f"{year}_manual_review.csv")
    errors: list[str] = []

    initial_urls = [row.get("pdf_url", "") for row in initial]
    brief_by_url = {row.get("pdf_url", ""): row for row in brief}
    review_by_url: dict[str, dict[str, str]] = {}
    for row in review:
        url = row.get("pdf_url", "")
        if url in review_by_url:
            errors.append(f"duplicate reviewed URL: {url}")
        review_by_url[url] = row

    require(errors, len(initial_urls) == len(set(initial_urls)), str(year), "initial extraction contains duplicate PDF URLs")
    require(errors, len(initial) == len(brief), str(year), "initial extraction and review brief row counts differ")
    require(errors, len(initial) == len(review), str(year), "initial extraction and manual review row counts differ")
    require(errors, set(initial_urls) == set(review_by_url), str(year), "manual review does not cover exactly the acquired PDF URLs")

    for source in initial:
        url = source.get("pdf_url", "")
        row = review_by_url.get(url)
        if row is None:
            continue
        label = f"{year} {row.get('era_citation') or row.get('search_result_number') or url}"
        category = row.get("document_category", "")
        included = row.get("included_in_merits_denominator", "")
        outcome = row.get("final_outcome", "")

        require(errors, row.get("manual_review_status") == "reviewed", label, "manual_review_status must be reviewed")
        require(errors, bool(row.get("manual_review_notes", "").strip()), label, "manual_review_notes is required")
        require(errors, row.get("confidence") in CONFIDENCE, label, "confidence must be high/medium/low")
        require(errors, category == INCLUDED_CATEGORY or category in EXCLUDED_CATEGORIES, label, "invalid or missing document_category")

        if category == INCLUDED_CATEGORY:
            require(errors, included == "yes", label, "included merits row must be in the denominator")
            require(errors, outcome in OUTCOMES, label, "included merits row needs a legal outcome")
            require(errors, bool(row.get("dismissal_reason_alleged", "").strip()), label, "dismissal reason is required; use not_stated if silent")
            require(errors, row.get("serious_misconduct_alleged") in YES_NO, label, "serious-misconduct allegation must be yes/no")
            require(errors, row.get("era_confirmed_conduct") in CONDUCT_FINDING, label, "ERA conduct finding is required")
            require(errors, row.get("era_confirmed_serious_misconduct") in SERIOUS_FINDING, label, "ERA serious-misconduct finding is required")
            require(errors, row.get("dismissal_substantively_justified") in JUSTIFICATION, label, "substantive justification is required")
            require(errors, row.get("dismissal_procedurally_justified") in JUSTIFICATION, label, "procedural justification is required")
            require(errors, row.get("contributory_conduct_found_s124") in YES_NO_UNCLEAR, label, "s 124 contribution finding is required")
            if row.get("contributory_conduct_found_s124") == "yes":
                require(errors, bool(row.get("contribution_percentage", "").strip()), label, "contribution percentage is required when contribution is found")
            require(errors, bool(row.get("remedies_awarded", "").strip()), label, "remedies are required; use none if no remedy")
            require(errors, bool(row.get("supporting_quote_or_paragraph", "").strip()), label, "supporting paragraph/quotation is required")
            require(errors, not row.get("exclusion_reason", "").strip(), label, "included row must not have an exclusion reason")
        else:
            require(errors, included == "no", label, "excluded row must not be in the denominator")
            require(errors, outcome in {"excluded", ""}, label, "excluded row must not carry a binary merits outcome")
            require(errors, bool(row.get("exclusion_reason", "").strip()), label, "excluded row needs a specific exclusion reason")
            if category == "excluded_duplicate_follow_up":
                require(errors, bool(row.get("duplicate_of", "").strip()), label, "duplicate/follow-up row must identify the underlying decision")

        brief_row = brief_by_url.get(url, {})
        must_second_review = any((
            outcome == "mixed_unclear",
            row.get("serious_misconduct_alleged") == "yes",
            row.get("contributory_conduct_found_s124") in {"yes", "unclear"},
            brief_row.get("full_dossier_second_pass_candidate") == "yes",
        ))
        if must_second_review:
            require(errors, row.get("second_review_required") == "yes", label, "high-risk row must be marked for second review")
            require(errors, row.get("second_review_status") == "reviewed", label, "high-risk row needs completed second review")
            require(errors, bool(row.get("second_review_notes", "").strip()), label, "second-review notes are required")
        elif row.get("second_review_required") == "yes":
            require(errors, row.get("second_review_status") == "reviewed", label, "voluntary second review is marked required but incomplete")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    errors = validate(args.root, args.year)
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(f"review validation failed with {len(errors)} error(s)")
    print(f"{args.year}: every acquired determination has a complete human review record")


if __name__ == "__main__":
    main()
