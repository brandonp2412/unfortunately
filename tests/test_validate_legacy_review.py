import csv
from pathlib import Path

from create_legacy_review_template import REVIEW_FIELDS
from validate_legacy_review import validate


def write_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def complete_row(url: str) -> dict[str, str]:
    row = {field: "" for field in REVIEW_FIELDS}
    row.update({
        "year": "2010",
        "search_result_number": "1",
        "era_citation": "AA 1/10",
        "pdf_url": url,
        "document_category": "included_merits",
        "included_in_merits_denominator": "yes",
        "final_outcome": "employee_win",
        "dismissal_reason_alleged": "performance",
        "serious_misconduct_alleged": "no",
        "era_confirmed_conduct": "not_applicable",
        "era_confirmed_serious_misconduct": "not_alleged",
        "dismissal_substantively_justified": "no",
        "dismissal_procedurally_justified": "no",
        "contributory_conduct_found_s124": "no",
        "remedies_awarded": "compensation",
        "supporting_quote_or_paragraph": "[42] The dismissal was unjustified.",
        "confidence": "high",
        "manual_review_status": "reviewed",
        "manual_review_notes": "Read findings, conclusion and orders.",
        "second_review_required": "no",
        "second_review_status": "not_required",
    })
    return row


def make_sources(root: Path, *, high_risk: str = "no") -> str:
    url = "https://example.invalid/aa-1_10.pdf"
    write_csv(
        root / "output" / "initial_extraction.csv",
        ["search_result_number", "era_citation", "pdf_url"],
        [{"search_result_number": "1", "era_citation": "AA 1/10", "pdf_url": url}],
    )
    write_csv(
        root / "output" / "2010_review_brief.csv",
        ["search_result_number", "era_citation", "pdf_url", "full_dossier_second_pass_candidate"],
        [{
            "search_result_number": "1",
            "era_citation": "AA 1/10",
            "pdf_url": url,
            "full_dossier_second_pass_candidate": high_risk,
        }],
    )
    return url


def test_complete_review_passes(tmp_path):
    url = make_sources(tmp_path)
    write_csv(tmp_path / "output" / "2010_manual_review.csv", REVIEW_FIELDS, [complete_row(url)])
    assert validate(tmp_path, 2010) == []


def test_pending_review_fails(tmp_path):
    url = make_sources(tmp_path)
    row = complete_row(url)
    row["manual_review_status"] = "pending"
    write_csv(tmp_path / "output" / "2010_manual_review.csv", REVIEW_FIELDS, [row])
    assert any("manual_review_status" in error for error in validate(tmp_path, 2010))


def test_high_risk_case_requires_second_review(tmp_path):
    url = make_sources(tmp_path, high_risk="yes")
    row = complete_row(url)
    write_csv(tmp_path / "output" / "2010_manual_review.csv", REVIEW_FIELDS, [row])
    errors = validate(tmp_path, 2010)
    assert any("second review" in error.lower() for error in errors)


def test_high_risk_case_passes_after_second_review(tmp_path):
    url = make_sources(tmp_path, high_risk="yes")
    row = complete_row(url)
    row.update({
        "second_review_required": "yes",
        "second_review_status": "reviewed",
        "second_review_notes": "Re-read full dossier and operative orders.",
    })
    write_csv(tmp_path / "output" / "2010_manual_review.csv", REVIEW_FIELDS, [row])
    assert validate(tmp_path, 2010) == []
