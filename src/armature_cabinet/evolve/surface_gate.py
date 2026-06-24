# src/armature_cabinet/evolve/surface_gate.py
"""Surface gate: enforce the layered auto/apply posture.

Invariant: guardrail surfaces are NEVER auto-applied. --apply cannot override;
only an explicit human --promote ack advances them. (invariant #2)
"""
from __future__ import annotations

from .types import RoutingDecision

_GUARDRAILS = {"guardrail"}


class ApplyFlagError(Exception):
    """Raised if a caller tries to force-apply a guardrail via a path that must error."""


def decide_gate(decision: RoutingDecision, *, force_apply: bool = False) -> str:
    if decision.surface in _GUARDRAILS:
        return "review"  # hard lock, regardless of force_apply
    if decision.surface == "none":
        return "none"
    return decision.gate  # auto or review as routed
