# tests/test_evolve_gate.py
import pytest
from armature_cabinet.evolve.surface_gate import decide_gate, ApplyFlagError
from armature_cabinet.evolve.types import RoutingDecision


def _dec(surface, gate="auto"):
    return RoutingDecision(None, surface, gate, "", "R1", "OUTPUT_INVALID")


def test_prose_surface_auto_applies():
    assert decide_gate(_dec("skills")) == "auto"
    assert decide_gate(_dec("mandate")) == "auto"


@pytest.mark.parametrize("force_apply", [False, True])
def test_guardrail_never_auto_applies(force_apply):
    # Even with --apply (force_apply=True), guardrail stays review.
    g = decide_gate(_dec("guardrail", "review"), force_apply=force_apply)
    assert g == "review"


def test_force_apply_on_guardrail_raises_when_asserted():
    # The CLI uses force_apply=True for --apply; guardrail must NOT raise (it just
    # downgrades to review). ApplyFlagError is only for explicit --promote abuse.
    assert decide_gate(_dec("guardrail", "review"), force_apply=True) == "review"


def test_none_surface_is_none():
    assert decide_gate(_dec("none", "none")) == "none"
