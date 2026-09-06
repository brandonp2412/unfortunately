from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
HEADLINE = ROOT / "output" / "headline"
STATIC = ROOT / "site"

INT_FIELDS = {
    "cases",
    "employee_wins",
    "employer_wins",
    "paired_cases",
    "legal_employee_wins",
    "monetary_employee_wins",
    "disagreements",
    "legal_only",
    "monetary_only",
}
FLOAT_FIELDS = {
    "employee_win_rate",
    "legal_employee_win_rate",
    "monetary_employee_win_rate",
    "disagreement_rate",
}


def _coerce(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if value == "":
            out[key] = None
        elif key == "year" and value.isdigit():
            out[key] = int(value)
        elif key in INT_FIELDS:
            out[key] = int(value)
        elif key in FLOAT_FIELDS:
            out[key] = float(value)
        else:
            out[key] = value
    return out


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [_coerce(row) for row in csv.DictReader(handle)]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def build_site(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(STATIC, output_dir)

    manifest = json.loads((HEADLINE / "manifest.json").read_text(encoding="utf-8"))
    legal = _read_csv(HEADLINE / "legal_outcome_summary.csv")
    monetary = _read_csv(HEADLINE / "monetary_outcome_summary.csv")
    comparison = _read_csv(HEADLINE / "legal_vs_monetary_summary.csv")
    cases = _read_csv(HEADLINE / "paired_case_outcomes.csv")

    legal_by_year = {row["year"]: row for row in legal if isinstance(row["year"], int)}
    monetary_by_year = {row["year"]: row for row in monetary if isinstance(row["year"], int)}
    comparison_by_year = {
        row["year"]: row for row in comparison if isinstance(row["year"], int)
    }
    years = sorted(
        set(legal_by_year) | set(monetary_by_year) | set(comparison_by_year)
    )

    yearly: list[dict[str, Any]] = []
    for year in years:
        yearly.append(
            {
                "year": year,
                "legal": legal_by_year.get(year),
                "monetary": monetary_by_year.get(year),
                "comparison": comparison_by_year.get(year),
            }
        )

    _write_json(
        output_dir / "data" / "summary.json",
        {
            "manifest": manifest,
            "yearly": yearly,
            "meta": {
                "year_start": min(years),
                "year_end": max(years),
                "case_count": len(cases),
            },
        },
    )
    _write_json(output_dir / "data" / "cases.json", cases)

    downloads = output_dir / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    for name in (
        "legal_outcome_summary.csv",
        "monetary_outcome_summary.csv",
        "legal_vs_monetary_summary.csv",
        "paired_case_outcomes.csv",
        "manifest.json",
    ):
        shutil.copy2(HEADLINE / name, downloads / name)

    (output_dir / ".nojekyll").touch()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Unfortunately GitHub Pages site.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist",
        help="Output directory (default: dist)",
    )
    args = parser.parse_args()
    build_site(args.output.resolve())


if __name__ == "__main__":
    main()
