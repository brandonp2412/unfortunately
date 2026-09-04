import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_outcome_summaries import (
    comparison_summary,
    paired_rows,
    summarize,
    unresolved_legal_rows,
)


def test_summarize_keeps_binary_measure_separate():
    rows = [
        {"year": "2010", "outcome": "employee_win", "pdf_url": "a"},
        {"year": "2010", "outcome": "employer_win", "pdf_url": "b"},
        {"year": "2011", "outcome": "employee_win", "pdf_url": "c"},
    ]
    summary = summarize(rows)
    assert summary[0]["cases"] == "2"
    assert summary[0]["employee_win_rate"] == "50.0"
    assert summary[-1]["cases"] == "3"
    assert summary[-1]["employee_win_rate"] == "66.7"


def test_pairing_surfaces_measure_disagreement_and_unmatched_cases():
    legal = [
        {"year": "2010", "era_citation": "A", "case_name": "A v B", "pdf_url": "a", "outcome": "employee_win"},
        {"year": "2010", "era_citation": "B", "case_name": "B v C", "pdf_url": "b", "outcome": "employer_win"},
    ]
    monetary = [
        {"year": "2010", "era_citation": "A", "case_name": "A v B", "pdf_url": "a", "outcome": "employer_win"},
        {"year": "2010", "era_citation": "C", "case_name": "C v D", "pdf_url": "c", "outcome": "employee_win"},
    ]
    paired = paired_rows(legal, monetary)
    summary = comparison_summary(paired)[0]
    assert summary["paired_cases"] == "1"
    assert summary["disagreements"] == "1"
    assert summary["disagreement_rate"] == "100.0"
    assert summary["legal_only"] == "1"
    assert summary["monetary_only"] == "1"

    unresolved = unresolved_legal_rows(paired)
    assert unresolved == [{
        "year": "2010",
        "era_citation": "C",
        "case_name": "C v D",
        "pdf_url": "c",
        "monetary_outcome": "employee_win",
        "legal_review_status": "direct_source_review_required",
    }]
