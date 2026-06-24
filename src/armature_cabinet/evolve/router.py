"""Deterministic symptom -> file router. The ONLY thing that picks a target file.

Pure: no I/O, no LLM. Data-driven by routing_rules.yaml.
"""
from __future__ import annotations
from importlib import resources
from pathlib import Path

import yaml

from .types import AgentTraceSummary, RoutingDecision


def load_rules(path: str | Path | None = None) -> dict:
    """Load the routing table. Defaults to the packaged routing_rules.yaml."""
    if path is not None:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    text = resources.files("armature_cabinet.evolve").joinpath("routing_rules.yaml").read_text()
    return yaml.safe_load(text)


def _surface_gate(rules: dict, surface: str) -> str:
    return rules["surfaces"].get(surface, "review")


def _pick_skill(summary: AgentTraceSummary, skill_tools: dict[str, list[str]]) -> str | None:
    """The failing, non-healthy skill to route to. Returns None if none attributable.

    A skill is attributable if it is failing (fail_count>0 or output_valid_rate<1.0)
    *or* if it declared tools that never fired (LOW_SKILL_ACTIVATION). The latter is
    detected via SkillStats.fired, which is False only when tools_declared is non-empty
    and none of those tools were called.
    """
    for sid in summary.per_skill:
        if sid in summary.healthy_skills:
            continue
        stats = summary.per_skill[sid]
        if stats.fail_count > 0 or stats.output_valid_rate < 1.0:
            return sid
        if stats.tools_declared and not stats.fired:
            return sid
    return None


def route(summary: AgentTraceSummary, skill_tools: dict[str, list[str]],
          rules: dict | None = None) -> RoutingDecision:
    rules = rules or load_rules()
    min_obs = rules["min_observations"]

    # Find the dominant modeled symptom.
    symptom: str | None = None
    count = 0
    for sym, c in summary.dominant_symptoms:
        if sym in {r["symptom"] for r in rules["rules"]} and c > count:
            symptom, count = sym, c
    if symptom is None or count < min_obs:
        return RoutingDecision(None, "none", "none",
                                f"no modeled symptom above min_observations ({min_obs})",
                                "unmodeled", symptom or "")

    skill_id = _pick_skill(summary, skill_tools)
    skill_attributable = skill_id is not None

    for rule in rules["rules"]:
        if rule["symptom"] != symptom:
            continue
        if "when_skill_attributable" in rule and rule["when_skill_attributable"] != skill_attributable:
            continue
        target = rule["target_file"]
        if "{skill_id}" in target:
            if skill_id is None:
                continue
            target = target.format(skill_id=skill_id)
        return RoutingDecision(
            target_file=target,
            surface=rule["surface"],
            gate=_surface_gate(rules, rule["surface"]),
            rationale=f"{symptom} observed {count}x; routing to {target}",
            rule_id=rule["id"],
            symptom=symptom,
            skill_id=skill_id,
            heuristic=summary.heuristic and rule["id"] == "R2",
        )

    return RoutingDecision(None, "none", "none", f"unmodeled symptom: {symptom}",
                           "unmodeled", symptom)
