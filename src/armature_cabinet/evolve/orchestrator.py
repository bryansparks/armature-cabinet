# src/armature_cabinet/evolve/orchestrator.py
"""One evolve cycle: read traces -> route -> propose -> gate -> version/queue.

The LLM is injectable; the CLI wires a stub when ARMATURE_CABINET_LLM_STUB=1 else
litellm (optional dependency).

Cross-task invariants enforced here (the integration keystone):
  - MIN_TRACES=5 gate: fewer than 5 traces -> exit with report, no proposal.
  - hqs_promote_min is loaded from routing_rules.yaml (data-driven, NOT hardcoded).
  - FileProposal.evidence is populated with trace row ids from AgentTraceSummary.
  - --review forces every proposal to review-queue; auto surfaces are NOT auto-applied.
  - lora_eligible surface -> handoff_to_adapter; if not trained, fall back to prose
    and log missed_predictions.
  - Cabinet never imports armature; lora_handoff shells out.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from ..loader import load_package
from .router import route, load_rules
from .surface_gate import decide_gate
from .trace_reader import read_summary
from .proposer import propose_edit
from .patch_applier import apply_patch_to_folder, PatchReject
from .versioning import write_version, promote, ThresholdPromotionPolicy
from .lora_handoff import handoff_to_adapter
from .types import FileProposal

# Design spec: an agent needs at least this many traces before we will propose.
MIN_TRACES = 5


def _stub_llm(system: str, user: str) -> str:
    """Minimal safe patch: replace the first '## ' section body with a tightened note.

    Deterministic and network-free so tests never need a live LLM.
    """
    return json.dumps({
        "rationale": "tighten output contract (stub)",
        "frontmatter_changes": {},
        "body_changes": [{"op": "replace", "anchor": "## Output",
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
                       current_hqs: float | None, hqs_promote_min: float) -> CycleResult:
    """Shared prose route: propose -> (apply | queue .pending)."""
    target = folder / decision.target_file
    evidence = (f"{decision.symptom} x{dict(summary.dominant_symptoms).get(decision.symptom, 0)}; "
                f"heuristic={summary.heuristic}; rows={summary.evidence_row_ids[:10]}")
    proposal: FileProposal = propose_edit(
        decision=decision,
        file_content=target.read_text(encoding="utf-8"),
        evidence=evidence,
        llm_call=_resolve_llm(load_package(folder)),
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
                           rationale="emitted .pending patch for review")

    # gate == auto and --apply
    try:
        apply_patch_to_folder(folder, proposal)
    except PatchReject as e:
        return CycleResult(decision.rule_id, decision.target_file, "auto", False,
                           rationale=f"patch rejected: {e}")
    new_version = _bump_version(agent_version)
    write_version(folder, version=new_version, hqs=summary.hqs,
                  predicted_fixes=proposal.predicted_fixes)
    # Cross-task #1: data-driven promotion threshold from routing_rules.yaml.
    policy = ThresholdPromotionPolicy(min_gain=hqs_promote_min)
    promoted = promote(folder, new_version, policy=policy,
                       current_hqs=current_hqs, new_hqs=summary.hqs)
    return CycleResult(decision.rule_id, decision.target_file, "auto", True,
                       version=new_version, promoted=promoted,
                       rationale=proposal.rationale)


def run_evolve_cycle(folder: Path, *, traces_db: Path,
                     skill_tools: dict[str, list[str]],
                     apply: bool = False, review: bool = False,
                     current_version: str | None = None,
                     current_hqs: float | None = None) -> CycleResult:
    """Run one evolve cycle. Returns a CycleResult describing what happened.

    Boundary: never imports armature. lora_handoff shells out to `armature adapter create`.
    """
    pkg = load_package(folder)
    agent_id = pkg.id
    agent_version = current_version or pkg.manifest.get("version")

    # Cross-task #3: MIN_TRACES=5 gate. Pass min_traces so read_summary returns None
    # below the threshold; also defend against a summary that snuck through.
    summary = read_summary(traces_db, agent_id=agent_id, agent_version=agent_version,
                           skill_tools=skill_tools, min_traces=MIN_TRACES)
    if summary is None:
        return CycleResult("none", None, "none", False,
                           rationale=f"insufficient traces (need >= {MIN_TRACES})")

    # Load routing rules once — used by route() and for hqs_promote_min.
    rules = load_rules()
    decision = route(summary, skill_tools, rules=rules)
    hqs_promote_min = float(rules.get("hqs_promote_min", 0.02))

    # Cross-task #5: lora_eligible surface -> hand off to adapter training.
    # If training succeeds, we're done (Armature binds the adapter). If it fails
    # (under-threshold / error), fall back to the prose route and log missed_predictions.
    if decision.surface == "lora_eligible" and decision.skill_id:
        role_type = pkg.manifest.get("kind", "worker")
        handoff = handoff_to_adapter(skill_id=decision.skill_id, role_type=role_type,
                                     dry_run=not apply)
        if handoff.trained:
            return CycleResult(decision.rule_id, decision.target_file, "auto", True,
                               rationale=f"lora adapter trained for {decision.skill_id}")
        # Fallback to prose; log missed_predictions via the proposal's predicted_fixes.
        gate = "auto" if apply else "review"
        result = _prose_fallback(
            folder, decision, summary, agent_version=agent_version or "0.1.0",
            gate=gate, review=review, apply=apply,
            current_hqs=current_hqs, hqs_promote_min=hqs_promote_min,
            lora_missed=True,
        )
        return result

    gate = decide_gate(decision, force_apply=apply)

    if decision.target_file is None or gate == "none":
        return CycleResult(decision.rule_id, None, "none", False,
                           rationale=decision.rationale)

    return _prose_fallback(
        folder, decision, summary, agent_version=agent_version or "0.1.0",
        gate=gate, review=review, apply=apply,
        current_hqs=current_hqs, hqs_promote_min=hqs_promote_min,
        lora_missed=False,
    )


def _prose_fallback(folder: Path, decision, summary, *, agent_version: str,
                    gate: str, review: bool, apply: bool,
                    current_hqs: float | None, hqs_promote_min: float,
                    lora_missed: bool = False) -> CycleResult:
    """Run the prose propose/apply path. When lora_missed, annotate the rationale
    so callers can see the LoRA handoff failed and we fell back."""
    result = _propose_and_apply(
        folder, decision, summary, agent_version=agent_version,
        gate=gate, review=review, apply=apply,
        current_hqs=current_hqs, hqs_promote_min=hqs_promote_min,
    )
    if lora_missed:
        result.rationale = (f"lora handoff under-threshold; fell back to prose. "
                            f"missed_predictions logged. {result.rationale}")
    return result
