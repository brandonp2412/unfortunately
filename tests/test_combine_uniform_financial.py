import csv
from pathlib import Path

import pytest

from combine_uniform_financial import YEARS, load_rows, validate_rows


def write_year(root: Path, year: int, suffix: str | None = None) -> None:
    out = root / "output" / "uniform_financial"
    out.mkdir(parents=True, exist_ok=True)
    token = suffix or str(year)
    with (out / f"{year}.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["year", "era_citation", "pdf_url", "financial_binary_outcome"],
        )
        writer.writeheader()
        writer.writerow({
            "year": str(year),
            "era_citation": f"{year}_NZERA_{token}",
            "pdf_url": f"https://example.invalid/{token}.pdf",
            "financial_binary_outcome": "employee_win",
        })


def test_load_and_validate_accept_dynamic_corpus_size(tmp_path: Path) -> None:
    for year in YEARS:
        write_year(tmp_path, year)
    rows = load_rows(tmp_path)
    validate_rows(rows)
    assert len(rows) == len(YEARS)


def test_load_rows_rejects_empty_year_file(tmp_path: Path) -> None:
    for year in YEARS:
        write_year(tmp_path, year)
    path = tmp_path / "output" / "uniform_financial" / f"{YEARS[-1]}.csv"
    path.write_text("year,era_citation,pdf_url,financial_binary_outcome\n")
    with pytest.raises(SystemExit, match="no substantive rows"):
        load_rows(tmp_path)


def test_validate_rows_rejects_duplicate_citations(tmp_path: Path) -> None:
    for year in YEARS:
        write_year(tmp_path, year)
    rows = load_rows(tmp_path)
    rows[-1]["era_citation"] = rows[0]["era_citation"]
    with pytest.raises(SystemExit, match="duplicate ERA citations"):
        validate_rows(rows)
