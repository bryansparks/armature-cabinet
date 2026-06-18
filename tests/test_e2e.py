"""North-star acceptance: a compiled bundle must round-trip through real armature.

Skipped entirely if ``armature-agents`` is not importable. Marked ``slow`` so CI
can deselect with ``-m 'not slow'`` (it imports litellm transitively).
"""
from pathlib import Path

import pytest

armature = pytest.importorskip("armature")
try:
    from armature.spec.loader import load_spec
except Exception:  # pragma: no cover - env-dependent
    pytest.skip("armature.spec.loader not available", allow_module_level=True)

pytestmark = pytest.mark.slow

WORKFLOW = Path(__file__).parent.parent / "examples" / "workflow.yml"


def test_bundle_roundtrips_through_armature():
    spec = load_spec(str(WORKFLOW))
    stage = next(s for s in spec.stages if s.id == "triage")
    assert stage.agent is None, "stage.agent should be cleared after resolution"
    assert stage.role.name == "Security Triage Partner"
    assert stage.role.type.value == "worker"
    assert len(stage.role.skills) == 3
    assert {"appsec.rank-findings"} <= set(spec.skill_library)


def test_incident_comms_stage_roundtrips():
    spec = load_spec(str(WORKFLOW))
    stage = next(s for s in spec.stages if s.id == "comms")
    assert stage.agent is None, "comms stage.agent should be cleared after resolution"
    assert stage.role.name == "Incident Comms Partner"
    assert stage.role.type.value == "worker"
    assert len(stage.role.skills) == 2
    assert {"comms.draft-status-update"} <= set(spec.skill_library)
    # two agents in one workflow: all 5 skills (3 appsec + 2 comms) merge without collision
    assert len(spec.skill_library) == 5, sorted(spec.skill_library)
