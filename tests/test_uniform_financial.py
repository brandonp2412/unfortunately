from uniform_financial import direction, score_text


def test_employer_payment_to_employee_is_positive():
    text = """
    ORDERS
    [80] ABC Limited is ordered to pay Jane Smith $12,500 compensation.
    """
    scored = score_text(text, "JANE SMITH v ABC LIMITED")
    assert scored["financial_binary_outcome"] == "employee_win"
    assert scored["positive_money_signal"] is True
    assert scored["negative_money_signal"] is False


def test_employee_ordered_to_pay_employer_costs_is_loss():
    text = """
    ORDERS
    [12] I order Jane Smith to pay ABC Limited $2,250 as a contribution to costs.
    """
    scored = score_text(text, "JANE SMITH v ABC LIMITED")
    assert scored["financial_binary_outcome"] == "employer_win"
    assert scored["negative_money_signal"] is True


def test_employer_penalty_to_crown_is_not_employee_recovery():
    text = """
    ORDERS
    [44] ABC Limited is ordered to pay a penalty of $5,000 to the Crown account.
    """
    scored = score_text(text, "JANE SMITH v ABC LIMITED")
    assert scored["financial_binary_outcome"] == "employer_win"
    assert scored["positive_money_signal"] is False


def test_issue_question_is_not_an_award():
    text = """
    DETERMINATION
    Should Ms Smith be reimbursed the sum of $348.00 deducted from final wages?
    [51] I find that she should not be reimbursed.
    """
    scored = score_text(text, "JANE SMITH v ABC LIMITED")
    assert scored["financial_binary_outcome"] == "employer_win"
    assert scored["positive_money_signal"] is False


def test_unjustified_but_no_remedies_is_financial_loss():
    text = """
    CONCLUSION
    [51] Ms Smith was unjustifiably dismissed. No remedies are awarded. Costs are reserved.
    """
    scored = score_text(text, "JANE SMITH v ABC LIMITED")
    assert scored["financial_binary_outcome"] == "employer_win"
    assert scored["positive_money_signal"] is False


def test_nonquantified_lost_wages_order_is_still_positive():
    text = """
    ORDERS
    [90] The respondent is ordered to pay the applicant three months' lost wages.
    """
    scored = score_text(text, "JANE SMITH v ABC LIMITED")
    assert scored["financial_binary_outcome"] == "employee_win"
    assert scored["positive_money_signal"] is True
