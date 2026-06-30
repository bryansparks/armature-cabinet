"""Compile a cabinet AgentPackage into the artifacts Armature consumes.

Output 1 — the CompiledAgent bundle (agent.yaml): `{role, skill_library}`.
   This is what a workflow's `agent_library` reference resolves to. It carries
   identity + capability only.

Output 2 — an advisory safety fragment (<id>.safety.yaml): the hard-enforcement
   pieces (forbidden actions, escalation gates, contract limits) that a
   CompiledAgent cannot carry today. The workflow author merges these in by hand.
   Brakes/trust are ALSO folded into the role prose as behavioral instruction so
   the agent self-governs even before the hard rules are wired.
"""
from __future__ import annotations
from typing import Any

from .errors import CabinetError
from .model import AgentPackage, Skill

# cabinet soul.type -> Armature RoleType (worker|orchestrator|judge|researcher)
_ROLE_TYPE = {"partner": "worker", "clone": "worker"}


def _role_type(pkg: AgentPackage) -> str:
    return pkg.soul_meta.get("armature_role_type") or _ROLE_TYPE.get(pkg.kind, "worker")


def _bullets(items: Any) -> str:
    if not items:
        return ""
    return "\n".join(f"- {x}" for x in items)


def compose_description(pkg: AgentPackage) -> str:
    """Fold soul + mandate + the behavioral parts of brakes/trust into one prose block."""
    parts: list[str] = []

    role_line = pkg.soul_meta.get("role")
    if role_line:
        parts.append(f"Your role: {role_line}.")
    if pkg.soul_body:
        parts.append(pkg.soul_body)

    expertise = pkg.soul_meta.get("expertise")
    if expertise:
        parts.append("Expertise:\n" + _bullets(expertise))

    temperament = pkg.soul_meta.get("temperament")
    if temperament:
        parts.append(f"Temperament: {temperament}")

    standards = pkg.soul_meta.get("standards")
    if standards:
        parts.append("Standards you hold to:\n" + _bullets(standards))

    # refusals (soul) + read-only / forbidden + halt-and-ask (brakes) => "you will not / you stop"
    refusals = list(pkg.soul_meta.get("refusals") or [])
    forbidden = list(pkg.brakes.get("forbidden_actions") or [])
    if forbidden:
        refusals.append("never take these actions: " + ", ".join(forbidden))
    if refusals:
        parts.append("You will not:\n" + _bullets(refusals))

    halt = pkg.brakes.get("halt_and_ask_when")
    if halt:
        parts.append("Stop and hand back to a human when:\n" + _bullets(halt))

    goal = pkg.mandate_meta.get("goal")
    oos = pkg.mandate_meta.get("out_of_scope")
    success = pkg.mandate_meta.get("success_looks_like")
    if goal or oos or success:
        mandate = []
        if goal:
            mandate.append(f"Your mandate: {goal}")
        if success:
            mandate.append("Success looks like:\n" + _bullets(success))
        if oos:
            mandate.append("Out of scope: " + ", ".join(oos))
        parts.append("\n".join(mandate))

    # trust => behavioral output requirements
    trust_reqs = []
    if pkg.trust.get("show_work") in ("required", "on_request"):
        trust_reqs.append("show your reasoning, not just conclusions")
    if pkg.trust.get("cite_sources") == "required":
        trust_reqs.append("cite the evidence behind every claim")
    if pkg.trust.get("uncertainty") == "must_flag":
        trust_reqs.append("state your confidence and what would change it")
    if trust_reqs:
        parts.append("When you respond, always:\n" + _bullets(trust_reqs))

    return "\n\n".join(p for p in parts if p).strip()


