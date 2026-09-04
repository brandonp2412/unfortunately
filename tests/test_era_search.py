import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from era_search import extract_next_start, extract_search_result_refs


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
