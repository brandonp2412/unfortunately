# Technical notes

## Scope

The corpus is made from public Employment Relations Authority determinations
returned by the ERA database search for `unjustified dismissal`. It covers
2020–2025 in the combined export, with 2010–2019 being added. This estimates
outcomes among disputes that reached a public determination; it is not an
employee grievance win probability. Settlements, confidential outcomes,
abandonment, and disputes never filed are outside the frame.

## Legal-review method

Each search result is downloaded, text is extracted with `pdftotext` (with OCR
fallback where required), and the operative findings, conclusion, and orders are
read individually for classification. Generated keyword hints and review queues
are navigation aids only; the agent performing the extension is responsible for
making and recording the final classification itself.

The merits baseline excludes costs-only, procedural/interlocutory, compliance or
removal, withdrawn/discontinued, want-of-prosecution, duplicate/follow-up, and
non-merits decisions.

An employee win means the Authority found unjustified dismissal, even where
remedies were reduced for contribution. An employer win means the dismissal was
found justified or the dismissal grievance was rejected. `mixed_unclear` is
retained when the determination cannot fairly be reduced to either result.

Serious misconduct is split into three distinct ideas:

1. employer allegation;
2. Authority finding that the conduct occurred; and
3. Authority finding that the conduct amounted to serious misconduct.

Only the third is used for the strict serious-misconduct exclusion. Cases with
serious/gross/summary-dismissal wording, s 124 contribution, short/OCR-damaged
text, or a mixed/unclear outcome are re-read before finalization.

## 2024 results

| Analysis | Included | Employee wins | Employer wins | Mixed/other | Employee rate (all) |
|---|---:|---:|---:|---:|---:|
| Baseline | 63 | 46 | 17 | 0 | 73.0% |
| Exclude ERA-confirmed serious misconduct | 61 | 46 | 15 | 0 | 75.4% |
| Exclude alleged serious-misconduct dismissals | 52 | 35 | 17 | 0 | 67.3% |
| Exclude any s 124 contribution | 61 | 44 | 17 | 0 | 72.1% |

## Cross-year classification

The historical exports keep each search result auditable by source URL and
classification notes. Years are only included in reviewed combined outputs once
all search-result determinations for that year have a completed case-by-case
classification.

## Context enrichment

`enrich_context.py` creates conservative, source-excerpt-backed context fields
for explicitly stated employee ethnicity and gender, salary text and annualized
salary range, occupation/collar signal, industry signal, and representation
mentioned in the decision.

Unstated attributes are `not_stated`. The script never infers ethnicity or
gender from names, pronouns, employers, or occupations. ERA decisions use
employee/employer terminology rather than criminal prosecution/defence
terminology, so representation is not automatically assigned to a side.

Salary normalization only accepts a stated dollar amount with an explicit hour,
week, fortnight, month, year, or annum unit. Hourly amounts assume 40 hours per
week and 52 weeks per year. `$` is treated as NZD. Values without a usable unit
remain `not_stated` for annualized fields.

## Files

- `analyze_era.py` — download, deduplicate, extract, and initial routing data.
- `analyze_legacy_year.py` — acquire legacy-year source material.
- `build_review_dossier.py` — collect operative material for per-case reading.
- `make_legacy_review_brief.py` — compact navigation aid for exhaustive review.
- `validate_legacy_reviews.py` — refuse incomplete reviewed-year exports.
- `combine_years.py` — combine year-level exports.
- `full_classification.py` — build combined classification exports.
- `enrich_context.py` — add context categories and salary normalization.
- `make_charts.py` — generate PNG charts using Pillow.
- `output/baseline_substantive_claims.csv` — 2024 substantive baseline.
- `output/combined_2020_2025_full_classification.csv` — historical audit export.
- `output/charts/` — generated visualizations.

PDFs and extracted text may be retained outside Git because they are bulk source
material. CSVs, scripts, reports, source URLs, supporting findings, and review
notes are the publishable audit trail.

## Reproduce or add a year

```bash
python3 analyze_era.py --root years/2026 --year 2026
python3 combine_years.py
python3 enrich_context.py
python3 make_charts.py
pytest -q
```

Every new year needs its own determination-by-determination merits review. Do
not copy year-specific overrides or infer serious misconduct from an employer
allegation. Read the operative findings, conclusions, and orders; deduplicate
follow-up decisions; finish the classifications rather than deferring them.

## Source and redistribution

Source decisions are published by the [New Zealand Employment Relations
Authority](https://determinations.era.govt.nz/). Check the database terms before
redistributing PDFs.
