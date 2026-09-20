import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import era_search
from era_search import _cache_slug, extract_next_start, extract_search_result_refs, resolve_pdf_url


def test_extract_search_result_refs_accepts_current_detail_links():
    html = '''
    <a href="/determination/view/8247">Naiker v D S Wireless Ltd</a>
    <a href="https://determinations.era.govt.nz/determination/view/8247">duplicate</a>
    <a href="/determination/view/13063">Sleeth v Bromley Park Hatcheries Ltd</a>
    '''
    assert extract_search_result_refs(html) == [
        "https://determinations.era.govt.nz/determination/view/8247",
        "https://determinations.era.govt.nz/determination/view/13063",
    ]


def test_extract_search_result_refs_also_accepts_direct_pdf_links():
    html = '<a href="/assets/elawpdf/2024/2024-NZERA-311.pdf">pdf</a>'
    assert extract_search_result_refs(html) == [
        "https://determinations.era.govt.nz/assets/elawpdf/2024/2024-NZERA-311.pdf"
    ]


def test_extract_next_start_prefers_smallest_forward_offset():
    html = '''
    <a href="?Keywords=x&amp;start=0">1</a>
    <a href="?Keywords=x&amp;start=20">3</a>
    <a href="?Keywords=x&start=10">2</a>
    '''
    assert extract_next_start(html, 0) == 10
    assert extract_next_start(html, 10) == 20
    assert extract_next_start(html, 20) is None


def test_cache_slug_distinguishes_normalisation_collisions():
    dashed = _cache_slug("constructive-dismissal")
    spaced = _cache_slug("constructive dismissal")

    assert dashed != spaced
    assert dashed.startswith("constructive_dismissal_")
    assert spaced.startswith("constructive_dismissal_")


def test_resolve_pdf_url_accepts_explicitly_unavailable_legacy_pdf(monkeypatch):
    monkeypatch.setattr(
        era_search,
        "fetch",
        lambda _url: b"<td>PDF file not available for download, please contact us to request a copy.</td>",
    )

    assert resolve_pdf_url("https://determinations.era.govt.nz/determination/view/10182", 2011) is None


def test_resolve_pdf_url_still_fails_closed_for_unexpected_missing_link(monkeypatch):
    monkeypatch.setattr(era_search, "fetch", lambda _url: b"<html><body>detail page changed</body></html>")

    try:
        resolve_pdf_url("https://determinations.era.govt.nz/determination/view/99999", 2011)
    except RuntimeError as exc:
        assert "no PDF link found" in str(exc)
    else:
        raise AssertionError("unexpected missing PDF link should fail closed")
