from resolve_financial_outcomes import direction, order_window, score_text


def test_employee_positive_order():
    text = """
    ORDERS
    [80] The respondent is ordered to pay the applicant $12,500 for lost remuneration.
    """
    scored = score_text(text)
    assert scored["employee_money_awarded"] == 12500
    assert scored["observable_net_money"] == 12500
    assert scored["financial_binary_outcome"] == "employee_win"


def test_employee_adverse_costs_can_turn_case_into_loss():
    text = """
    ORDERS
    [80] The respondent is ordered to pay the applicant $1,000 compensation.
    [81] The applicant is ordered to pay the respondent $2,500 costs.
    """
    scored = score_text(text)
    assert scored["employee_money_awarded"] == 1000
    assert scored["employee_money_adverse"] == 2500
    assert scored["observable_net_money"] == -1500
    assert scored["financial_binary_outcome"] == "employer_win"


def test_zero_observable_recovery_is_loss():
    text = """
    CONCLUSION
    [40] The parties are to bear their own costs. No monetary remedy is awarded.
    """
    scored = score_text(text)
    assert scored["observable_net_money"] == 0
    assert scored["financial_binary_outcome"] == "employer_win"


def test_claimed_amount_is_not_automatically_award():
    assert direction("The applicant claimed $30,000 compensation.") == "neutral"


def test_order_window_prefers_last_orders_heading():
    text = "Claimed $50,000 earlier.\n\nORDERS\nThe respondent is ordered to pay the applicant $5,000.\n" + "x" * 1300
    assert "Claimed $50,000" not in order_window(text)
