from analyze_legacy_year import extract_pdf_urls_for_year, field_citation, field_date


def test_extracts_legacy_year_scoped_pdf_paths_and_deduplicates():
    html = '''
    <a href="/assets/elawpdf/2010/3f38b9bbb4/aa-528_10.pdf">one</a>
    <a href="https://determinations.era.govt.nz/assets/elawpdf/2010/3f38b9bbb4/aa-528_10.pdf">duplicate</a>
    <a href="/assets/elawpdf/2011/abc/aa-1_11.pdf">other year</a>
    '''
    assert extract_pdf_urls_for_year(html, 2010) == [
        "https://determinations.era.govt.nz/assets/elawpdf/2010/3f38b9bbb4/aa-528_10.pdf"
    ]


def test_preserves_legacy_decision_identifier():
    assert field_citation("", 2010, "aa-528_10") == "AA 528/10"
    assert field_citation("", 2010, "ca-189a_10") == "CA 189A/10"


def test_uses_neutral_citation_when_present():
    assert field_citation("[2019] NZERA 77", 2019, "2019-NZERA-77") == "[2019] NZERA 77"


def test_does_not_take_wrong_year_neutral_citation_from_body():
    assert field_citation("Reference to [2014] NZERA 12", 2013, "aa-88_13") == "AA 88/13"


def test_extracts_requested_year_decision_date():
    text = "Date of Determination: 4 June 2013"
    assert field_date(text, 2013) == "4 June 2013"
