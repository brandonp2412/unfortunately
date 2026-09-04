import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_outcome_summaries import (
    comparison_summary,
    paired_rows,
    source_resolved_legal_rows,
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
        "legal_review_status": "manual_direct_source_review_required",
    }]


def write_source_resolution(root: Path, *, outcome: str, status: str, evidence: str) -> None:
    path = root / "output" / "headline" / "legal_source_resolutions.csv"
    path.parent.mkdir(parents=True)
    fields = [
        "year", "era_citation", "case_name", "pdf_url", "legal_outcome",
        "source_resolution_status", "evidence_excerpt",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "year": "2020",
            "era_citation": "2020_NZERA_1",
            "case_name": "A v B",
            "pdf_url": "https://example.invalid/1.pdf",
            "legal_outcome": outcome,
            "source_resolution_status": status,
            "evidence_excerpt": evidence,
        })


def test_source_resolution_requires_explicit_agreement_and_evidence(tmp_path: Path):
    write_source_resolution(
        tmp_path,
        outcome="employee_win",
        status="explicit_source_cue_agreement",
        evidence="The dismissal was not justified.",
    )
    rows = source_resolved_legal_rows(tmp_path)
    assert rows[0]["outcome"] == "employee_win"
    assert "explicit_source_cue_agreement" in rows[0]["source"]


def test_source_resolution_rejects_unproven_binary_result(tmp_path: Path):
    write_source_resolution(
        tmp_path,
        outcome="employee_win",
        status="broad_cue_without_strict_confirmation",
        evidence="some text",
    )
    with pytest.raises(ValueError, match="required status"):
        source_resolved_legal_rows(tmp_path)
