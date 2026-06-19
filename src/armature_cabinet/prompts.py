"""Interactive prompts that collect a cabinet agent's answers (questionary + rich).

The only module that imports questionary. Imported lazily by ``cli.cmd_new`` so
that ``import armature_cabinet`` and the build/validate commands never pull it in.
"""
from __future__ import annotations

import questionary
from rich.console import Console
from rich.panel import Panel

console = Console()

_KINDS = ["partner", "clone"]
_ROLE_TYPES = ["worker", "orchestrator", "judge", "researcher"]
_COST_TIERS = ["T1", "T2", "T3"]


def _section(title: str) -> None:
    console.print(Panel.fit(title, style="bold cyan"))


def _hint(hint: str) -> None:
    if hint:
        console.print(f"  [dim]{hint}[/dim]")


def _text(msg: str, default: str = "", hint: str = "") -> str:
    _hint(hint)
    return questionary.text(msg + ": ", default=default).ask() or ""


def _req_text(msg: str, default: str = "", hint: str = "") -> str:
    _hint(hint)
    while True:
        v = questionary.text(msg + ": ", default=default).ask()
        if v and v.strip():
            return v.strip()
        console.print("[red]Required — please enter a value.[/red]")


def _list(msg: str, hint: str = "") -> list[str]:
    _hint(hint)
    out: list[str] = []
    while True:
        v = questionary.text(f"{msg} (blank to finish): ").ask()
        if not v or not v.strip():
            break
        out.append(v.strip())
    return out


def _multiline(msg: str, hint: str = "") -> str:
    _hint(hint)
    console.print(f"{msg} (enter lines; blank line to finish):")
    lines: list[str] = []
    while True:
        v = input("... ")
        if not v.strip():
            break
        lines.append(v)
    return "\n".join(lines)


def _select(msg: str, choices: list[str], default: str | None = None,
            hint: str = "") -> str:
    _hint(hint)
    return questionary.select(msg, choices=choices, default=default).ask()


def _confirm(msg: str, default: bool = False, hint: str = "") -> bool:
    _hint(hint)
    return bool(questionary.confirm(msg, default=default).ask())


