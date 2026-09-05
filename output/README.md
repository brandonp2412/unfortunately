# Output guide

The `output/` directory contains both public results and research/audit artifacts.

## Canonical public results

Use `headline/` for statistics quoted outside the repository:

- `headline/legal_outcome_summary.csv`
- `headline/monetary_outcome_summary.csv`
- `headline/legal_vs_monetary_summary.csv`
- `headline/paired_case_outcomes.csv`
- `headline/unfinished_legal_cases.csv` — determinations for which direct agent legal-merits source review is still unfinished.
- `headline/manifest.json`
- `headline/README.md`

Use the `legal_*`, `monetary_*`, and `legal_vs_monetary_*` PNGs in `charts/` for outcome visualizations.

The legal headline is calculated only from cases with a direct binary legal-merits classification. If `unfinished_legal_cases.csv` is non-empty, the project is **unfinished** and the legal headline is provisional. Those rows are excluded until the reviewing agent completes direct source review; their monetary outcome is never used to fill the legal field. Automated source-cue audits are routing aids only and are non-canonical.

## Audit and intermediate data

The `combined_*`, `uniform_*`, `financial_*`, per-year outputs, unfinished-work lists, cue audits, and scope ledgers exist to make the pipeline auditable and reproducible. Their filenames describe pipeline stages, not endorsement as headline statistics.

`binary_outcome_summary.csv` and the older unprefixed outcome chart names are historical/intermediate outputs from the previous mixed-measure presentation. Do not cite them as the canonical project result.

## Search recall

`recall/` contains the primary-vs-alternative-query audit. Alternate-query-only determinations are candidates for direct scope review; their presence does not automatically mean they belong in the dismissal-merits denominator.

The recall audit fails closed when the ERA search page cannot be parsed; a parser failure must not be published as a zero-result search.

Regenerate public summaries with:

```bash
python3 build_outcome_summaries.py
python3 make_dual_outcome_charts.py
```
