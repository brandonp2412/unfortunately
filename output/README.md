# Output guide

The `output/` directory contains both public results and research/audit artifacts.

## Canonical public results

Use `headline/` for statistics quoted outside the repository:

- `headline/legal_outcome_summary.csv`
- `headline/monetary_outcome_summary.csv`
- `headline/legal_vs_monetary_summary.csv`
- `headline/paired_case_outcomes.csv`
- `headline/manifest.json`
- `headline/README.md`

Use the `legal_*`, `monetary_*`, and `legal_vs_monetary_*` PNGs in `charts/` for outcome visualizations.

The canonical build requires every included determination to have both a legal-merits outcome and a monetary outcome. `build_outcome_summaries.py` fails rather than publishing unmatched cases.

## Audit and intermediate data

The `combined_*`, `uniform_*`, `financial_*`, per-year outputs, and scope ledgers exist to make the pipeline auditable and reproducible. Their filenames describe pipeline stages, not endorsement as headline statistics.

`binary_outcome_summary.csv` and the older unprefixed outcome chart names are historical/intermediate outputs from the previous mixed-measure presentation. Do not cite them as the canonical project result.

## Search recall

`recall/` contains the primary-vs-alternative-query audit. Alternate-query-only determinations are candidates for direct scope review; their presence does not automatically mean they belong in the dismissal-merits denominator.

The recall audit fails closed when the ERA search page cannot be parsed; a parser failure must not be published as a zero-result search.

Regenerate public summaries with:

```bash
python3 build_outcome_summaries.py
python3 make_dual_outcome_charts.py
```
