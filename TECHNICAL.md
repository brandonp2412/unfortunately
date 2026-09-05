# Technical notes

## Scope

The project studies public Employment Relations Authority determinations returned by the ERA determinations database for the primary search phrase `unjustified dismissal`, currently covering 2010–2025.

That is a **search-derived corpus**, not an asserted census of every dismissal determination. Costs-only, procedural, compliance, withdrawal, duplicate, jurisdiction-only, and follow-up decisions remain visible in audit material but are excluded from merits analyses when they do not finally determine a dismissal or constructive-dismissal claim.

`audit_search_recall.py` compares the primary query with alternative phrases including `unjustifiably dismissed`, `dismissal was not justified`, and `constructive dismissal`. Alternate-query-only determinations are candidates for direct scope review, not automatic additions. The live ERA site currently routes search results through `/determination/view/...` pages; `era_search.py` resolves those pages to source PDFs and makes both current and legacy acquisition use the same search parser. A search-page parse failure raises instead of being recorded as zero results.

## Two outcome measures

The repository deliberately publishes legal and monetary outcomes separately.

### Legal merits

Legal outcomes come from direct review of operative findings, conclusions, and orders:

- `employee_win`: the Authority upheld the dismissal grievance or found the dismissal unjustified.
- `employer_win`: the Authority rejected the dismissal grievance or found the dismissal justified.

Automated text cues and `audit_legal_source_cues.py` are routing aids only. They never create or override a canonical legal classification; final legal coding requires direct agent reading of the determination.

Not every monetary-corpus determination currently has a binary legal-merits classification. Canonical output reports legal classification coverage explicitly and writes every unfinished case to `output/headline/unfinished_legal_cases.csv`. A non-empty unfinished list means the project is **unfinished** and the legal headline is provisional. A monetary result is never used to fill that legal gap.

Older and intermediate audit tables may still contain the literal pipeline state `review_required`. In those artifacts it means **unfinished agent review work**, not a request for the reader or repository user to perform the review. Canonical/public outputs use the explicit unfinished-work terminology.

### Monetary outcome

The monetary measure asks a different question: what observable net monetary order flowed to the employee in the public determination?

- `employee_win`: positive observable net money/remedy flow to the employee.
- `employer_win`: zero observable employee recovery or a net adverse monetary order.

Orders in both directions are netted when quantifiable and parser-sensitive cases are routed to direct source audit. Private legal fees or unstated settlements are not invented.

A case can therefore be a **legal employee win but a monetary employer win**, or vice versa. This is expected and is measured explicitly.

## Canonical headline outputs

`build_outcome_summaries.py` creates `output/headline/`:

- `legal_outcome_summary.csv` — legal-merits totals and rates by year.
- `monetary_outcome_summary.csv` — monetary totals and rates by year.
- `legal_vs_monetary_summary.csv` — paired-case rates, overlap, and disagreement.
- `paired_case_outcomes.csv` — case-level legal/monetary comparison.
- `unfinished_legal_cases.csv` — monetary-corpus determinations whose direct agent legal-merits source review is still unfinished.
- `manifest.json` — machine-readable definitions, source files, totals, and legal-classification coverage.
- `README.md` — generated human-readable headline summary.

The legal and monetary datasets may have different denominators. The paired comparison uses only determinations with both measures and reports unmatched cases explicitly.

The older root-level `output/binary_outcome_summary.csv` and mixed outcome chart filenames are retained only as historical/intermediate artifacts; they are not canonical headline statistics.

## Acquisition and parsing

`analyze_era.py` accepts a requested `--year` and `--keywords`. Citation and decision-date parsing are year-parameterized. `analyze_legacy_year.py` and `analyze_era.py` both use `era_search.py` for the current ERA result-detail-page format.

The outcome cue treats these materially different findings separately:

- `dismissal was not justified` → employee-side cue.
- `dismissal was justified` → employer-side cue.
- `dismissal was unjustified` → employee-side cue.
- `dismissal was not unjustified` → employer-side cue.

Regression tests cover these negation cases, current ERA result links, and multi-year citation/date parsing.

PDF text extraction uses `pdftotext`; short/empty results can fall back to OCR when the required binaries are available.

## Serious misconduct

Serious misconduct is coded as separate facts: employer allegation, Authority finding that the conduct occurred, and Authority finding that the conduct amounted to serious misconduct. Allegation alone is never treated as an Authority finding.

## Context enrichment

`enrich_context.py` records source-excerpt-backed context fields for stated employee ethnicity and gender, salary text and annualized salary range, occupation/collar signal, industry signal, and representation mentioned in the determination. Silent source fields use `not_stated`.

Salary normalization accepts explicit hour, week, fortnight, month, year, or annum units. Hourly amounts annualize at 40 hours per week and 52 weeks per year; `$` is treated as NZD.

## Output layout

See `output/README.md`. In short:

- `output/headline/` — canonical public statistics and legal-review coverage queue.
- `output/charts/` — public visualizations; filenames prefixed `legal_` or `monetary_` are canonical outcome charts.
- `output/recall/` — search-recall audit results.
- `output/uniform_*`, `output/combined_*`, queues, and audit ledgers — intermediate or audit datasets.

## Reproduce

```bash
python3 build_outcome_summaries.py
python3 make_dual_outcome_charts.py
python3 -m pytest -q
```

To acquire a new year:

```bash
python3 analyze_era.py --root years/2026 --year 2026
```

A year is not complete merely because automated routing produced an outcome. Completion requires determination-by-determination direct agent merits review, required monetary audits, deduplication, regenerated canonical outputs, an empty unfinished-work list for the claimed scope, and passing tests.

To audit search recall:

```bash
python3 audit_search_recall.py --year-start 2010 --year-end 2025
```

## Source

[New Zealand Employment Relations Authority determinations](https://determinations.era.govt.nz/)
