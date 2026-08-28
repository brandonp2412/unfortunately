#!/usr/bin/env python3
"""Publish the completed 2010-2025 uniform dismissal-scope audit.

The main audit table contains the full reviewed routing. Three 2010 determinations
were directly confirmed as merits decisions during the final scope review but were
omitted from the initial durable override table; apply those exact decisions before
materializing the audited denominator.
"""
import apply_uniform_scope_audit as audit


audit.DIRECT.update({
    "aa15510": ("yes", "employer_win", "dismissal merits resolved against employee"),
    "aa3810": ("yes", "employee_win", "unjustified dismissal merits resolved for employee"),
    "aa2410": ("yes", "employee_win", "unjustified dismissal merits resolved for employee"),
})


if __name__ == "__main__":
    audit.main()
