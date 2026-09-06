import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_outcome_summaries import (
    comparison_summary,
    direct_review_rows,
    monetary_rows,
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
        "work_status": "agent_source_review_pending",
    }]


def write_direct_review(root: Path, *, included: str, outcome: str) -> None:
    path = root / "years" / "2022" / "output" / "2022_direct_legal_reviews.csv"
    path.parent.mkdir(parents=True)
    fields = [
        "year", "era_citation", "case_name", "pdf_url", "included_in_merits_denominator",
        "legal_outcome", "supporting_quote_or_paragraph", "confidence", "review_status",
        "review_notes",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "year": "2022",
            "era_citation": "2022 NZERA 1",
            "case_name": "A v B",
            "pdf_url": "https://example.invalid/1.pdf",
            "included_in_merits_denominator": included,
            "legal_outcome": outcome,
            "supporting_quote_or_paragraph": "The dismissal claim is unsuccessful.",
            "confidence": "high",
            "review_status": "direct_agent_source_review",
            "review_notes": "Direct reading of conclusion.",
        })


def test_direct_review_ledger_requires_direct_agent_status_and_evidence(tmp_path: Path):
    write_direct_review(tmp_path, included="yes", outcome="employer_win")
    rows = direct_review_rows(tmp_path)
    assert rows[0]["legal_outcome"] == "employer_win"
    assert rows[0]["source"].endswith("2022_direct_legal_reviews.csv")


def test_direct_review_exclusion_removes_case_from_monetary_scope(tmp_path: Path):
    write_direct_review(tmp_path, included="no", outcome="excluded")
    financial = tmp_path / "output" / "uniform_financial_2010_2025.csv"
    financial.parent.mkdir(parents=True)
    with financial.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["year", "era_citation", "case_name", "pdf_url", "financial_binary_outcome"])
        writer.writeheader()
        writer.writerow({
            "year": "2022", "era_citation": "2022 NZERA 1", "case_name": "A v B",
            "pdf_url": "https://example.invalid/1.pdf", "financial_binary_outcome": "employee_win",
        })
    assert monetary_rows(tmp_path) == []
