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


@dataclass
class Verdict:
    verdict: str               # "fixed" | "unfixed" | "regressed"
    checked_cycle: int | None = None


def verify_prior(history: list[dict], current: AgentTraceSummary) -> Verdict | None:
    """Compare the LAST cycle's predicted_fixes / predicted_regressions against
    the current dominant symptoms. Read-only (the orchestrator writes the verdict
    back via cycle_history.update_last_verified). Returns None if no prior cycle.

      fixed     - no predicted fix symptom remains dominant, and no predicted
                  regression appeared.
      unfixed   - a predicted fix symptom is still dominant.
      regressed - a predicted regression is now dominant (takes precedence).
    """
    if not history:
        return None
    last = history[-1]
    current_symptoms = {sym for sym, _ in current.dominant_symptoms}
    pred_tokens = {_symptom_token(p) for p in (last.get("predicted_fixes") or [])}
    reg_tokens = {_symptom_token(p) for p in (last.get("predicted_regressions") or [])}
    if reg_tokens & current_symptoms:
        v = "regressed"
    elif pred_tokens & current_symptoms:
        v = "unfixed"
    else:
        v = "fixed"
    return Verdict(verdict=v, checked_cycle=last.get("cycle"))
