# Agent instructions for adding ERA years

This repository is an empirical legal-outcomes project. Legal merits and monetary outcomes are separate measures and must never be silently merged.

## Required workflow

1. Create `years/YYYY/` and run `analyze_era.py --root years/YYYY --year YYYY`.
2. Verify search pagination and unique PDF URLs. Run the recall audit before claiming the corpus is complete.
3. Extract text, repair OCR failures, and inspect every empty or suspiciously short result.
4. Read every possible merits determination individually, focusing on operative findings, conclusions, and orders.
5. Decide whether the determination belongs in the dismissal-merits denominator. Deduplicate follow-up determinations against the underlying merits decision.
6. Classify **legal merits** from the Authority's dismissal finding:
   - `employee_win` when the dismissal grievance succeeds / dismissal is unjustified.
   - `employer_win` when the dismissal grievance fails / dismissal is justified.
7. Score **monetary outcome separately** from final observable orders. A monetary result must never replace or tie-break the legal merits result.
8. For each included claim, preserve supporting paragraph/quotation, confidence, review notes, serious-misconduct allegation, Authority finding, substantive/procedural justification, s 124 contribution, remedies, and financial evidence where applicable.
9. Give a second source review to serious-misconduct, summary-dismissal, gross-misconduct, contribution, s 124, low-confidence, parser-audit, legal/monetary-disagreement, and unresolved-routing cases.
10. Run `build_outcome_summaries.py`, `make_dual_outcome_charts.py`, and the full test suite.
11. For context categories, run `enrich_context.py`, verify each source excerpt, and use `not_stated` for silent decisions.
12. If any required direct source reviews remain, the repository and website must be marked **unfinished** with the remaining count. Never present an automated cue audit as completed review, and never use “review required” as though review were being deferred to the user.

Automated outcome hints and source-cue audits are routing aids. Final legal classifications come from direct agent reading of the determination. Monetary classifications come from observable final orders plus direct audit where the parser cannot safely resolve them.

Year-specific reviewed overrides remain local to their source year. Do not add a new hard-coded calendar year to generic citation, date, or URL parsing.

The final handoff includes the raw-results CSV, substantive-claims CSV, unfinished-work ledger (which must be empty before claiming completion), legal outcomes, monetary outcomes, disagreement/audit queue, recall results, regenerated headline outputs/charts, and exact commands used.
