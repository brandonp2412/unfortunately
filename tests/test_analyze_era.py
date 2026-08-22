import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyze_era import extract_pdf_urls, extract_pdf_urls_for_year, outcome_from_operative_text, category_from_text


def test_extract_pdf_urls_deduplicates_and_normalizes_relative_links():
    html = '''<a href="/assets/elawpdf/2024/2024-NZERA-781.pdf">one</a>
    <a href="https://determinations.era.govt.nz/assets/elawpdf/2024/2024-NZERA-781.pdf">two</a>
    <a href="/assets/elawpdf/2024/2024-NZERA-782.pdf">three</a>'''

    assert extract_pdf_urls(html) == [
        "https://determinations.era.govt.nz/assets/elawpdf/2024/2024-NZERA-781.pdf",
        "https://determinations.era.govt.nz/assets/elawpdf/2024/2024-NZERA-782.pdf",
    ]


def test_extract_pdf_urls_for_year_uses_requested_year():
    html = '<a href="/assets/elawpdf/2025/2025-NZERA-4.pdf">2025</a>'
    assert extract_pdf_urls_for_year(html, 2025) == [
        "https://determinations.era.govt.nz/assets/elawpdf/2025/2025-NZERA-4.pdf"
    ]


def test_extract_pdf_urls_for_year_accepts_legacy_underscore_filenames():
    html = '<a href="/assets/elawpdf/2020/2020_NZERA_541.pdf">2020</a>'
    assert extract_pdf_urls_for_year(html, 2020) == [
        "https://determinations.era.govt.nz/assets/elawpdf/2020/2020_NZERA_541.pdf"
    ]


def test_outcome_does_not_treat_negative_finding_as_employee_win():
    assert outcome_from_operative_text("I find the dismissal was not unjustifiably dismissed.") == "employer_win"


def test_outcome_uses_later_operational_finding_not_earlier_submission():
    text = "The employer says dismissal was justified. Conclusion: Campbell was unjustifiably dismissed."
    assert outcome_from_operative_text(text) == "employee_win"


def test_category_from_text_identifies_costs_follow_up():
    assert category_from_text("COSTS DETERMINATION OF THE AUTHORITY") == "costs_follow_up"
