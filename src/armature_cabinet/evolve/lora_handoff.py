"""Decide whether a skill needs LoRA weights (vs a prose edit), then shell out to
`armature adapter create`. Mirrors team.run_workflow's subprocess pattern.

Cabinet never imports armature; only shells out (one-directional boundary).
Cabinet never writes the workflow's `adapter:` binding — it only recommends
training. Armature trains + binds; the orchestrator decides fallback.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from ..errors import CabinetError
from .types import AgentTraceSummary


@dataclass
class LoraRecommendation:
    eligible: bool
    skill_id: str | None
    rationale: str


@dataclass
class HandoffResult:
    """Outcome of a handoff. The orchestrator inspects ``trained`` to decide
    whether to fall back to the prose route and log missed_predictions."""

    skill_id: str
    command: list[str]
    dry_run: bool
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def trained(self) -> bool:
        """True only when a real invocation returned exit code 0."""
        return (not self.dry_run) and self.returncode == 0


def decide_lora(
    summary: AgentTraceSummary,
    *,
    prose_cycles_without_gain: int,
    skill_id: str | None,
) -> LoraRecommendation:
    """Eligible when prose edits are exhausted (>=2 cycles w/o HQS gain) AND the
    skill's tools are being called correctly (fired) — a tacit pattern a text
    edit cannot fix. Returns the recommendation; does not perform the handoff.
    """
    stats = summary.per_skill.get(skill_id) if skill_id else None
    if stats is None:
        return LoraRecommendation(False, skill_id, "skill not in trace")
    # Eligible when prose is exhausted AND tools fired (right tools, wrong output).
    tools_right = stats.fired
    if prose_cycles_without_gain >= 2 and tools_right:
        return LoraRecommendation(
            True,
            skill_id,
            "prose edits exhausted; tools called correctly but outputs wrong",
        )
    return LoraRecommendation(False, skill_id, "prose route still viable or tools misfiring")


def build_adapter_command(
    *,
    skill_id: str,
    role_type: str,
    min_score: float = 0.7,
    continual_learning: bool = True,
) -> list[str]:
    """Pure: assemble the `armature adapter create` argv. Never executes."""
    cmd = [
        "armature",
        "adapter",
        "create",
        skill_id,
        "--from-traces",
        "--role-type",
        role_type,
        "--min-score",
        str(min_score),
    ]
    if continual_learning:
        cmd.append("--continual-learning")
    return cmd


def handoff_to_adapter(
    *,
    skill_id: str,
    role_type: str,
    min_score: float = 0.7,
    continual_learning: bool = True,
    dry_run: bool = False,
) -> HandoffResult:
    """Shell out to `armature adapter create` to train a LoRA adapter.

    Mirrors team.run_workflow: ``shutil.which("armature")`` guard raises
    CabinetError if the CLI is missing, then ``subprocess.run`` is invoked.
    Enhanced with ``capture_output=True, text=True, check=False`` so the
    orchestrator can inspect stdout/stderr and decide fallback.

    With ``dry_run=True`` the command is built and returned but never executed
    — use this in tests and in a "propose only" mode.
    """
    if shutil.which("armature") is None:
        raise CabinetError(
            "armature CLI not found; install armature-agents to train an adapter"
        )
    cmd = build_adapter_command(
        skill_id=skill_id,
        role_type=role_type,
        min_score=min_score,
        continual_learning=continual_learning,
    )
    if dry_run:
        return HandoffResult(skill_id=skill_id, command=cmd, dry_run=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return HandoffResult(
        skill_id=skill_id,
        command=cmd,
        dry_run=False,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
