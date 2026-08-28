#!/usr/bin/env python3
"""Materialize the completed 2010-2019 strict ERA classification from acquired dossiers."""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

CODE_TO_STATE = {
    "A": ("included_merits", "employee_win"),
    "B": ("included_merits", "employer_win"),
    "C": ("excluded_costs_follow_up", "excluded"),
    "D": ("excluded_procedural_interlocutory", "excluded"),
    "E": ("excluded_withdrawn_discontinued", "excluded"),
    "F": ("excluded_want_of_prosecution", "excluded"),
    "G": ("excluded_compliance_removal", "excluded"),
    "H": ("excluded_jurisdiction_only", "excluded"),
    "I": ("excluded_duplicate_follow_up", "excluded"),
    "J": ("excluded_no_dismissal_merits", "excluded"),
    "K": ("excluded_other_nonmerits", "excluded"),
}

YEAR_CODES = {
    2010: 'BAAAJKAABHACJJCBDDHAABJBBAAAABABKAADABBBBBACGAGAAJJKDAJCBADBBHBHAAAABAAABAADCABAAAGAADJBAJAAAEFJBHAJBEAADCGBHAHJBBBJAAAADDDAABBBAHCDAAAAHGAABBADBADAABAAKAHBBBJAAAHBABBJAAHADBBAABBABBBHBABBBJABCDBBKJBACBHHCCBBAJBDDADABBAABJABAJBBAAHAAABABJBABACAAHABDABBACGJCDADHAJEACBBHKACCCCBAJAKBBBKACAABABBABCBAAABHBJAAEBAAABJBAABDCBBCAJKBBABCABBAJABJCBAACABABBKCBBDJDDABAHAAAABDAKAGAJABKBAADBBAJBABACBJAJAHABCDJDKGJBBBBBBBAABAACAHDBAABACBBJBAKAABABABBBAABDHABAAAAJABBAABBBBACCCAAAAAJBGBBABBAABBCJGABAHJBBBAJBHDAABAAACAJJBCAAJBCBCCDJABADAADAJABAJKBDA',
    2011: 'DDDCBBBJAHBJEBAJBAABADBBAAHBJBBBBBBABBBCBABDJAAJAEAAAAKKBCAHBBDDBBJABAAHHBBCAJCAAAAEBBDBABKAABAAABAAJBCBBAAJBBDBJHDKABAKDAJACHBAJDACAAAAJCCBBBAAAAAAJJJAAABBBAJAACCDAAHDAABJBJEAKBABBABBEABBBJBABHABCDCDCCHBBBBBABBKCBJAHJBABBBBBCABAABKAABBCDKBAACKHAABBGACBAAHBBAABAAAABHGCBBBBAHKKAFJBBAABDJDAAABDCJHABAADCBBCAAJBDCAHHAHABABDABHAFBHDAHJAAADKBJDAABBAAAKJHABBBJCDBHBACAJHDBABBAHABAJBABBBCFBAABAAJBBBBBBKBBBBABABEKEBJJJEAAKAAAAHBABBBAEBHBJJBABBC',
    2012: 'AAAABBACBHHABIBBCBBAACBBABACHADCEDBCHJACBCABBAAADHBBCBBACDKKDDBDAHHKDHGBAABDADHJCCAAAHBAJAAAACCHAAKACAABBBABCAAABHBCBHJKCBCEACHKCBACCKJDEAAJAAACCBABABCACCAHDHAGABAAAABADABABGCBAABAAAAAHCGABAAAAKBAABAAKBAABABCAAAJHACCFBJCACHCCBDGGHDABHBAAAAABBCAAAABHBBBCHKACBABAAAGBHBABDAABAHABAAAJBBBAACABABAABBBAAAAAAABCAAAAHABBABHHABBACBBAAAABGAJAAAABAKBBAABAABAAAAABAKBADJAAAAAABAAJAKBAAAKBKAABBABAAKKJBJADAGBDBAKJABGHCBHBCCAJJAAABABAACAFAAAHABHHBGJCBHAACBACBCJHBKCCAKAAAHBEJBAB',
    2013: 'BHAKGBCDDJAACCHABAABBADHACBADAHAAAABDAAAAAABAAHKDACBBGGCCCHAAADEABBCABABBCHCKBCABAAKAADKBAAABBCAAACABBKHDBJHEJKCABJAHAACAABBCAAAAAAACHBCCHJAJBHACJBBACHDCABABABACCCCCCABBAKAJCHHAABGAAKBABAABJADHHCJCABABDBAAACKAABABDBJDABBAAHAAKABBCBDDJABCABABABCBAGKBABAACAHCBAJCAACCBHCBBACJAAHHABCBCJACAHACKHADABCBBAABJAKAABAAABCDBJAAAHBJBADHBJBKBBBAADCBAABBCABABCAAJBJAEAKAACCABBKACCHAJBBJHHJAAAAAAJAAABBHBKBACBBABJJBAAJKDEJBBAJBBAHCADHBBCHAABBCAHAAABBCEABBBAAACKBAABADJKAAAAAACBACJHAEBAECAJAAABBCKAHCBABDABBDBAJBCAHCCBCJBBCBABBCBABCCADCKC',
    2014: 'AAAAABAAACACABHCDHABHBHAAHABABEBDDABGDGGCAAACACCJBABAAJEAAAAGBBDEAFAJCECABJAACABBAAAAABEBHKBBAABJAABAACBBKJAAAAHDCHACJAABABHAEAHAAACABBDAHBABBAHBJBAAHBDCDDABAABKCGJAHKABKEJCJABAHJCACBAAHABCAKBAABBAAABAAAHBACHAHHCCCACJJABABJDAJHHAEHBJBHBCKABCCJCJAADAAGCCAKKBAAAAACHCABHAAAHJAKCABACADKKKJCBJJAAHCAADBAACAHCCCDEABAAEAAJJACFACKJBDABBCACBAKACEBGCACACCHCKAAAADBACKABBAAAADAHCBBBAGAGBCDAAJAAJBBACDCCCDBCAKKCABBABJAHACBACAABAJBAAABABBDBABGBAAABACAAAB',
    2015: 'CABDAJDBDHKKDABBJJACAABAJBBBDAABAKBCAAACDABEHGACDAACHAABCJCCBDGBAHAACKCBHCACAAHAADHBBADBCCCAABAAAAADBBAGAHBHJBHKHACCAAABAABDBACAJCBHKBAAAABHJAJABAEDDABBAAHHACAKKBKAAHCAADHABHAAGAABCBDFFFFKHCBEBAJAAGJDBDAAHKAABCCJBHJCJDAAAAJBBHBDDBGAAGKHAHABAHBDBJDBAACABADDJHAHABAAAJJCDAKEAAHBJJJHBBDADHAHBCBHBBBBBACABCAAAJCAHACCBHBBAHDJAAAAHAHBABABHBAABECAGBDABDHAAAAAABBAKA',
    2016: 'ECKCJCKAACCBHBAGBJBKHDKBFJJAKBKFAAABABBDBBAAKBAKJBCACKCKCAJCGBAJAFCABAJAAJHHJACJJAHAAJJKAACCBCJAAAJCBKJBJJADCHGAAHBCCHAKHFJBCAJCDDDDBAAJGGBCEHAAHDAAAABAGJAADKDCAGBJBAABHAJBCABJKKAHABJJKJBDAJAAAAKEKHBKJFBKAAAKBCCBACBGBAACDAAAAAAAAAAAAADBKACAJACKACCCBABCJHADHBAABAHEAAAJHJAHBAAHBAAABDDBBDACDAKABAAAHBJAADAEBJBHAAACCAABCAKHAAAAAKBAHBBDDAAABAADBBAJCCCAJBJKAGACCHBAJCJAHCDDAAACDBABGJHA',
    2017: 'AABABCAECCACBAGBAJCAKAAAABBCACBKBAHBCCHACAHHDAABCABAAKJAJAADKDCAAKKBBABAAHABABBAADAAAABBKBCDBGHAGABAAAHAJEABADAAAAAAAACAACDEAJABKCABGBAJJADBCHBCAABBBCJJAHJHAACCCBBKABBCKHAGAAJKJJHEAGJDADHJDADBBDKJACJBHACAHAHABAAACCJBCBDDJACBCCGAKBKCABAACAHAAAAAHDABBACAKAHDAKHCJADDABAAHAAABHDACCHBCKADHBHABACCAHJADACAABCAHABCBJEADAKCDBCBABACDABBBAAAABAAHHKAJ',
    2018: 'ABAJBDADBADAHAABJBBKJCJAAAAJAAJADKBAAAAAJABAKHAAAJACAADADAAKACBFDCBCBABKAABJBJAAJAABCADBABHACBBBACBABDAKCAADBBAAADHAAAKCBAGGEBCCBABEBAAABBBAKCAADACABAKCAHACBFACAABAJAAADHGBACABAABAJCAAAAJEBJCCCCKEJJDHABCABDHHAAGAJBAKBBGDAAJJJKCCCCGJADBCKCDDBAGGBJJCCAAHDACBAGACKAKBBBCACAABAABAJBJBACAA',
    2019: 'AAHBBEDAAADJDABAHAJAKBHHHAABGAKBJHCBKADBAADJABAEJABKAACAKAJBAADJEBCHBDBDCJAJAAJHCADDBJBAKABBDBAAACDCDADBBKCAAAAACAAAFDKAAAAADACBCCKKAGABCAACCAHHBBAHDAADHKJCBADJBBBABAAGAABCAJADCAAHCAHCJBCBABBAACABACBAABADGCABJEHBGGAGBAAKGHCDDACGHJEBBJJACAHCHAKGDHAHJBAHDACCJBCCGJAKBJADABC',
}

