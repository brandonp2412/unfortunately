# Technical notes

## Scope

The corpus covers public Employment Relations Authority determinations returned by the ERA database search for `unjustified dismissal` from 2010–2025. The merits denominator contains determinations that finally resolve a dismissal or constructive-dismissal claim. Related costs, procedural, compliance, withdrawal, duplicate, and follow-up decisions remain in the audit corpus with their routing recorded.

## Classification

Each search result is downloaded, text is extracted with `pdftotext` plus OCR where required, and the operative findings, conclusion, and orders are read for final classification.

Final merits outcomes are binary:

- `employee_win`: the Authority found an unjustified dismissal or upheld the dismissal grievance.
- `employer_win`: the Authority found the dismissal justified or rejected the dismissal grievance.

Automated text cues provide review routing. Direct source review supplies final legal classifications.

For review-routed 2020–2025 cases, the published binary dataset also records an observable-order tie-breaker from operative monetary orders:

1. total money ordered in the employee/applicant's favour;
2. total money or costs ordered against the employee/applicant;
3. subtract adverse money from employee-side recovery;
4. positive net → `employee_win`;
5. zero or negative net → `employer_win`.

Targeted source audits cover parser-sensitive monetary orders and are stored in `output/financial_audit_resolutions.csv`. The 2020–2025 binary output contains 673 substantive decisions: 476 employee wins and 197 employer wins (70.7%).

## Serious misconduct

Serious misconduct is coded as three separate facts: employer allegation, Authority finding that the conduct occurred, and Authority finding that the conduct amounted to serious misconduct. The strict serious-misconduct analysis uses the Authority finding.

### 2024 strict results

| Analysis | Included | Employee wins | Employer wins | Employee rate |
|---|---:|---:|---:|---:|
| Baseline | 63 | 46 | 17 | 73.0% |
| ERA-confirmed serious misconduct removed | 61 | 46 | 15 | 75.4% |
| Serious-misconduct allegations removed | 52 | 35 | 17 | 67.3% |
| s 124 contribution removed | 61 | 44 | 17 | 72.1% |

## Cross-year charts

The headline 2010–2025 charts combine the completed 2010–2019 strict legal review with the audited 2020–2025 binary dataset. `make_charts.py` generates the outcome, trend, serious-misconduct, industry, and occupation charts.

## Context enrichment

`enrich_context.py` records source-excerpt-backed context fields for stated employee ethnicity and gender, salary text and annualized salary range, occupation/collar signal, industry signal, and representation mentioned in the determination. Silent source fields use `not_stated`.

Salary normalization accepts stated amounts with explicit hour, week, fortnight, month, year, or annum units. Hourly amounts annualize at 40 hours per week and 52 weeks per year; `$` is treated as NZD.

## Main files

- `analyze_era.py` — acquire, extract, and route recent-year determinations.
- `analyze_legacy_year.py` — acquire legacy-year source material.
- `build_review_dossier.py` — collect operative material for case review.
- `make_legacy_review_brief.py` — create compact review ledgers.
- `validate_legacy_review.py` — validate completed reviewed-year exports.
- `combine_years.py` / `combine_legacy_reviews.py` — combine year-level exports.
- `full_classification.py` — build combined legal-classification exports.
- `resolve_financial_outcomes.py` / `resolve_financial_outcomes_parallel.py` — resolve review-routed monetary outcomes.
- `apply_financial_audit.py` — apply source-audited monetary resolutions and generate binary summaries.
- `enrich_context.py` — add context categories and salary normalization.
- `make_charts.py` — generate published PNG charts.
- `output/combined_2010_2019_strict_classification.csv` — completed legacy strict classification.
- `output/combined_2020_2025_binary_classification.csv` — audited recent binary classification.
- `output/binary_outcome_summary.csv` — recent per-year totals and rates.
- `output/financial_audit_resolutions.csv` — source-audited monetary resolutions.
- `output/charts/` — published visualizations.

## Reproduce or add a year

```bash
python3 analyze_era.py --root years/2026 --year 2026
python3 combine_years.py
python3 enrich_context.py
python3 make_charts.py
pytest -q
```

A completed year includes determination-by-determination merits review, source-supported binary outcomes, deduplication, regenerated charts, and passing tests.

## Source

[New Zealand Employment Relations Authority determinations](https://determinations.era.govt.nz/)