def _skill_entry(s: Skill, pkg: AgentPackage) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": s.id,
        "description": s.description or s.name or s.when or s.id,
        "content": s.body,
    }
    # thick metadata preserved via Armature's extra="allow"; x_ prefix keeps it clear
    if s.when:
        entry["x_when"] = s.when
    if s.tools:
        entry["x_tools"] = s.tools
    if s.cost_tier:
        entry["x_cost_tier"] = s.cost_tier
    if s.version:
        entry["x_version"] = s.version
    # resolved context refs -> their bodies (SkillDef allows extra)
    resolved = {ref: pkg.context[ref] for ref in s.context if ref in pkg.context}
    if resolved:
        entry["x_context"] = resolved
    # pass through any other skill frontmatter via extra="allow"
    for key, val in s.extra.items():
        entry[f"x_{key}"] = val
    return entry


def compile_agent(pkg: AgentPackage, *, include: list[str] | None = None) -> dict[str, Any]:
    """Produce the CompiledAgent bundle dict: {role, skill_library}.

    `include` optionally restricts which skill ids are attached (compile-time
    selection — the foundation for the woodshop `when`-based model). Default:
    attach all skills in the package.
    """
    if pkg.kind == "clone" and not (pkg.brakes.get("forbidden_actions") or []):
        raise CabinetError(
            f"clone agent {pkg.id!r} has no forbidden_actions; a clone that acts "
            f"unattended must declare hard brakes."
        )
    skills = pkg.skills if include is None else [s for s in pkg.skills if s.id in include]

    tools = sorted({t for s in skills for t in s.tools})
    role: dict[str, Any] = {
        "name": pkg.name,
        "type": _role_type(pkg),
        "description": compose_description(pkg),
        "tools": tools,
        "skills": [s.id for s in skills],
        # metadata along for the ride (Role has extra="allow")
        "x_kind": pkg.kind,
        "x_source": pkg.id,
    }
    schema_version = pkg.manifest.get("schema_version")
    if schema_version is not None:
        role["x_schema_version"] = schema_version
    version = pkg.manifest.get("version")
    if version is not None:
        role["x_agent_version"] = version
    for _rich in ("summary", "tags", "maturity", "runtime_hints"):
        val = pkg.manifest.get(_rich)
        if val is not None:
            role[f"x_{_rich}"] = val
    skill_library = {s.id: _skill_entry(s, pkg) for s in skills}
    bundle: dict[str, Any] = {"role": role, "skill_library": skill_library}
    block_rules = [
        {
            "tool": action,
            "condition": None,  # None = matches every call (armature >= 0.5.0)
            "action": "block",
            "message": f"{pkg.name} is forbidden from '{action}'.",
        }
        for action in (pkg.brakes.get("forbidden_actions") or [])
    ]
    if block_rules:
        bundle["safety_rules"] = block_rules
    return bundle


def compile_safety_fragment(pkg: AgentPackage) -> dict[str, Any]:
    """Advisory spec fragment for the hard enforcement a CompiledAgent can't carry.

    Block rules (forbidden_actions) are emitted onto the bundle's `safety_rules`
    by `compile_agent` (enforced there), so this fragment no longer carries them.
    It holds only advisory limits (iteration cap, USD ceiling), suggested
    escalation gates, and the merge-it-in `_note`.
    """
    suggested_gates = []
    for cond in pkg.trust.get("escalate_when") or []:
        suggested_gates.append(str(cond))

    fragment: dict[str, Any] = {
        "_note": (
            "ADVISORY. The CompiledAgent bundle carries this agent's block rules "
            "(`safety_rules`) as HARD constraints already. Merge these remaining "
            "advisory limits (`contracts:`) and escalation gates into your workflow."
        ),
    }
    contract: dict[str, Any] = {}
    if "max_iterations" in pkg.brakes:
        contract["max_iterations"] = pkg.brakes["max_iterations"]
    if "cost_ceiling_usd" in pkg.brakes:
        # no USD field in Contract yet — surfaced as a note (candidate core change)
        contract["_cost_ceiling_usd"] = pkg.brakes["cost_ceiling_usd"]
    if contract:
        fragment["contracts"] = contract
    if suggested_gates:
        fragment["suggested_escalation_gates"] = suggested_gates
    return fragment
