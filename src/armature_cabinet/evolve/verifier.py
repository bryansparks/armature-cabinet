# src/armature_cabinet/evolve/verifier.py
"""Verify a prior cycle's predicted_fixes against the current cycle's traces.
Mirrors Armature's falsifiable-contract shape (verified/missed/regressions/drift).

Read-only: consumes the next cycle's AgentTraceSummary (produced by trace_reader.read_summary)
and a prior AgentVersion's predicted_fixes. Writes nothing.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from .types import AgentTraceSummary


@dataclass
class VerificationResult:
    verified_fixes: list[str] = field(default_factory=list)
    missed_predictions: list[str] = field(default_factory=list)
    unexpected_regressions: list[str] = field(default_factory=list)
    drift_score: float = 0.0


def _symptom_token(pred: str) -> str:
    # "output_invalid:draft-reply" -> "OUTPUT_INVALID"
    return pred.split(":", 1)[0].upper()


def verify_predictions(*, prior_predicted_fixes: list[str], prior_hqs: float | None,
                       current: AgentTraceSummary) -> VerificationResult:
    current_symptoms = {sym for sym, _ in current.dominant_symptoms}
    res = VerificationResult()
    for pred in prior_predicted_fixes:
        tok = _symptom_token(pred)
        if tok in current_symptoms:
            res.missed_predictions.append(pred)
        else:
            res.verified_fixes.append(pred)
    if prior_hqs is not None and current.hqs < prior_hqs:
        res.unexpected_regressions.append(f"hqs: {prior_hqs:.3f} -> {current.hqs:.3f}")
        res.drift_score = prior_hqs - current.hqs
    return res
