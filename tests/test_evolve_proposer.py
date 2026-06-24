# tests/test_evolve_proposer.py
import json
from armature_cabinet.evolve.proposer import propose_edit, parse_proposal
from armature_cabinet.evolve.types import RoutingDecision


def _dec(target="skills/draft-reply.md", surface="skills", skill_id="draft-reply"):
    return RoutingDecision(target_file=target, surface=surface, gate="auto",
                           rationale="4/5 OUTPUT_INVALID", rule_id="R1",
                           symptom="OUTPUT_INVALID", skill_id=skill_id)


def _stub_llm(system, user):
    return json.dumps({
        "rationale": "tighten output contract",
        "frontmatter_changes": {"output_type": {"set": "guided_json"}},
        "body_changes": [{"op": "replace", "anchor": "## Output",
                          "content": "Always include `urgency`."}],
        "predicted_fixes": ["output_invalid:draft-reply"],
        "predicted_regressions": [],
        "confidence": 0.7,
    })


def test_propose_edit_returns_fileproposal():
    p = propose_edit(decision=_dec(), file_content="---\nid: draft-reply\n---\n\n## Output\nold",
                     evidence="4/5 OUTPUT_INVALID", llm_call=_stub_llm)
    assert p.target_file == "skills/draft-reply.md"
    assert p.frontmatter_changes == {"output_type": {"set": "guided_json"}}
    assert p.body_changes[0]["anchor"] == "## Output"
    assert p.predicted_fixes == ["output_invalid:draft-reply"]
    assert p.confidence == 0.7


def test_parse_proposal_rejects_malformed_json():
    import pytest
    with pytest.raises(ValueError):
        parse_proposal("not json", _dec())


def test_propose_edit_rejects_if_llm_targets_other_file():
    # The proposer is sandboxed: it must not emit a patch targeting a different file.
    import pytest
    def bad_llm(system, user):
        return json.dumps({"rationale": "x", "frontmatter_changes": {}, "body_changes": [],
                           "predicted_fixes": [], "predicted_regressions": [], "confidence": 0.5,
                           "target_file": "brakes.md"})  # wrong target
    with pytest.raises(ValueError, match="target"):
        propose_edit(decision=_dec(), file_content="x", evidence="e", llm_call=bad_llm)
