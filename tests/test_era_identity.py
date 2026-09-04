import csv
from pathlib import Path

import pytest

from era_identity import canonical_citation, citation_from_pdf_url
from repair_recent_citations import repair_file


def test_citation_from_hyphenated_era_pdf_url() -> None:
    url = "https://determinations.era.govt.nz/assets/elawpdf/2025/2025-NZERA-266.pdf"
    assert citation_from_pdf_url(url) == "2025 NZERA 266"


def test_citation_from_underscored_era_pdf_url() -> None:
    url = "https://determinations.era.govt.nz/assets/elawpdf/2020/2020_NZERA_100.pdf"
    assert citation_from_pdf_url(url) == "2020 NZERA 100"


def test_url_identity_overrides_stale_parsed_citation() -> None:
    url = "https://determinations.era.govt.nz/assets/elawpdf/2025/2025-NZERA-266.pdf"
    assert canonical_citation("[2024] NZERA 668", url) == "2025 NZERA 266"


def test_url_with_disagreeing_path_year_fails_closed() -> None:
    with pytest.raises(ValueError, match="year mismatch"):
        citation_from_pdf_url(
            "https://determinations.era.govt.nz/assets/elawpdf/2024/2025-NZERA-266.pdf"
        )


def test_repair_file_preserves_schema_and_repairs_citation(tmp_path: Path) -> None:
    path = tmp_path / "recent.csv"
    fields = ["year", "era_citation", "case_name", "pdf_url", "classified_outcome"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "year": "2025",
            "era_citation": "[2024] NZERA 668",
            "case_name": "A v B",
            "pdf_url": "https://determinations.era.govt.nz/assets/elawpdf/2025/2025-NZERA-266.pdf",
            "classified_outcome": "review_required",
        })
    assert repair_file(path) == 1
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == fields
    assert rows[0]["era_citation"] == "2025 NZERA 266"
