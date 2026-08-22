# Technical notes

## Scope

The corpus is made from public Employment Relations Authority determinations
returned by the ERA database search for `unjustified dismissal`. It covers
2020–2025 in the combined export. This estimates outcomes among disputes that
reached a public determination; it is not an employee grievance win
probability. Settlements, confidential outcomes, abandonment, and disputes
never filed are outside the frame.

## 2024 legal-review method

The 2024 search returned 130 unique PDFs. Each result was downloaded, text was
extracted with `pdftotext` (with OCR fallback where required), and the
operative findings and orders were read for classification.

The baseline excludes costs-only, procedural/interlocutory, compliance or
removal, withdrawn/discontinued, want-of-prosecution, duplicate/follow-up, and
non-merits decisions. The baseline contains 63 substantive determinations.

An employee win means the Authority found unjustified dismissal, even where
remedies were reduced for contribution. An employer win means the dismissal
was found justified or the claim was rejected. Mixed/unclear is reserved for
outcomes that cannot fairly be reduced to either result.

Serious misconduct is split into three distinct ideas:

1. employer allegation;
2. Authority finding that the conduct occurred; and
3. Authority finding that the conduct amounted to serious misconduct.

Only the third is used for the strict serious-misconduct exclusion.

## 2024 results

| Analysis | Included | Employee wins | Employer wins | Mixed/other | Employee rate (all) |
|---|---:|---:|---:|---:|---:|
| Baseline | 63 | 46 | 17 | 0 | 73.0% |
| Exclude ERA-confirmed serious misconduct | 61 | 46 | 15 | 0 | 75.4% |
| Exclude alleged serious-misconduct dismissals | 52 | 35 | 17 | 0 | 67.3% |
| Exclude any s 124 contribution | 61 | 44 | 17 | 0 | 72.1% |

## Cross-year classification

The combined audit export contains 860 rows:

- 2020: 156
- 2021: 71
- 2022: 152
- 2023: 117
- 2024: 130
- 2025: 234

The 2024 rows are legally reviewed. Earlier and 2025 rows retain route/text
classification flags and should not be described as equivalent full legal
review without further inspection.

## Context enrichment

`enrich_context.py` creates:

`output/combined_2020_2025_context_enriched.csv`

It adds conservative, source-excerpt-backed fields for:

- explicitly stated employee ethnicity and gender;
- salary text and annualized salary range;
- occupation/collar signal;
- industry signal;
- representation mentioned in the decision.

Unstated attributes are `not_stated`. The script never infers ethnicity or
gender from names, pronouns, employers, or occupations. ERA decisions use
employee/employer terminology rather than criminal prosecution/defence
terminology, so representation is not automatically assigned to a side.

Salary normalization only accepts a stated dollar amount with an explicit
hour, week, fortnight, month, year, or annum unit. Hourly amounts assume 40
hours per week and 52 weeks per year. `$` is treated as NZD. Values without a
usable unit remain `not_stated` for annualized fields.

## Files

- `analyze_era.py` — download, deduplicate, extract, and initial review data.
- `combine_years.py` — combine year-level exports.
- `full_classification.py` — build the combined classification export.
- `enrich_context.py` — add context categories and salary normalization.
- `make_charts.py` — generate PNG charts using Pillow.
- `output/baseline_substantive_claims.csv` — 2024 substantive baseline.
- `output/combined_2020_2025_full_classification.csv` — combined audit export.
- `output/combined_2020_2025_context_enriched.csv` — enriched export.
- `output/uncertain_cases_for_human_legal_review.csv` — review queue.
- `output/charts/` — generated visualizations.

PDFs and extracted text are retained locally for auditability and ignored by
Git because they are bulk source material. CSVs, scripts, reports, and review
notes are the publishable outputs.

## Reproduce or add a year

```bash
python3 analyze_era.py --root years/2026 --year 2026
python3 combine_years.py
python3 enrich_context.py
python3 make_charts.py
pytest -q tests/test_analyze_era.py
```

Every new year needs its own merits review. Do not copy year-specific
overrides or infer serious misconduct from an employer allegation. Read the
operative findings, conclusions, and orders; deduplicate follow-up decisions.

## Source and redistribution

Source decisions are published by the [New Zealand Employment Relations
Authority](https://determinations.era.govt.nz/). Check the database terms
before redistributing PDFs.
