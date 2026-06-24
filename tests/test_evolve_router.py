from armature_cabinet.evolve.types import AgentTraceSummary, SkillStats
from armature_cabinet.evolve.router import route, load_rules


def _summary(agent_id="a", version="0.1", skills=None, symptoms=None, healthy=None, heuristic=False):
    return AgentTraceSummary(
        agent_id=agent_id, agent_version=version, n_traces=5,
        output_valid_rate=0.4, success_rate=0.4, quorum=0.5, escalation_rate=0.2, hqs=0.5,
        per_skill=skills or {}, dominant_symptoms=symptoms or [], healthy_skills=healthy or [],
        heuristic=heuristic,
    )


def test_r1_routes_invalid_output_to_skill():
    s = _summary(skills={"draft-reply": SkillStats("draft-reply", fail_count=4, output_valid_rate=0.2)},
                 symptoms=[("OUTPUT_INVALID", 4)])
    d = route(s, skill_tools={"draft-reply": ["gmail:draft.create"]})
    assert d.target_file == "skills/draft-reply.md"
    assert d.surface == "skills"
    assert d.gate == "auto"
    assert d.rule_id == "R1"
    assert d.skill_id == "draft-reply"


def test_r2_routes_invalid_output_to_mandate_when_no_skill():
    s = _summary(symptoms=[("OUTPUT_INVALID", 4)])  # no per_skill, no skill attributable
    d = route(s, skill_tools={})
    assert d.target_file == "mandate.md"
    assert d.surface == "mandate"
    assert d.gate == "auto"
    assert d.rule_id == "R2"
    assert d.heuristic is False  # R2 is the legitimate stage-level route, not a heuristic fallback


def test_r2_heuristic_when_attribution_absent():
    s = _summary(symptoms=[("OUTPUT_INVALID", 4)], heuristic=True)
    d = route(s, skill_tools={})
    assert d.rule_id == "R2"
    assert d.heuristic is True


def test_r3_routes_low_skill_activation():
    s = _summary(
        skills={"triage-inbox": SkillStats("triage-inbox", tools_declared=["gmail:messages.list"],
                                           tools_called=[])},
        symptoms=[("LOW_SKILL_ACTIVATION", 3)])
    d = route(s, skill_tools={"triage-inbox": ["gmail:messages.list"]})
    assert d.target_file == "skills/triage-inbox.md"
    assert d.surface == "skills+soul"
    assert d.rule_id == "R3"


def test_guardrails_are_review_gated():
    s = _summary(symptoms=[("REFUSAL_OR_FALSE_HALT", 3)])
    d = route(s, skill_tools={})
    assert d.target_file == "brakes.md"
    assert d.surface == "guardrail"
    assert d.gate == "review"
    assert d.rule_id == "G1"


def test_unmodeled_symptom_is_noop():
    s = _summary(symptoms=[("SOMETHING_NEW", 5)])
    d = route(s, skill_tools={})
    assert d.target_file is None
    assert d.gate == "none"
    assert d.rule_id == "unmodeled"


def test_healthy_skill_is_skipped():
    # draft-reply is in healthy_skills -> not routed even if it has failures
    s = _summary(skills={"draft-reply": SkillStats("draft-reply", fail_count=4)},
                 symptoms=[("OUTPUT_INVALID", 4)], healthy=["draft-reply"])
    d = route(s, skill_tools={"draft-reply": ["gmail:draft.create"]})
    # Falls through to R2 (stage-level) since the only failing skill is healthy
    assert d.rule_id == "R2"


def test_below_min_observations_is_noop():
    s = _summary(symptoms=[("OUTPUT_INVALID", 2)])  # < min_observations (3)
    d = route(s, skill_tools={})
    assert d.target_file is None
    assert d.gate == "none"


def test_load_rules_returns_table():
    rules = load_rules()
    assert rules["min_observations"] == 3
    assert any(r["id"] == "R1" for r in rules["rules"])
