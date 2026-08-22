# NZ ERA dismissal decisions — 2025

What happened when New Zealand employees challenged dismissal at the Employment
Relations Authority in 2025?

This project downloads public ERA decisions, routes them for legal review, and
keeps the resulting evidence in auditable CSV files. The current README
highlights the most recent completed search: **2025**.

![Outcome classification by year](output/charts/outcomes_by_year.png)

*2025 is the largest search cohort shown. Its substantial mixed/unclear segment
is retained instead of being forced into a binary employee or employer result.*

## 2025 results

The official 2025 search returned **234 unique PDFs**. Following the initial
routing, **173 possible merits determinations** are included in the review
denominator. The remaining decisions were excluded as 34 costs/follow-up, 24
procedural/interlocutory, 2 compliance/removal, and 1
withdrawal/non-prosecution determination.

| Outcome | Cases |
|---|---:|
| Employee win | 75 |
| Employer win | 16 |
| Mixed/unclear | 82 |

The employee-win rate is **43.4%** across all 173 merits rows, or **82.4%**
among the 91 clear employee/employer outcomes. The difference is a useful
reminder that the headline depends on whether mixed and unclear determinations
are included.

Read the full 2025 report: [2025 categorized results](years/2025/output/2025_final_report.md).

## Important interpretation note

The 2025 file deliberately preserves mixed and unclear outcomes rather than
forcing a binary result. Its serious-misconduct fields are initial text-routing
flags, not confirmed findings: each needs operative-findings legal verification
before it can be reported as ERA-confirmed serious misconduct.

## Supporting charts

### Win-rate comparison

![Employee win rate by year](output/charts/employee_win_rate_by_year.png)

*Green shows all classified outcomes; blue shows only clear employee/employer
outcomes.*

### Overall outcome mix

![Overall outcome classification](output/charts/outcome_overall_pie.png)

### Serious-misconduct review status

![Serious-misconduct status by year](output/charts/serious_status_by_year.png)

*These are review-status categories, not a count of confirmed serious
misconduct findings.*

### Case context

![Industry signal](output/charts/industry_overall_pie.png)

![Occupation collar signal](output/charts/collar_overall_pie.png)

## Project outputs

- [2025 categorized decisions](years/2025/output/2025_final_categorized.csv)
- [2025 review queue](years/2025/output/2025_categorized_review_queue.csv)
- [2025 initial extraction](years/2025/output/initial_extraction.csv)
- [Combined 2020–2025 report](output/final_report.md)

The combined historical outputs and charts remain available for comparison, but
they are not the focus of the current report.

## Reproduce or extend

```bash
python3 analyze_era.py --root years/2026 --year 2026
python3 combine_years.py
python3 enrich_context.py
python3 make_charts.py
pytest -q tests/test_analyze_era.py
```

The full method, field definitions, limitations, and audit trail are in
[TECHNICAL.md](TECHNICAL.md). Source decisions: [New Zealand ERA database](https://determinations.era.govt.nz/).
