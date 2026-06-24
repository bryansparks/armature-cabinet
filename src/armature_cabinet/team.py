"""Team workflow generation + armature run handoff."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

from .errors import CabinetError

_MODEL_TIERS = {"small": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}}


def generate_workflow(agent_ids: list[str], bundles_dir: Path, name: str) -> dict:
    """Pure: build an Armature workflow spec dict from an ordered agent id list.

    Agents form a sequential pipeline (stage[i].depends_on = [stage[i-1].id]).
    Bundle paths are absolute so armature resolves them regardless of the wf location.
    """
    bdir = Path(bundles_dir).resolve()
    agent_library = {aid: {"path": str(bdir / aid / "agent.yaml")} for aid in agent_ids}
    stages = []
    for i, aid in enumerate(agent_ids):
        stages.append({
            "id": aid,
            "agent": aid,
            "output_mode": "text",
            "depends_on": [agent_ids[i - 1]] if i > 0 else [],
        })
    return {
        "name": name,
        "version": "1.0",
        "model_tiers": _MODEL_TIERS,
        "role_type_defaults": {rt: "small" for rt in ("worker", "orchestrator", "judge", "researcher")},
        "agent_library": agent_library,
        "stages": stages,
    }


def run_workflow(wf_path: Path, dry_run: bool) -> int:
    """Shell out to `armature run [--dry-run] <wf>`. Returns the runner exit code.

    Raises CabinetError if the armature CLI is not on PATH. Does not import
    armature's runner — only shells out (one-directional boundary preserved).
    """
    if shutil.which("armature") is None:
        raise CabinetError("armature CLI not found; install armature-agents to run a team")
    cmd = ["armature", "run"]
    if dry_run:
        cmd.append("--dry-run")
    cmd.append(str(wf_path))
    return subprocess.run(cmd).returncode
