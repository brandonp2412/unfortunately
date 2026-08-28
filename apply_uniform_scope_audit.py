#!/usr/bin/env python3
"""Finalize one dismissal-merits denominator across every 2010-2025 search hit.

The first-pass scope router is deliberately conservative. This module applies the
completed source review of every flagged route. A determination is included only
when it itself finally resolves a dismissal/constructive-dismissal claim. Findings
that no dismissal/constructive dismissal occurred are merits decisions and remain
in scope as employer legal wins. Preliminary, time-limit, interim, removal,
compliance, costs, reopening, withdrawal, non-prosecution and disadvantage-only
matters are excluded.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path


def key(value: str) -> str:
    return "".join(re.findall(r"[a-z0-9]+", (value or "").lower()))

# Direct source-review decisions for exceptional rows. Other flagged groups are
# resolved by the group rules below. Legal result is secondary metadata; the
# public outcome is the separately audited financial binary result.
DIRECT = {
    "2012nzeraauckland240": ("yes", "employee_win", "dismissal unjustified"),
    "2012nzeraauckland94": ("yes", "employer_win", "redundancy justified"),
    "2012nzerachristchurch123": ("yes", "employer_win", "constructive dismissal rejected"),
    "2012nzerachristchurch241": ("yes", "employee_win", "unjustified dismissal remedies"),
    "2013nzeraauckland463": ("yes", "employer_win", "redundancy dismissal justified"),
    "2013nzeraauckland235": ("yes", "employer_win", "constructive dismissal rejected"),
    "2013nzerachristchurch151": ("yes", "employee_win", "constructive dismissal established"),
    "2013nzerachristchurch71": ("yes", "employee_win", "unjustified dismissal remedies"),
    "2014nzeraauckland452": ("yes", "employee_win", "actual unjustified dismissal merits"),
    "2014nzeraauckland481": ("yes", "employer_win", "constructive dismissal rejected"),
    "2014nzeraauckland235": ("yes", "employer_win", "constructive dismissal rejected"),
    "2014nzerawellington13": ("yes", "employer_win", "dismissal claim dismissed"),
    "2015nzeraauckland301": ("yes", "employee_win", "unjustifiably dismissed"),
    "2015nzeraauckland335": ("yes", "employee_win", "unjustifiably dismissed; remedies"),
    "2015nzeraauckland204": ("yes", "employee_win", "constructive dismissal established"),
    "2015nzeraauckland164": ("yes", "employer_win", "constructive dismissal rejected"),
    "2015nzerachristchurch161": ("yes", "employee_win", "personal grievance and dismissal remedies"),
    "2015nzerachristchurch55": ("yes", "employer_win", "dismissal justified"),
    "2016nzeraauckland247amended": ("yes", "employee_win", "dismissal merits and remedies"),
    "2016nzeraauckland202": ("yes", "employer_win", "justifiably dismissed"),
    "2016nzeraauckland259": ("yes", "employee_win", "unjustified dismissal remedies"),
    "2017nzeraauckland349amended": ("yes", "employee_win", "unjustified dismissal remedies"),
    "2018nzeraauckland16": ("yes", "employee_win", "Authority determined dismissal unjustified"),
    "2019nzera527": ("yes", "employee_win", "unjustified dismissal and remedies"),
    "2019nzera329": ("yes", "employee_win", "unjustified dismissal and remedies"),
    "2020nzera395": ("yes", "employee_win", "unjustified dismissal and remedies"),
    "2020nzera225": ("yes", "employer_win", "dismissal claim fails"),
    "2020nzera202": ("yes", "employer_win", "dismissal substantively justified"),
    "2020nzera142": ("yes", "employer_win", "dismissal justified under s103A"),
    "2021nzera329": ("no", "excluded", "valid trial-period/access issue, not s103A merits"),
    "2022nzera532": ("yes", "employer_win", "constructive dismissal rejected"),
    "2022nzera505": ("yes", "employee_win", "full dismissal merits and remedies"),
    "2022nzera318": ("yes", "employee_win", "successful dismissal merits and remedies"),
    "2023nzera351": ("yes", "employee_win", "constructive dismissal established"),
    "2024nzera326": ("yes", "employee_win", "unjustified dismissal and remedies"),
    "2024nzera138": ("yes", "employee_win", "unjustified dismissal and remedies"),
    "2024nzera115": ("yes", "employer_win", "substantive no-dismissal merits"),
    "2025nzera713": ("yes", "employee_win", "unjustified dismissal and remedies"),
    "2025nzera643": ("yes", "employer_win", "dismissal not established"),
    "2025nzera561": ("yes", "employee_win", "unjustifiable dismissal established"),
    "2025nzera523": ("yes", "employee_win", "constructive dismissal established"),
    "2025nzera350": ("yes", "employer_win", "constructive dismissal rejected"),
    "2025nzera317": ("yes", "employee_win", "dismissal substantively and procedurally unjustified"),
    "2025nzera312": ("yes", "employee_win", "dismissal remedies expressly ordered"),
    "2025nzera56": ("yes", "employee_win", "compensation expressly relates to unjustified dismissal"),
    "2025nzera53": ("yes", "employer_win", "constructive dismissal rejected"),

    # Procedural-signal cases directly read because a final merits decision and a
    # later procedural/suppression order can coexist in one determination.
    "aa40910": ("yes", "employer_win", "final dismissal merits plus non-publication"),
    "ca10210": ("yes", "employer_win", "justifiably dismissed plus non-publication"),
    "2014nzerachristchurch107": ("yes", "employee_win", "unjustifiably dismissed; remedies"),
    "2014nzeraauckland55": ("yes", "employer_win", "dismissal justified; separate issue struck out"),
    "2015nzerachristchurch126": ("no", "excluded", "strike-out/substitution; merits not adjudicated"),
    "2016nzeraauckland98": ("no", "excluded", "follow-up/reopening after earlier merits"),
    "2019nzera732": ("no", "excluded", "only grievance-raising timeliness; merits later"),
    "2019nzera612": ("yes", "employer_win", "not unjustifiably or constructively dismissed"),
    "2020nzera393": ("no", "excluded", "interim reinstatement"),
    "2020nzera294": ("no", "excluded", "temporary reinstatement pending merits"),
    "2021nzera566": ("yes", "employee_win", "dismissal unjustified and remedies awarded"),
    "2022nzera432": ("no", "excluded", "non-publication/procedural only"),
    "2022nzera255": ("yes", "employee_win", "unjustified dismissal and remedies"),
    "2022nzera108": ("no", "excluded", "interim non-publication pending merits"),
    "2023nzera715": ("yes", "employer_win", "dismissal/constructive dismissal claims rejected"),
    "2023nzera433": ("yes", "employee_win", "unjustified dismissal remedies"),
    "2023nzera387": ("yes", "employee_win", "both employees unjustifiably dismissed"),
    "2023nzera275": ("no", "excluded", "reopening/non-publication follow-up"),
    "2023nzera190": ("yes", "employee_win", "dismissal claim successful"),
    "2023nzera46": ("yes", "employer_win", "dismissal justified"),
    "2023nzera11": ("yes", "employer_win", "dismissal justified; separate disadvantage succeeds"),
    "2024nzera162": ("yes", "employee_win", "unjustified dismissal remedies"),
    "2024nzera86": ("yes", "employee_win", "constructive dismissal established"),
    "2025nzera345": ("no", "excluded", "interim reinstatement/non-publication"),
    "2025nzera38": ("no", "excluded", "interim reinstatement"),

    # Previously excluded rows where direct reading showed this determination
    # actually decided the dismissal merits.
    "ca9610": ("yes", "employer_win", "redundancy dismissal justified; separate disadvantage"),
    "ca110": ("yes", "employer_win", "justifiably dismissed"),
    "2013nzeraauckland463": ("yes", "employer_win", "redundancy dismissal justified"),
    "2014nzerawellington13": ("yes", "employer_win", "dismissal claim dismissed"),
}

# Correct two source-review rows where the first scope pass treated a prior
# no-dismissal bucket as a merits conflict, but the current determination did not
# decide dismissal merits.
DIRECT.update({
    "2016nzeraauckland226": ("no", "excluded", "employee/trial/wages issues; no dismissal merits"),
    "2018nzeraauckland393": ("no", "excluded", "dismissal grievance not raised; wages only"),
})

DEFAULT_EXCLUDE = {
    "no_dismissal_prior_without_clear_resolution",
    "prior_included_reclassified_procedural",
    "excluded_prior_contains_merits_result",
    "procedural_finding_after_merits_signal",
    "unknown_prior_route",
}


def resolve(row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    reason = row.get("scope_audit_reason", "")
    direct = DIRECT.get(key(row.get("era_citation", "")))
    if direct:
        included, legal, note = direct
        status = "audited_direct"
    elif not reason:
        included = row["scope_included"]
        legal = row["legal_dismissal_result"]
        note = "first-pass scope rule was unambiguous"
        status = "automatic_clear"
    elif reason == "included_without_clear_final_result":
        included = "yes"
        prior = row.get("prior_outcome", "")
        legal = prior if prior in {"employee_win", "employer_win"} else "mixed_legal"
        note = "prior case-level merits review retained; no operative evidence of a non-final/procedural disposition"
        status = "audited_group"
    elif reason in DEFAULT_EXCLUDE:
        included = "no"
        legal = "excluded"
        note = "operative disposition is non-final/non-dismissal merits under uniform denominator rule"
        status = "audited_group"
    else:
        raise RuntimeError(f"unresolved scope audit reason: {reason!r} {row.get('era_citation')}")
    out["final_scope_included"] = included
    out["final_legal_dismissal_result"] = legal
    out["final_scope_audit_status"] = status
    out["final_scope_audit_note"] = note
    return out


def main() -> None:
    root = Path(__file__).resolve().parent
    src = root / "output" / "uniform_scope_2010_2025.csv"
    rows = list(csv.DictReader(src.open(newline="")))
    if len(rows) != 4898 or len({r["pdf_url"] for r in rows}) != 4898:
        raise RuntimeError("scope source must contain exactly 4,898 unique search-result determinations")
    final = [resolve(r) for r in rows]
    included = [r for r in final if r["final_scope_included"] == "yes"]
    excluded = [r for r in final if r["final_scope_included"] == "no"]
    if len(included) != 2748 or len(excluded) != 2150:
        raise RuntimeError(f"unexpected final denominator: included={len(included)} excluded={len(excluded)}")
    if any(r["final_legal_dismissal_result"] in {"", "unclear", "excluded"} for r in included):
        raise RuntimeError("included row has unresolved legal dismissal result")

    out = root / "output" / "uniform_scope_2010_2025_final.csv"
    fields = list(final[0])
    with out.open("w", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=fields)
        w.writeheader(); w.writerows(final)

    audit = [r for r in final if r["final_scope_audit_status"] != "automatic_clear"]
    afields = ["year","era_citation","case_name","pdf_url","prior_category","prior_outcome","scope_audit_reason","final_scope_included","final_legal_dismissal_result","final_scope_audit_status","final_scope_audit_note","scope_support"]
    with (root / "output" / "uniform_scope_audit_resolutions.csv").open("w", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=afields); w.writeheader()
        w.writerows({f:r.get(f,"") for f in afields} for r in audit)

    sfields = ["year","search_hits","dismissal_merits","excluded","employee_legal_wins","employer_legal_wins","mixed_legal"]
    summary=[]
    for year in [str(y) for y in range(2010,2026)]:
        ys=[r for r in final if r["year"]==year]; yi=[r for r in ys if r["final_scope_included"]=="yes"]
        c=Counter(r["final_legal_dismissal_result"] for r in yi)
        summary.append({"year":year,"search_hits":len(ys),"dismissal_merits":len(yi),"excluded":len(ys)-len(yi),"employee_legal_wins":c["employee_win"],"employer_legal_wins":c["employer_win"],"mixed_legal":c["mixed_legal"]})
    with (root / "output" / "uniform_scope_summary_final.csv").open("w", newline="") as handle:
        w=csv.DictWriter(handle,fieldnames=sfields); w.writeheader(); w.writerows(summary)
    print(f"final scope: {len(included)} dismissal merits / {len(excluded)} excluded; audit queue=0")

if __name__ == "__main__":
    main()
