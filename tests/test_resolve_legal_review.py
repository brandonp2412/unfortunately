from resolve_legal_review import final_operative_section, resolve_text, strict_operative_match


def test_strict_employee_cue_returns_evidence() -> None:
    text = "Background submissions.\nOrders\nThe dismissal was not justified. Remedies follow."
    outcome, evidence = strict_operative_match(text)
    assert outcome == "employee_win"
    assert "dismissal was not justified" in evidence.lower()


def test_strict_employer_cue_returns_evidence() -> None:
    text = "The employee alleged unjustified dismissal.\nConclusion\nThe dismissal was justified."
    outcome, evidence = strict_operative_match(text)
    assert outcome == "employer_win"
    assert "dismissal was justified" in evidence.lower()


def test_later_final_section_finding_wins() -> None:
    text = (
        "The applicant says the dismissal was not justified. "
        + "x" * 500
        + "\nConclusion\nThe Authority concludes the dismissal was justified."
    )
    outcome, status, evidence = resolve_text(text)
    assert outcome == "employer_win"
    assert status == "explicit_source_cue_agreement"
    assert "dismissal was justified" in evidence.lower()


def test_statutory_unjustified_wording_before_final_section_is_ignored() -> None:
    text = (
        "Section 103A prevents a finding that a dismissal was unjustified solely because of minor defects.\n"
        "Conclusion\nThe dismissal was justified."
    )
    section = final_operative_section(text)
    assert "103A" not in section
    outcome, status, evidence = resolve_text(text)
    assert outcome == "employer_win"
    assert status == "explicit_source_cue_agreement"
    assert "dismissal was justified" in evidence.lower()


def test_cue_without_explicit_final_section_stays_manual() -> None:
    text = "The dismissal was not justified."
    outcome, status, evidence = resolve_text(text)
    assert outcome == "review_required"
    assert status == "no_explicit_final_operative_section"
    assert evidence == ""


def test_money_only_language_does_not_resolve_legal_merits() -> None:
    text = "Orders\nThe respondent is ordered to pay $25,000 compensation and $10,000 lost wages."
    outcome, status, evidence = resolve_text(text)
    assert outcome == "review_required"
    assert status == "no_explicit_binary_source_cue_in_final_section"
    assert evidence == ""
