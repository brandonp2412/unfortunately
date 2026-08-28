# 2025 ERA unjustified-dismissal search: categorized results

The official 2025 search returned 234 unique PDFs. The completed routing is:

- 173 possible merits determinations included in the review denominator;
- 34 costs/follow-up determinations excluded;
- 24 procedural/interlocutory determinations excluded;
- 2 compliance/removal determinations excluded;
- 1 withdrawal/non-prosecution candidate excluded.

The original legal routing among the 173 possible merits determinations was:

| Original legal outcome | Count |
|---|---:|
| Employee win | 75 |
| Employer win | 16 |
| Mixed/unclear | 82 |

For the public binary outcome metric, the mixed/unclear rows are resolved from the operative monetary orders. Clear legal outcomes are preserved; for mixed rows, a positive observable employee-side net recovery is an employee win and zero or negative observable recovery is an employer win.

| Audited binary outcome | Count |
|---|---:|
| Employee win | 119 |
| Employer win | 54 |

The final 2025 employee-win rate is therefore **68.8% (119/173)** under the audited binary presentation.

The original `mixed_unclear` coding remains in the legal-classification export for auditability. The binary result is in `../../output/combined_2020_2025_binary_classification.csv`, with source-audited ambiguous monetary cases recorded in `../../output/mixed_financial_audit_resolutions.csv`.

Serious-misconduct routing fields are separate from the binary financial tie-breaker and must not be read as ERA-confirmed serious-misconduct findings unless the operative findings establish that conclusion.
