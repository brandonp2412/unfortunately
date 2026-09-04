from pathlib import Path

import pytest

import audit_search_recall


def test_collect_results_groups_parallel_searches(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[int, str]] = []

    def fake_search(root: Path, year: int, term: str) -> list[str]:
        assert root == tmp_path
        calls.append((year, term))
        return [f"{year}:{term}:a", f"{year}:{term}:b"]

    monkeypatch.setattr(audit_search_recall, "all_search_result_refs", fake_search)
    terms = ("unjustified dismissal", "constructive dismissal")
    results = audit_search_recall.collect_results(tmp_path, range(2024, 2026), terms, workers=2)

    assert set(calls) == {
        (2024, "unjustified dismissal"),
        (2024, "constructive dismissal"),
        (2025, "unjustified dismissal"),
        (2025, "constructive dismissal"),
    }
    assert results[2024]["unjustified dismissal"] == {
        "2024:unjustified dismissal:a",
        "2024:unjustified dismissal:b",
    }
    assert results[2025]["constructive dismissal"] == {
        "2025:constructive dismissal:a",
        "2025:constructive dismissal:b",
    }


def test_collect_results_rejects_zero_workers(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workers must be at least 1"):
        audit_search_recall.collect_results(
            tmp_path,
            range(2024, 2025),
            ("unjustified dismissal",),
            workers=0,
        )
