from armature_cabinet.evolve.verifier import verify_predictions, verify_prior
from armature_cabinet.evolve.types import AgentTraceSummary


def _summary(symptoms, hqs=0.7):
    return AgentTraceSummary(agent_id="a", agent_version="0.2", n_traces=5,
                             output_valid_rate=0.8, success_rate=0.8, quorum=0.7,
                             escalation_rate=0.0, hqs=hqs, dominant_symptoms=symptoms)


def test_predicted_fix_landed():
    res = verify_predictions(prior_predicted_fixes=["output_invalid:draft-reply"],
                            prior_hqs=0.5, current=_summary(symptoms=[]))
    assert "output_invalid:draft-reply" in res.verified_fixes
    assert res.missed_predictions == []
    assert res.drift_score == 0.0


def test_predicted_fix_did_not_land():
    res = verify_predictions(prior_predicted_fixes=["output_invalid:draft-reply"],
                            prior_hqs=0.5, current=_summary(symptoms=[("OUTPUT_INVALID", 4)]))
    assert "output_invalid:draft-reply" in res.missed_predictions
    assert res.verified_fixes == []


def test_regression_detected():
    # current hqs dropped below prior -> unexpected_regression
    res = verify_predictions(prior_predicted_fixes=[], prior_hqs=0.7,
                            current=_summary(symptoms=[("OUTPUT_INVALID", 4)], hqs=0.4))
    assert len(res.unexpected_regressions) >= 1
    assert res.drift_score > 0.0


def _summary_prior(symptoms):
    return AgentTraceSummary(
        agent_id="a", agent_version="0.1.0", n_traces=5,
        output_valid_rate=1.0, success_rate=1.0, quorum=0.5, escalation_rate=0.0,
        hqs=0.5, dominant_symptoms=symptoms, per_skill={}, healthy_skills=[],
        evidence_row_ids=[], heuristic=False,
    )


def test_verify_prior_none_when_no_history():
    assert verify_prior([], _summary_prior([("OUTPUT_INVALID", 3)])) is None


def test_verify_prior_fixed_when_predicted_symptom_gone():
    history = [{"cycle": 1, "predicted_fixes": ["output_invalid:draft-reply"],
                "predicted_regressions": []}]
    v = verify_prior(history, _summary_prior([("LOW_SKILL_ACTIVATION", 3)]))
    assert v.verdict == "fixed"
    assert v.checked_cycle == 1


def test_verify_prior_unfixed_when_predicted_symptom_remains():
    history = [{"cycle": 1, "predicted_fixes": ["output_invalid:draft-reply"],
                "predicted_regressions": []}]
    v = verify_prior(history, _summary_prior([("OUTPUT_INVALID", 3)]))
    assert v.verdict == "unfixed"


def test_verify_prior_regressed_when_predicted_regression_appears():
    history = [{"cycle": 1, "predicted_fixes": ["output_invalid:draft-reply"],
                "predicted_regressions": ["low_skill_activation:triage"]}]
    v = verify_prior(history, _summary_prior([("LOW_SKILL_ACTIVATION", 3)]))
    assert v.verdict == "regressed"