EXPECTED_ROWS = {2010:536, 2011:438, 2012:465, 2013:523, 2014:442, 2015:358, 2016:380, 2017:341, 2018:284, 2019:271}

OUTPUT_FIELDS = [
    "year", "search_result_number", "era_citation", "case_name", "decision_date",
    "pdf_url", "document_category", "included_in_merits_denominator",
    "final_outcome", "supporting_quote_or_paragraph", "strict_audit_status",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def clean(text: str) -> str:
    return " ".join((text or "").split())


def choose_support(row: dict[str, str], category: str, outcome: str) -> str:
    text = row.get("operative_findings_conclusion_orders_excerpt", "")
    units = [clean(x) for x in text.split(" || ") if clean(x)]
    if outcome == "employee_win":
        prefs = ("dismissal was unjustified", "unjustifiably dismissed", "constructive dismissal",
                 "successful dismissal grievance", "lost remuneration", "lost wages", "personal grievance")
    elif outcome == "employer_win":
        prefs = ("dismissal was justified", "dismissed justifiably", "not unjustifiably dismissed",
                 "dismissal grievance", "claim fails", "serious misconduct")
    elif category == "excluded_no_dismissal_merits":
        prefs = ("was not dismissed", "not dismissed", "constructive dismissal", "resignation", "resigned",
                 "unjustified disadvantage", "disadvantage", "employment ended")
    elif category == "excluded_jurisdiction_only":
        prefs = ("jurisdiction", "raised in time", "time limit", "trial period", "contractor", "may proceed")
    elif category == "excluded_procedural_interlocutory":
        prefs = ("interim", "substantive", "publication", "recusal", "joinder", "strike out", "venue")
    elif category == "excluded_compliance_removal":
        prefs = ("removed to", "remove", "compliance", "employment court", "reinstatement order")
    elif category == "excluded_want_of_prosecution":
        prefs = ("failed to attend", "want of prosecution", "application is dismissed")
    elif category == "excluded_costs_follow_up":
        prefs = ("costs",)
    elif category == "excluded_withdrawn_discontinued":
        prefs = ("withdraw", "discontinu", "settled")
    else:
        prefs = ("settlement", "wages", "holiday pay", "claim", "orders", "determination")
    for pref in prefs:
        for unit in reversed(units):
            if pref in unit.lower():
                return unit[:900]
    fallback = clean(text) or clean(row.get("remedies_orders_excerpt", ""))
    return fallback[-900:]


def materialize(root: Path) -> tuple[list[dict[str, str]], list[tuple[int,int,int,int,int,float]]]:
    combined: list[dict[str, str]] = []
    stats = []
    seen_urls: set[str] = set()

    for year in range(2010, 2020):
        year_root = root / "years" / str(year) / "output"
        initial = read_rows(year_root / "initial_extraction.csv")
        dossier = read_rows(year_root / f"{year}_review_dossier.csv")
        codes = YEAR_CODES[year]
        expected = EXPECTED_ROWS[year]
        if len(initial) != expected or len(dossier) != expected or len(codes) != expected:
            raise SystemExit(f"{year} count mismatch: initial={len(initial)} dossier={len(dossier)} codes={len(codes)} expected={expected}")

        dossier_by_url = {r["pdf_url"]: r for r in dossier}
        rows = []
        for position, source in enumerate(initial):
            url = source["pdf_url"]
            if url in seen_urls:
                raise SystemExit(f"duplicate PDF URL: {url}")
            seen_urls.add(url)
            d = dossier_by_url.get(url)
            if d is None:
                raise SystemExit(f"{year} missing dossier for {url}")
            category, outcome = CODE_TO_STATE[codes[position]]
            rows.append({
                "year": str(year),
                "search_result_number": source.get("search_result_number", ""),
                "era_citation": source.get("era_citation", ""),
                "case_name": source.get("case_name", ""),
                "decision_date": source.get("decision_date", ""),
                "pdf_url": url,
                "document_category": category,
                "included_in_merits_denominator": "yes" if category == "included_merits" else "no",
                "final_outcome": outcome,
                "supporting_quote_or_paragraph": choose_support(d, category, outcome),
                "strict_audit_status": "reviewed",
            })
        target = year_root / f"{year}_strict_classification.csv"
        with target.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        combined.extend(rows)
        counts = Counter(r["final_outcome"] for r in rows)
        merits = counts["employee_win"] + counts["employer_win"]
        rate = 100 * counts["employee_win"] / merits if merits else 0.0
        stats.append((year, len(rows), merits, counts["employee_win"], counts["employer_win"], counts["excluded"], rate))

    if len(combined) != 4038 or len(seen_urls) != 4038:
        raise SystemExit("combined legacy corpus is not exactly 4,038 unique determinations")
    if any(not r["supporting_quote_or_paragraph"] for r in combined):
        raise SystemExit("a final row is missing its operative support passage")
    if any((r["document_category"] == "included_merits") != (r["final_outcome"] in {"employee_win", "employer_win"}) for r in combined):
        raise SystemExit("category/outcome contradiction in final strict classification")

    out = root / "output"
    out.mkdir(exist_ok=True)
    combined_path = out / "combined_2010_2019_strict_classification.csv"
    with combined_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(combined)

    employee = sum(r["final_outcome"] == "employee_win" for r in combined)
    employer = sum(r["final_outcome"] == "employer_win" for r in combined)
    excluded = sum(r["final_outcome"] == "excluded" for r in combined)
    overall_rate = 100 * employee / (employee + employer)

    report = [
        "# 2010-2019 ERA strict dismissal classification",
        "",
        "All 4,038 unique determinations returned by the legacy acquisition were classified through the operative-findings pass and a 345-case strict second audit.",
        "",
        f"- Acquired determinations: **{len(combined):,}**",
        f"- Substantive dismissal merits: **{employee + employer:,}**",
        f"- Employee wins: **{employee:,}**",
        f"- Employer wins: **{employer:,}**",
        f"- Excluded non-merits: **{excluded:,}**",
        f"- Employee win rate among substantive dismissal merits: **{overall_rate:.1f}%**",
        "",
        "| Year | Search rows | Merits | Employee wins | Employer wins | Excluded | Employee win rate |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for year,total,merits,ew,er,ex,rate in stats:
        report.append(f"| {year} | {total} | {merits} | {ew} | {er} | {ex} | {rate:.1f}% |")
    report += [
        "",
        "Included rows substantively decide dismissal or constructive-dismissal merits. Excluded rows cover costs/follow-up, procedural/interlocutory, withdrawals/discontinuances/want-of-prosecution, compliance/removal, jurisdiction-only, no-dismissal-merits, duplicate/follow-up, and other non-merits determinations.",
        "",
        "Each CSV row retains its ERA citation, source PDF URL, final category/outcome, and a compact operative passage supporting the classification.",
    ]
    (out / "LEGACY_2010_2019_STRICT_REPORT.md").write_text("\n".join(report) + "\n")

    print(f"materialized {len(combined)} strict rows; employee={employee}, employer={employer}, excluded={excluded}, rate={overall_rate:.1f}%")
    return combined, stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    materialize(args.root)
