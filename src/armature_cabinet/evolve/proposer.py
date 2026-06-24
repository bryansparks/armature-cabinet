# src/armature_cabinet/evolve/proposer.py
"""LLM proposer, sandboxed to a single file. The LLM never chooses the target —
the router did. The LLM only writes content inside that one file.

The LLM is dependency-injected as llm_call(system, user) -> str returning a JSON
proposal. Tests inject a stub; runtime wires a real client (optional litellm import).
"""
from __future__ import annotations
import json
from typing import Any, Callable

from .types import FileProposal, RoutingDecision

_SYSTEM_PROMPT = """You improve ONE file in a Cabinet agent definition. You are given
the file's current content and the trace evidence that justifies the change. Output
ONLY a JSON object with keys: rationale, frontmatter_changes (each value {"set": v} or
{"remove": true}), body_changes (list of {op: "replace"|"insert", anchor: "## Section",
content: str}), predicted_fixes (list[str]), predicted_regressions (list[str]),
confidence (float 0-1). Do NOT name a target_file; the caller enforces it. Do NOT touch
any other file. If the evidence does not justify an edit, return confidence 0 and empty
changes."""


def parse_proposal(raw: str, decision: RoutingDecision) -> FileProposal:
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"proposer returned non-JSON: {e}") from e
    if data.get("target_file") and data["target_file"] != decision.target_file:
        raise ValueError(f"proposer targeted {data['target_file']!r}, expected {decision.target_file!r}")
    return FileProposal(
        target_file=decision.target_file,
        surface=decision.surface,
        gate=decision.gate,
        rationale=str(data.get("rationale", decision.rationale)),
        frontmatter_changes=data.get("frontmatter_changes", {}) or {},
        body_changes=data.get("body_changes", []) or [],
        predicted_fixes=list(data.get("predicted_fixes", []) or []),
        predicted_regressions=list(data.get("predicted_regressions", []) or []),
        confidence=float(data.get("confidence", 0.0)),
        rule_id=decision.rule_id,
        skill_id=decision.skill_id,
    )


def propose_edit(*, decision: RoutingDecision, file_content: str, evidence: str,
                 llm_call: Callable[[str, str], str]) -> FileProposal:
    user = f"EVIDENCE:\n{evidence}\n\nFILE ({decision.target_file}):\n{file_content}\n"
    raw = llm_call(_SYSTEM_PROMPT, user)
    proposal = parse_proposal(raw, decision)
    proposal.evidence = []  # caller (evolve CLI) attaches row ids from the summary
    return proposal


def litellm_call(model: str, api_key_env: str) -> Callable[[str, str], str]:
    """Build a real llm_call using litellm (optional dependency). Raises ImportError
    with guidance if litellm is not installed."""
    try:
        import litellm  # type: ignore
    except ImportError as e:
        raise ImportError("The proposer needs `litellm`; install it to run evolve with a live LLM.") from e
    import os

    def _call(system: str, user: str) -> str:
        resp = litellm.completion(model=model, messages=[{"role": "system", "content": system},
                                                          {"role": "user", "content": user}],
                                  api_key=os.environ.get(api_key_env))
        return resp.choices[0].message.content or ""
    return _call