def collect_answers(id_: str | None = None) -> dict:
    """Walk the author through every cabinet field; return the answers dict."""
    _section("Identity")
    aid = id_ or _req_text("Agent id (folder name)",
                            hint="folder name + agent id; becomes x_source on the role")
    name = _text("Display name", default=aid,
                 hint="display name; becomes role.name")
    kind = _select("Kind", _KINDS, default="partner",
                   hint="partner | clone; maps to role.type (default worker) + x_kind")
    summary = _text("One-line summary (optional)",
                    hint="one-line description (optional; currently dropped by the compiler — declarative)")
    schema_version = _text("schema_version", default="0.1.0",
                           hint="source-format version; becomes x_schema_version")

    _section("Soul — identity")
    role = _req_text("Role (one line)",
                     hint="one-line role; folded into role.description as 'Your role: …'")
    expertise = _list("Expertise area",
                      hint="areas of expertise (list); folded into role.description as 'Expertise: …'")
    temperament = _text("Temperament (optional)",
                        hint="one line; folded into role.description as 'Temperament: …'")
    standards = _list("Standard you hold to",
                      hint="standards you hold to (list); folded into role.description")
    refusals = _list("Refusal (you will not)",
                     hint="what it won't do (list); folded into role.description as 'You will not: …'")
    soul_body = _multiline("Voice / soul body (optional)",
                           hint="the voice paragraph; folded into role.description")
    rtype = _select("armature_role_type override",
                    ["(skip — default from kind)"] + _ROLE_TYPES,
                    default="(skip — default from kind)",
                    hint="overrides role.type (else mapped from kind, default worker)")
    armature_role_type = None if rtype.startswith("(skip") else rtype

    _section("Mandate — what it's for")
    goal = _text("Goal (optional)",
                 hint="what it's for; folded into role.description as 'Your mandate: …'")
    success_looks_like = _list("Success looks like",
                               hint="list; folded into role.description as 'Success looks like: …'")
    out_of_scope = _list("Out of scope",
                         hint="list; folded into role.description as 'Out of scope: …'")
    mandate_body = _multiline("Mandate body (optional)",
                              hint="optional 'why' paragraph; kept in the source (not compiled into the bundle)")

    brakes = None
    if _confirm("Add hard brakes/limits?",
                hint="hard limits & stop conditions; behavioral parts fold into role.description, hard parts emit an advisory safety fragment"):
        _section("Brakes")
        cost = _text("cost_ceiling_usd (optional)",
                     hint="hard cost cap; advisory contracts._cost_ceiling_usd in the safety fragment")
        maxit = _text("max_iterations (optional)",
                      hint="hard iteration cap; advisory contracts.max_iterations in the safety fragment")
        forbidden = _list("Forbidden action",
                          hint="actions it must not take (list); role.description prose AND block rules in the safety fragment")
        halt = _list("Halt-and-ask when",
                     hint="when to stop and hand back (list); folded into role.description")
        bbody = _multiline("Brakes body (optional)")
        brakes = {
            "cost_ceiling_usd": float(cost) if cost.strip() else None,
            "max_iterations": int(maxit) if maxit.strip() else None,
            "forbidden_actions": forbidden,
            "halt_and_ask_when": halt,
            "body": bbody,
        }

    trust = None
    if _confirm("Add response discipline (trust)?",
                hint="response discipline; behavioral parts fold into role.description"):
        _section("Trust")
        sw = _select("show_work", ["required", "on_request", "(none)"],
                     hint="required | on_request | none; folded into role.description ('show your reasoning…')")
        cs = _select("cite_sources", ["required", "(none)"],
                     hint="required | none; folded into role.description ('cite the evidence…')")
        un = _select("uncertainty", ["must_flag", "(none)"],
                     hint="must_flag | none; folded into role.description ('state your confidence…')")
        esc = _list("Escalate when",
                    hint="when to escalate (list); suggested_escalation_gates in the safety fragment")
        trust = {
            "show_work": None if sw == "(none)" else sw,
            "cite_sources": None if cs == "(none)" else cs,
            "uncertainty": None if un == "(none)" else un,
            "escalate_when": esc,
        }

    skills: list[dict] = []
    _section("Skills")
    while _confirm("Add a skill?", default=False):
        sid = _req_text("Skill id (e.g. appsec.rank-findings)",
                        hint="unique skill id; the skill_library key")
        sname = _text("Short name (optional, default from id)",
                      hint="short name; becomes the skill description (default = id)")
        when = _req_text("when (the trigger)",
                         hint="the trigger sentence; preserved as x_when (used by --when selection)")
        tools = _list("Tool (e.g. github:dependabot.list_alerts)",
                      hint="tools the skill uses (list); unioned into role.tools + x_tools")
        context = _list("Context ref (e.g. context/severity-rubric.md)",
                        hint="refs to context/*.md (list); resolved to x_context in the bundle")
        ct = _select("cost_tier", ["(skip)"] + _COST_TIERS,
                     hint="T1 | T2 | T3; preserved as x_cost_tier")
        version = _text("version", default="0.1.0",
                        hint="skill version; preserved as x_version")
        outputs = _text("outputs (optional, e.g. Finding[])",
                        hint="what the skill returns (e.g. Finding[]); preserved as x_outputs")
        body = _multiline("Skill body (the procedure)",
                         hint="the procedure; becomes skill_library[id].content")
        skills.append({
            "id": sid, "name": sname or None, "when": when, "tools": tools,
            "context": context, "cost_tier": None if ct == "(skip)" else ct,
            "version": version, "outputs": outputs or None, "body": body,
        })

    return {
        "id": aid, "name": name, "kind": kind, "summary": summary,
        "schema_version": schema_version,
        "role": role, "expertise": expertise, "temperament": temperament,
        "standards": standards, "refusals": refusals, "soul_body": soul_body,
        "armature_role_type": armature_role_type,
        "goal": goal, "success_looks_like": success_looks_like,
        "out_of_scope": out_of_scope, "mandate_body": mandate_body,
        "brakes": brakes, "trust": trust, "skills": skills,
    }
