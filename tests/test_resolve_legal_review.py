from resolve_legal_review import resolve_text, strict_operative_match


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


def test_later_operative_finding_wins() -> None:
    text = (
        "The applicant says the dismissal was not justified. "
        + "x" * 500
        + " The Authority concludes the dismissal was justified."
    )
    outcome, status, evidence = resolve_text(text)
    assert outcome == "employer_win"
    assert status == "explicit_source_cue_agreement"
    assert "dismissal was justified" in evidence.lower()


def test_money_only_language_does_not_resolve_legal_merits() -> None:
    text = "The respondent is ordered to pay $25,000 compensation and $10,000 lost wages."
    outcome, status, evidence = resolve_text(text)
    assert outcome == "review_required"
    assert status == "no_explicit_binary_source_cue"
    assert evidence == ""
