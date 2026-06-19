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


def _text(msg: str, default: str = "") -> str:
    return questionary.text(msg + ": ", default=default).ask() or ""


def _req_text(msg: str, default: str = "") -> str:
    while True:
        v = questionary.text(msg + ": ", default=default).ask()
        if v and v.strip():
            return v.strip()
        console.print("[red]Required — please enter a value.[/red]")


def _list(msg: str) -> list[str]:
    out: list[str] = []
    while True:
        v = questionary.text(f"{msg} (blank to finish): ").ask()
        if not v or not v.strip():
            break
        out.append(v.strip())
    return out


def _multiline(msg: str) -> str:
    console.print(f"{msg} (enter lines; blank line to finish):")
    lines: list[str] = []
    while True:
        v = input("... ")
        if not v.strip():
            break
        lines.append(v)
    return "\n".join(lines)


def _select(msg: str, choices: list[str], default: str | None = None) -> str:
    return questionary.select(msg, choices=choices, default=default).ask()


def _confirm(msg: str, default: bool = False) -> bool:
    return bool(questionary.confirm(msg, default=default).ask())


def collect_answers(id_: str | None = None) -> dict:
    """Walk the author through every cabinet field; return the answers dict."""
    _section("Identity")
    aid = id_ or _req_text("Agent id (folder name)")
    name = _text("Display name", default=aid)
    kind = _select("Kind", _KINDS, default="partner")
    summary = _text("One-line summary (optional)")
    schema_version = _text("schema_version", default="0.1.0")

    _section("Soul — identity")
    role = _req_text("Role (one line)")
    expertise = _list("Expertise area")
    temperament = _text("Temperament (optional)")
    standards = _list("Standard you hold to")
    refusals = _list("Refusal (you will not)")
    soul_body = _multiline("Voice / soul body (optional)")
    rtype = _select("armature_role_type override",
                    ["(skip — default from kind)"] + _ROLE_TYPES,
                    default="(skip — default from kind)")
    armature_role_type = None if rtype.startswith("(skip") else rtype

    _section("Mandate — what it's for")
    goal = _text("Goal (optional)")
    success_looks_like = _list("Success looks like")
    out_of_scope = _list("Out of scope")
    mandate_body = _multiline("Mandate body (optional)")

    brakes = None
    if _confirm("Add hard brakes/limits?"):
        _section("Brakes")
        cost = _text("cost_ceiling_usd (optional)")
        maxit = _text("max_iterations (optional)")
        forbidden = _list("Forbidden action")
        halt = _list("Halt-and-ask when")
        bbody = _multiline("Brakes body (optional)")
        brakes = {
            "cost_ceiling_usd": float(cost) if cost.strip() else None,
            "max_iterations": int(maxit) if maxit.strip() else None,
            "forbidden_actions": forbidden,
            "halt_and_ask_when": halt,
            "body": bbody,
        }

    trust = None
    if _confirm("Add response discipline (trust)?"):
        _section("Trust")
        sw = _select("show_work", ["required", "on_request", "(none)"])
        cs = _select("cite_sources", ["required", "(none)"])
        un = _select("uncertainty", ["must_flag", "(none)"])
        esc = _list("Escalate when")
        trust = {
            "show_work": None if sw == "(none)" else sw,
            "cite_sources": None if cs == "(none)" else cs,
            "uncertainty": None if un == "(none)" else un,
            "escalate_when": esc,
        }

    skills: list[dict] = []
    _section("Skills")
    while _confirm("Add a skill?", default=False):
        sid = _req_text("Skill id (e.g. appsec.rank-findings)")
        sname = _text("Short name (optional, default from id)")
        when = _req_text("when (the trigger)")
        tools = _list("Tool (e.g. github:dependabot.list_alerts)")
        context = _list("Context ref (e.g. context/severity-rubric.md)")
        ct = _select("cost_tier", ["(skip)"] + _COST_TIERS)
        version = _text("version", default="0.1.0")
        outputs = _text("outputs (optional, e.g. Finding[])")
        body = _multiline("Skill body (the procedure)")
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
