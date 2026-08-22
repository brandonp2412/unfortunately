# Agent instructions for adding ERA years

This repository is an empirical legal-outcomes project. A new year is not
complete when PDFs have merely been downloaded or keyword-classified.

## Required workflow

1. Create `years/YYYY/` and run `analyze_era.py --root years/YYYY --year YYYY`.
2. Verify the search pagination ended normally and count unique PDF URLs.
3. Extract text and OCR failures; inspect every row whose text is empty or
   suspiciously short.
4. Manually inspect every possible merits determination. Read the operative
   findings, conclusion, and orders—not just the background allegations.
5. Exclude costs-only, procedural/interlocutory, withdrawals, discontinuances,
   want-of-prosecution dismissals, compliance/removal decisions, duplicates,
   and decisions referring to another dismissal without deciding it.
6. For each included claim, code outcome, alleged reason, serious-misconduct
   allegation, ERA-confirmed conduct, substantive and procedural justification,
   s 124 contribution, percentage, remedies, supporting paragraph/quotation,
   confidence, and review notes.
7. Treat “serious misconduct” as ERA-confirmed only when the Authority finds
   both that the conduct occurred and that it amounted to serious misconduct.
8. Review every mixed/unclear outcome and every serious-misconduct,
   summary-dismissal, gross-misconduct, contribution, or s 124 hit twice.
9. Deduplicate follow-up determinations against the underlying merits decision.
10. Recalculate all published tables from the reviewed CSV and run the tests.
11. If context categories are requested, run `python3 enrich_context.py`.
    Treat its fields as extraction candidates only: verify the source excerpt,
    keep `not_stated` where the decision is silent, and do not infer ethnicity,
    gender, salary rate, or party representation.

## Prohibited shortcuts

- Never use the automated outcome hint as the final legal outcome.
- Never classify an allegation as proven serious misconduct.
- Never force an unclear case into employee/employer win.
- Never copy year-specific classification overrides into another year.
- Never report a percentage while mixed/uncertain cases remain unreviewed.

The final handoff must include the raw-results CSV, the substantive-claims CSV,
the uncertain-case list, the report, and the exact script command used.
