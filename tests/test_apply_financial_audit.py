from apply_financial_audit import apply_audit_to_row, normalize_citation


def row(citation: str, outcome: str = "employee_win", awarded: str = "999.00", adverse: str = "0.00") -> dict[str, str]:
    return {
        "era_citation": citation,
        "binary_outcome": outcome,
        "employee_money_awarded": awarded,
        "employee_money_adverse": adverse,
        "observable_net_money": awarded,
    }


def test_normalize_citation_handles_brackets_spaces_and_underscores():
    assert normalize_citation("[2024] NZERA 550") == "2024nzera550"
    assert normalize_citation("2020_NZERA_485") == "2020nzera485"


def test_remihana_question_is_audited_to_zero_recovery_loss():
    audited = apply_audit_to_row(row("2020_NZERA_485"))
    assert audited["binary_outcome"] == "employer_win"
    assert audited["employee_money_awarded"] == "0.00"
    assert audited["observable_net_money"] == "0.00"
    assert audited["financial_audit_status"] == "audited_override"


def test_burton_wage_orders_are_audited_to_employee_win():
    audited = apply_audit_to_row(row("2020 NZERA 314", outcome="employer_win", awarded="0.00"))
    assert audited["binary_outcome"] == "employee_win"
    assert audited["employee_money_awarded"] == "2892.77"
    assert audited["observable_net_money"] == "2892.77"


def test_named_employee_cost_order_is_audited_as_adverse_money():
    audited = apply_audit_to_row(row("[2024] NZERA 550"))
    assert audited["binary_outcome"] == "employer_win"
    assert audited["employee_money_awarded"] == "0.00"
    assert audited["employee_money_adverse"] == "2250.00"
    assert audited["observable_net_money"] == "-2250.00"


def test_both_sides_case_can_be_marked_confirmed_without_rewriting_amounts():
    original = row("2022 NZERA 109", outcome="employee_win", awarded="100.00", adverse="50.00")
    audited = apply_audit_to_row(original)
    assert audited["binary_outcome"] == "employee_win"
    assert audited["employee_money_awarded"] == "100.00"
    assert audited["employee_money_adverse"] == "50.00"
    assert audited["financial_audit_status"] == "audited_confirmed"
