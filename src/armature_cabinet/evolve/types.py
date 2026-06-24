from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillStats:
    skill_id: str
    fail_count: int = 0
    escalation: int = 0
    output_valid_rate: float = 1.0
    tools_declared: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)

    @property
    def fired(self) -> bool:
        """A skill 'fired' if any of its declared tools were called."""
        if not self.tools_declared:
            return True  # skill with no tools: treat as active when the stage ran
        return bool(set(self.tools_declared) & set(self.tools_called))


@dataclass
class AgentTraceSummary:
    agent_id: str
    agent_version: str | None
    n_traces: int
    output_valid_rate: float
    success_rate: float
    quorum: float
    escalation_rate: float
    hqs: float
    per_skill: dict[str, SkillStats] = field(default_factory=dict)
    dominant_symptoms: list[tuple[str, int]] = field(default_factory=list)  # (CausalStatus-like str, count)
    healthy_skills: list[str] = field(default_factory=list)
    evidence_row_ids: list[int] = field(default_factory=list)
    heuristic: bool = False  # True when attribution fields were absent (pre-enrichment traces)


@dataclass
class RoutingDecision:
    target_file: str | None          # relative to agent folder root, e.g. "skills/draft-reply.md"
    surface: str                     # skills | mandate | skills+soul | guardrail | lora_eligible | none
    gate: str                        # auto | review | none
    rationale: str
    rule_id: str                     # R1..G2.. or "unmodeled"
    symptom: str
    skill_id: str | None = None
    heuristic: bool = False


@dataclass
class FileProposal:
    target_file: str
    surface: str
    gate: str
    rationale: str
    frontmatter_changes: dict[str, Any] = field(default_factory=dict)  # {key: {"set": v} | {"remove": True}}
    body_changes: list[dict[str, Any]] = field(default_factory=list)   # [{op, anchor, content}]
    predicted_fixes: list[str] = field(default_factory=list)
    predicted_regressions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[int] = field(default_factory=list)
    rule_id: str = ""
    skill_id: str | None = None


@dataclass
class AgentVersion:
    """A versioned snapshot of an agent folder used by promotion policies."""
    version: str
    hqs: float | None = None
    predicted_fixes: list[str] = field(default_factory=list)
    created_at: str = ""