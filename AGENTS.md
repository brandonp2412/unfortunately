# Agent instructions for adding ERA years

This repository is an empirical legal-outcomes project. Each year is complete after every acquired determination has received substantive source review and the published outputs have been regenerated.

## Required workflow

1. Create `years/YYYY/` and run `analyze_era.py --root years/YYYY --year YYYY`.
2. Verify search pagination and count unique PDF URLs.
3. Extract text, repair OCR failures, and inspect every empty or suspiciously short result.
4. Read every possible merits determination individually, focusing on operative findings, conclusions, and orders.
5. Classify the merits denominator from decisions that determine dismissal or constructive-dismissal claims.
6. For each included claim, code `employee_win` or `employer_win`, alleged reason, serious-misconduct allegation, ERA-confirmed conduct, substantive and procedural justification, s 124 contribution, percentage, remedies, supporting paragraph/quotation, confidence, and review notes.
7. Record serious misconduct as ERA-confirmed when the Authority finds both that the conduct occurred and that it amounted to serious misconduct.
8. Give a second source review to serious-misconduct, summary-dismissal, gross-misconduct, contribution, s 124, low-confidence, and unresolved routing cases before final classification.
9. Deduplicate follow-up determinations against the underlying merits decision.
10. Recalculate all published tables and charts from the completed classifications and run the tests.
11. For context categories, run `python3 enrich_context.py`, verify each source excerpt, and use `not_stated` for silent decisions.

Automated outcome hints are routing aids. Final classifications come from direct reading of the determination. Year-specific overrides remain local to their source year.

The final handoff includes the raw-results CSV, substantive-claims CSV, review queue, report, and exact script command used.
