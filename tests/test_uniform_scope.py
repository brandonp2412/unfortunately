from uniform_scope import classify_scope


def test_no_dismissal_merits_is_in_scope_employer_win():
    out=classify_scope('[40] I find that Ms X was not constructively dismissed and her dismissal grievance fails.','excluded_no_dismissal_merits','excluded')
    assert out['scope_included']=='yes'
    assert out['legal_dismissal_result']=='employer_win'


def test_interim_reinstatement_is_excluded():
    out=classify_scope('[50] The application for interim reinstatement is declined. The substantive grievance will be investigated later.','included_merits','employee_win')
    assert out['scope_included']=='no'


def test_final_unjustified_dismissal_is_included():
    out=classify_scope('[51] I find that Ms X was unjustifiably dismissed. The employer is ordered to pay compensation.','included_merits','employee_win')
    assert out['scope_included']=='yes'
    assert out['legal_dismissal_result']=='employee_win'


def test_constructive_dismissal_failure_is_included_loss():
    out=classify_scope('[71] The constructive dismissal grievance is not established. The claim fails.','excluded_no_dismissal_merits','excluded')
    assert out['scope_included']=='yes'
    assert out['legal_dismissal_result']=='employer_win'


def test_costs_followup_not_reincluded_from_quoted_merits():
    out=classify_scope('[2] In the earlier determination Ms X was unjustifiably dismissed. [20] I order costs of $4,500.','excluded_costs_follow_up','excluded')
    assert out['scope_included']=='no'
    assert out['scope_audit_reason']=='excluded_prior_contains_merits_result'
