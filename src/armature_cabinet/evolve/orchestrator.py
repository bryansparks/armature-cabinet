# src/armature_cabinet/evolve/orchestrator.py
"""One evolve cycle: read traces -> route -> propose -> gate -> version/queue.

The LLM is injectable; the CLI wires a stub when ARMATURE_CABINET_LLM_STUB=1 else
litellm (optional dependency).

Cross-task invariants enforced here (the integration keystone):
  - MIN_TRACES=5 gate: fewer than 5 traces -> exit with report, no proposal.
  - hqs_promote_min is loaded from routing_rules.yaml (data-driven, NOT hardcoded).
  - FileProposal.evidence is populated with trace row ids from AgentTraceSummary.
  - --review forces every proposal to review-queue; auto surfaces are NOT auto-applied.
  - LoRA handoff is an orchestrator-level decide_lora step (not a router route):
    when prose is exhausted (>=2 flat cycles) and the routed skill's tools fire,
    hand off to adapter training; if not trained, fall back to prose and log
    missed_predictions.
  - Cabinet never imports armature; lora_handoff shells out.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from ..loader import load_package
from .router import route, load_rules
from .surface_gate import decide_gate
from .trace_reader import read_summary
from .proposer import propose_edit
from .patch_applier import apply_patch_to_folder, PatchReject
from .versioning import (write_version, promote, ThresholdPromotionPolicy,
                         rollback as evolve_rollback, read_latest)
from .lora_handoff import handoff_to_adapter, decide_lora
from .types import FileProposal
from .cycle_history import (read_history, append_record, prose_cycles_without_gain,
                            update_last_verified, detect_oscillation)
from .verifier import verify_prior

# Design spec: an agent needs at least this many traces before we will propose.
MIN_TRACES = 5


def _stub_llm(system: str, user: str) -> str:
    """Minimal safe patch: replace the first section of the target file body with a
    tightened output contract.

    Deterministic and network-free so tests never need a live LLM.

    Content-aware: the proposer passes the target file's content in the ``user``
    prompt, so we anchor on the first real ``## `` section header — or, when the file
    has no section headers (e.g. the real ``gmail-reader`` skills, which use a
    numbered-list body), on the first non-empty body line. This makes the stub apply
    cleanly to REAL agent folders, not just synthetic fixtures that happen to contain
    a literal ``## Output`` section.
    """
    # The proposer formats the user prompt as:
    #   "EVIDENCE:\n...\n\nFILE (<path>):\n<content>\n"
    file_content = ""
    marker = "FILE ("
    idx = user.find(marker)
    if idx != -1:
        nl = user.find("\n", idx)
        if nl != -1:
            file_content = user[nl + 1:]
    # Strip frontmatter so we only inspect the body.
    body = file_content
    if body.lstrip().startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4:].lstrip("\n")
    # Prefer a '## ' section header; fall back to the first non-empty body line.
    anchor = "## Output"
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("## "):
            anchor = s
            break
        if not s.startswith("---"):
            anchor = s
            break
    return json.dumps({
        "rationale": "tighten output contract (stub)",
        "frontmatter_changes": {},
        "body_changes": [{"op": "replace", "anchor": anchor,
                          "content": "## Output\nAlways produce valid JSON per the schema.\n"}],
        "predicted_fixes": ["output_invalid:stub"],
        "predicted_regressions": [],
        "confidence": 0.5,
    })


def _resolve_llm(pkg) -> callable:
    """Pick the llm_call. Stub when ARMATURE_CABINET_LLM_STUB is set; otherwise litellm.

    litellm is an OPTIONAL dependency: litellm_call raises a clean ImportError if the
    package is absent. The stub path never imports litellm.
    """
    if os.environ.get("ARMATURE_CABINET_LLM_STUB"):
        return _stub_llm
    hints = pkg.manifest.get("runtime_hints") or {}
    model = hints.get("proposer_model", "anthropic/claude-haiku-4-5-20251001")
    env = hints.get("proposer_api_key_env", "ANTHROPIC_API_KEY")
    from .proposer import litellm_call
    return litellm_call(model, env)


@dataclass
class CycleResult:
    rule_id: str
    target_file: str | None
    gate: str
    applied: bool
    version: str | None = None
    promoted: bool = False
    rationale: str = ""
    missed_predictions: list[dict] = field(default_factory=list)
    verified: str | None = None
    predicted_fixes: list[str] = field(default_factory=list)
    predicted_regressions: list[str] = field(default_factory=list)
    rolled_back: bool = False


def _bump_version(v: str | None) -> str:
    """Simple patch bump on the last segment of a dotted version string."""
    if not v:
        return "0.1.1"
    parts = v.split(".")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except ValueError:
        parts[-1] = "1"
    return ".".join(parts)


def _propose_and_apply(folder: Path, decision, summary, *, agent_version: str,
                       gate: str, review: bool, apply: bool,
                       current_hqs: float | None, hqs_promote_min: float,
                       pkg) -> CycleResult:
    """Shared prose route: propose -> (apply | queue .pending)."""
    target = folder / decision.target_file
    evidence = (f"{decision.symptom} x{dict(summary.dominant_symptoms).get(decision.symptom, 0)}; "
                f"heuristic={summary.heuristic}; rows={summary.evidence_row_ids[:10]}")
    proposal: FileProposal = propose_edit(
        decision=decision,
        file_content=target.read_text(encoding="utf-8"),
        evidence=evidence,
        llm_call=_resolve_llm(pkg),
    )
    # Cross-task #2: attach the trace row ids as evidence.
    proposal.evidence = summary.evidence_row_ids

    # Safe-by-default: emit .pending unless --apply is set. --review (or a routed
    # review gate) also forces .pending only — never apply. Without --apply, even
    # an auto-gate surface must NOT modify live files.
    if gate == "review" or review or not apply:
        vdir = folder / "versions" / _bump_version(agent_version)
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / ".pending.patch").write_text(
            json.dumps(proposal.__dict__, default=str), encoding="utf-8")
        return CycleResult(decision.rule_id, decision.target_file, "review", False,
                           rationale="emitted .pending patch for review",
                           predicted_fixes=proposal.predicted_fixes,
                           predicted_regressions=proposal.predicted_regressions)

    # gate == auto and --apply
    try:
        apply_patch_to_folder(folder, proposal)
    except PatchReject as e:
        return CycleResult(decision.rule_id, decision.target_file, "auto", False,
                           rationale=f"patch rejected: {e}",
                           predicted_fixes=proposal.predicted_fixes,
                           predicted_regressions=proposal.predicted_regressions)
    new_version = _bump_version(agent_version)
    write_version(folder, version=new_version, hqs=summary.hqs,
                  predicted_fixes=proposal.predicted_fixes)
    # Cross-task #1: data-driven promotion threshold from routing_rules.yaml.
    policy = ThresholdPromotionPolicy(min_gain=hqs_promote_min)
    promoted = promote(folder, new_version, policy=policy,
                       current_hqs=current_hqs, new_hqs=summary.hqs)
    return CycleResult(decision.rule_id, decision.target_file, "auto", True,
                       version=new_version, promoted=promoted,
                       rationale=proposal.rationale,
                       predicted_fixes=proposal.predicted_fixes,
                       predicted_regressions=proposal.predicted_regressions)


def run_evolve_cycle(folder: Path, *, traces_db: Path,
                     skill_tools: dict[str, list[str]],
                     apply: bool = False, review: bool = False,
                     current_version: str | None = None,
                     current_hqs: float | None = None,
                     history: list[dict] | None = None,
                     prose_cycles_without_gain_arg: int | None = None,
                     rollback_threshold: float = 0.05,
                     auto_rollback_guardrail: bool = True,
                     oscillating: bool | None = None,
                     latency_threshold_ms: float = 3000.0,
                     cost_threshold_tokens: float = 8000.0,
                     ) -> CycleResult:
    """Run one evolve cycle. Returns a CycleResult describing what happened.

    Boundary: never imports armature. lora_handoff shells out to `armature adapter create`.
    v2: reads the cycle-history sidecar, verifies+annotates the prior cycle's
    predicted_fixes (invariant #3), loads the package ONCE, and appends a record
    to <folder>/.evolve/history.jsonl.
    """
    pkg = load_package(folder)
    agent_id = pkg.id
    agent_version = current_version or pkg.manifest.get("version")

    history_records = history if history is not None else read_history(folder)
    prose_cycles = (prose_cycles_without_gain_arg
                    if prose_cycles_without_gain_arg is not None
                    else prose_cycles_without_gain(history_records))
    is_oscillating = oscillating if oscillating is not None else detect_oscillation(history_records)
    prior_latest = read_latest(folder)

    summary = read_summary(traces_db, agent_id=agent_id, agent_version=agent_version,
                           skill_tools=skill_tools, min_traces=MIN_TRACES,
                           latency_threshold_ms=latency_threshold_ms,
                           cost_threshold_tokens=cost_threshold_tokens)
    if summary is None:
        return CycleResult("none", None, "none", False,
                           rationale=f"insufficient traces (need >= {MIN_TRACES})")

    # v2: verify the prior cycle's predicted_fixes against current symptoms and
    # annotate the prior history record (observational — never blocks promotion).
    prior_verdict: str | None = None
    missed_predictions: list[dict] = []
    v = verify_prior(history_records, summary)
    if v is not None:
        prior_verdict = v.verdict
        update_last_verified(folder, v.verdict, vs_cycle=v.checked_cycle or 0)
        for pred in (history_records[-1].get("predicted_fixes") or []):
            tok = pred.split(":", 1)[0].upper()
            observed = tok in {s for s, _ in summary.dominant_symptoms}
            if observed:
                missed_predictions.append(
                    {"predicted": pred, "observed": tok, "verdict": v.verdict})

    rules = load_rules()
    decision = route(summary, skill_tools, rules=rules)
    hqs_promote_min = float(rules.get("hqs_promote_min", 0.02))

    # v2: LoRA is an orchestrator-level decision, not a router route. When prose
    # is exhausted (>=2 flat prose cycles) and the routed skill's tools fire
    # correctly, hand off to adapter training. If trained, skip prose. If not
    # trained (or --apply not set), fall back to prose with lora_missed.
    lora_rec = decide_lora(summary, prose_cycles_without_gain=prose_cycles,
                          skill_id=decision.skill_id)
    if lora_rec.eligible and decision.skill_id:
        role_type = pkg.manifest.get("kind", "worker")
        handoff = handoff_to_adapter(skill_id=decision.skill_id, role_type=role_type,
                                     dry_run=not apply)
        if handoff.trained:
            result = CycleResult(decision.rule_id, decision.target_file, "auto", True,
                                 rationale=f"lora adapter trained for {decision.skill_id}",
                                 missed_predictions=missed_predictions, verified=prior_verdict)
            _append_cycle_record(folder, decision, summary, result, history_records,
                                 prose_cycles, current_hqs)
            return result
        gate = "auto" if apply else "review"
        result = _prose_fallback(
            folder, decision, summary, agent_version=agent_version or "0.1.0",
            gate=gate, review=review, apply=apply,
            current_hqs=current_hqs, hqs_promote_min=hqs_promote_min,
            pkg=pkg, lora_missed=True,
        )
        result.missed_predictions = missed_predictions
        result.verified = prior_verdict
        _maybe_rollback(folder, result, decision,
                        current_hqs=current_hqs, new_hqs=summary.hqs,
                        rollback_threshold=rollback_threshold,
                        auto_rollback_guardrail=auto_rollback_guardrail,
                        prior_latest=prior_latest)
        _append_cycle_record(folder, decision, summary, result, history_records,
                             prose_cycles, current_hqs)
        return result

    if is_oscillating:
        gate = "review"   # stop auto-promoting a thrashing agent
    else:
        gate = decide_gate(decision, force_apply=apply)
    if decision.target_file is None or gate == "none":
        result = CycleResult(decision.rule_id, None, "none", False,
                             rationale=decision.rationale,
                             missed_predictions=missed_predictions, verified=prior_verdict)
        _append_cycle_record(folder, decision, summary, result, history_records,
                             prose_cycles, current_hqs)
        return result

    result = _prose_fallback(
        folder, decision, summary, agent_version=agent_version or "0.1.0",
        gate=gate, review=review, apply=apply,
        current_hqs=current_hqs, hqs_promote_min=hqs_promote_min, pkg=pkg,
    )
    _maybe_rollback(folder, result, decision,
                    current_hqs=current_hqs, new_hqs=summary.hqs,
                    rollback_threshold=rollback_threshold,
                    auto_rollback_guardrail=auto_rollback_guardrail,
                    prior_latest=prior_latest)
    result.missed_predictions = missed_predictions
    result.verified = prior_verdict
    _append_cycle_record(folder, decision, summary, result, history_records,
                         prose_cycles, current_hqs)
    return result


def _append_cycle_record(folder, decision, summary, result, history_records,
                         prose_cycles, current_hqs) -> None:
    """Append this cycle's record to .evolve/history.jsonl.

    Carries the proposal's predicted_fixes/predicted_regressions so next cycle's
    verify_prior has them (closes invariant #3 across cycles). ``decision`` may be
    None on the insufficient-traces early exit; ``summary`` may be None there too.
    """
    cycle = len(history_records) + 1
    append_record(folder, {
        "cycle": cycle,
        "proposed_file": decision.target_file if decision is not None else None,
        "gate": result.gate,
        "surface": decision.surface if decision is not None else "none",
        "hqs_before": current_hqs,
        "hqs_after": summary.hqs if summary is not None else None,
        "predicted_fixes": list(getattr(result, "predicted_fixes", [])),
        "predicted_regressions": list(getattr(result, "predicted_regressions", [])),
        "verified": {},
        "version": result.version,
        "rolled_back": bool(getattr(result, "rolled_back", False)),
    })


def _prose_fallback(folder: Path, decision, summary, *, agent_version: str,
                    gate: str, review: bool, apply: bool,
                    current_hqs: float | None, hqs_promote_min: float,
                    pkg, lora_missed: bool = False) -> CycleResult:
    """Run the prose propose/apply path. When lora_missed, annotate the rationale
    so callers can see the LoRA handoff failed and we fell back."""
    result = _propose_and_apply(
        folder, decision, summary, agent_version=agent_version,
        gate=gate, review=review, apply=apply,
        current_hqs=current_hqs, hqs_promote_min=hqs_promote_min, pkg=pkg,
    )
    if lora_missed:
        result.rationale = (f"lora handoff under-threshold; fell back to prose. "
                            f"missed_predictions logged. {result.rationale}")
    return result


def _maybe_rollback(folder, result, decision, *, current_hqs, new_hqs,
                    rollback_threshold, auto_rollback_guardrail, prior_latest) -> None:
    """If --apply patched the live folder but the HQS gate blocked promotion (a
    regression), restore the live folder to prior_latest.

    Guardrail-touched regressions: restore unconditionally (auto_rollback_guardrail).
    Non-guardrail regressions: restore only when drop >= rollback_threshold; a
    sub-threshold drop is left as a 'trial' on the live folder (latest unchanged)
    so a minor regression gets a next-cycle chance to prove out.
    Mutates `result` (rationale, rolled_back). Does NOT change latest (the gate
    already refused to advance it).
    """
    if not result.applied or result.promoted or prior_latest is None:
        return
    if current_hqs is None or new_hqs is None:
        return
    if new_hqs >= current_hqs:
        return  # not a regression (gate blocked for another reason)
    drop = current_hqs - new_hqs
    is_guardrail = decision.surface == "guardrail"
    if (is_guardrail and auto_rollback_guardrail) or (not is_guardrail and drop >= rollback_threshold):
        evolve_rollback(folder, prior_latest)
        why = "guardrail regression" if is_guardrail else f"drop {drop:.3f} >= {rollback_threshold}"
        result.rationale = f"rolled back live folder to {prior_latest} ({why}). {result.rationale}"
        result.rolled_back = True
    else:
        result.rationale = (f"regression {drop:.3f} < threshold {rollback_threshold}; "
                            f"left as trial on live folder (latest unchanged). {result.rationale}")
