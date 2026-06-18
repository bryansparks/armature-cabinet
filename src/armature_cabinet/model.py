"""In-memory model of a cabinet agent package (the source folder).

A cabinet agent is a folder of files:

    my-agent/
      cabinet.yaml      # manifest (id, name, kind, summary, ...)
      soul.md           # always-on identity (frontmatter + prose)
      mandate.md        # what it's for
      brakes.md         # optional — hard limits & stop conditions
      trust.yaml        # optional — how it proves its work
      skills/*.md       # procedures (frontmatter + body)
      context/*.md      # reference material

These are *source*. The compiler turns them into an Armature CompiledAgent
bundle ({role, skill_library}) plus an advisory safety fragment.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Skill:
    id: str
    body: str
    name: str | None = None
    when: str | None = None
    tools: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)
    cost_tier: str | None = None
    version: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPackage:
    manifest: dict[str, Any]          # contents of cabinet.yaml
    soul_meta: dict[str, Any]
    soul_body: str
    mandate_meta: dict[str, Any]
    mandate_body: str
    skills: list[Skill]
    brakes: dict[str, Any] = field(default_factory=dict)
    trust: dict[str, Any] = field(default_factory=dict)
    context: dict[str, str] = field(default_factory=dict)  # filename -> body

    @property
    def id(self) -> str:
        return self.manifest.get("id", "unnamed-agent")

    @property
    def name(self) -> str:
        return self.manifest.get("name", self.id)

    @property
    def kind(self) -> str:
        return self.manifest.get("kind", "partner")
