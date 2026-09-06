import json
from pathlib import Path

from build_site import build_site


def test_build_site_exports_canonical_data_and_visible_content(tmp_path: Path) -> None:
    target = tmp_path / "site"
    build_site(target)

    html = (target / "index.html").read_text(encoding="utf-8")
    for content in (
        "Legal merits",
        "Monetary outcome",
        "Case explorer",
        "Method",
        "Download case data",
    ):
        assert content in html

    summary = json.loads((target / "data" / "summary.json").read_text(encoding="utf-8"))
    cases = json.loads((target / "data" / "cases.json").read_text(encoding="utf-8"))
    assert summary["manifest"]["schema_version"] == 5
    assert summary["meta"]["year_start"] == 2010
    assert summary["meta"]["year_end"] == 2025
    assert len(summary["yearly"]) == 16
    assert len(cases) == summary["meta"]["case_count"]
    assert len(cases) == summary["manifest"]["corpus"]["case_count"]
    legal_outcomes = {row["legal_outcome"] for row in cases}
    assert legal_outcomes >= {"employee_win", "employer_win"}
    assert None not in legal_outcomes
    assert all(row["monetary_outcome"] is not None for row in cases)
