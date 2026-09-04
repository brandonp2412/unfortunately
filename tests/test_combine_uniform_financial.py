import csv
from pathlib import Path

import pytest

from combine_uniform_financial import YEARS, load_rows, validate_rows


def write_year(root: Path, year: int, suffix: str | None = None, stored_citation: str | None = None) -> None:
    out = root / "output" / "uniform_financial"
    out.mkdir(parents=True, exist_ok=True)
    token = suffix or str(year)
    number = int(token) if token.isdigit() else year
    with (out / f"{year}.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["year", "era_citation", "pdf_url", "financial_binary_outcome"],
        )
        writer.writeheader()
        writer.writerow({
            "year": str(year),
            "era_citation": stored_citation or f"{year}_NZERA_{number}",
            "pdf_url": f"https://determinations.era.govt.nz/assets/elawpdf/{year}/{year}-NZERA-{number}.pdf",
            "financial_binary_outcome": "employee_win",
        })


def write_legacy_2010(root: Path) -> None:
    out = root / "output" / "uniform_financial"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "2010.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["year", "era_citation", "pdf_url", "financial_binary_outcome"],
        )
        writer.writeheader()
        writer.writerow({
            "year": "2010",
            "era_citation": "WA 999/10",
            "pdf_url": "https://determinations.era.govt.nz/assets/elawpdf/2010/2ecbf5cd22/wa-206_10.pdf",
            "financial_binary_outcome": "employee_win",
        })


def test_load_and_validate_accept_dynamic_corpus_size(tmp_path: Path) -> None:
    for year in YEARS:
        write_year(tmp_path, year)
    rows = load_rows(tmp_path)
    validate_rows(rows)
    assert len(rows) == len(YEARS)


def test_load_and_validate_accept_source_verified_legacy_citation(tmp_path: Path) -> None:
    for year in YEARS:
        write_year(tmp_path, year)
    write_legacy_2010(tmp_path)
    rows = load_rows(tmp_path)
    row = next(row for row in rows if row["year"] == "2010")
    assert row["era_citation"] == "WA 206/10"
    validate_rows(rows)


def test_load_rows_repairs_stale_cross_year_citation_from_url(tmp_path: Path) -> None:
    for year in YEARS:
        write_year(tmp_path, year)
    write_year(tmp_path, 2025, suffix="266", stored_citation="[2024] NZERA 668")
    rows = load_rows(tmp_path)
    row = next(row for row in rows if row["year"] == "2025")
    assert row["era_citation"] == "2025 NZERA 266"
    validate_rows(rows)


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
