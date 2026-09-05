import json
from pathlib import Path

from build_site import build_site


def test_build_site_exports_canonical_data(tmp_path: Path) -> None:
    target = tmp_path / "site"
    build_site(target)

    assert (target / "index.html").is_file()
    assert (target / "styles.css").is_file()
    assert (target / "app.js").is_file()
    assert (target / ".nojekyll").is_file()

    summary = json.loads((target / "data" / "summary.json").read_text(encoding="utf-8"))
    cases = json.loads((target / "data" / "cases.json").read_text(encoding="utf-8"))
    unfinished = json.loads((target / "data" / "unfinished-legal-cases.json").read_text(encoding="utf-8"))

    coverage = summary["manifest"]["measures"]["legal_merits"]["binary_classification_coverage"]
    assert summary["manifest"]["schema_version"] == 4
    assert summary["manifest"]["status"]["state"] in {"unfinished", "complete"}
    assert summary["meta"]["year_start"] == 2010
    assert summary["meta"]["year_end"] == 2025
    assert len(summary["yearly"]) == 16
    assert len(cases) == summary["meta"]["case_count"]
    assert len(unfinished) == summary["meta"]["unfinished_case_count"]
    assert len(unfinished) == coverage["unfinished_agent_source_review"]
    assert {row["legal_outcome"] for row in cases} >= {None, "employee_win", "employer_win"}
    assert (target / "downloads" / "paired_case_outcomes.csv").is_file()
    assert (target / "downloads" / "unfinished_legal_cases.csv").is_file()
    assert (target / "downloads" / "manifest.json").is_file()


def test_site_uses_relative_assets_for_project_pages(tmp_path: Path) -> None:
    target = tmp_path / "site"
    build_site(target)

    html = (target / "index.html").read_text(encoding="utf-8")
    js = (target / "app.js").read_text(encoding="utf-8")

    assert 'href="./styles.css"' in html
    assert 'src="./app.js"' in html
    assert 'fetch("./data/summary.json")' in js
    assert 'fetch("./data/cases.json")' in js
    assert "Review required" not in html
    assert "Review required" not in js
