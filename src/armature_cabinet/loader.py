"""Read a cabinet agent folder from disk into an AgentPackage."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

import yaml

from .model import AgentPackage, Skill

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)

# fields consumed explicitly off a skill's frontmatter; the rest fall into extra
_SKILL_KNOWN = {"id", "name", "when", "tools", "context", "cost_tier", "version"}


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body) for a markdown file with YAML frontmatter."""
    m = _FM.match(text)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        return meta, m.group(2).strip()
    return {}, text.strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_skill(path: Path) -> Skill:
    meta, body = split_frontmatter(_read(path))
    sid = meta.get("id") or meta.get("name") or path.stem
    extra = {k: v for k, v in meta.items() if k not in _SKILL_KNOWN}
    return Skill(
        id=sid,
        body=body,
        name=meta.get("name"),
        when=meta.get("when"),
        tools=list(meta.get("tools") or []),
        context=list(meta.get("context") or []),
        cost_tier=meta.get("cost_tier"),
        version=meta.get("version"),
        extra=extra,
    )


def load_package(folder: str | Path) -> AgentPackage:
    root = Path(folder)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a cabinet agent folder: {root}")

    manifest_path = root / "cabinet.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing cabinet.yaml manifest in {root}")
    manifest = yaml.safe_load(_read(manifest_path)) or {}

    soul_meta, soul_body = ({}, "")
    if (root / "soul.md").exists():
        soul_meta, soul_body = split_frontmatter(_read(root / "soul.md"))

    mandate_meta, mandate_body = ({}, "")
    if (root / "mandate.md").exists():
        mandate_meta, mandate_body = split_frontmatter(_read(root / "mandate.md"))

    brakes: dict[str, Any] = {}
    if (root / "brakes.md").exists():
        brakes, _ = split_frontmatter(_read(root / "brakes.md"))

    trust: dict[str, Any] = {}
    if (root / "trust.yaml").exists():
        trust = yaml.safe_load(_read(root / "trust.yaml")) or {}

    skills: list[Skill] = []
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for sp in sorted(skills_dir.glob("*.md")):
            skills.append(_load_skill(sp))

    context: dict[str, str] = {}
    context_dir = root / "context"
    if context_dir.is_dir():
        for cp in sorted(context_dir.glob("*.md")):
            context[cp.name] = _read(cp).strip()

    return AgentPackage(
        manifest=manifest,
        soul_meta=soul_meta,
        soul_body=soul_body,
        mandate_meta=mandate_meta,
        mandate_body=mandate_body,
        skills=skills,
        brakes=brakes,
        trust=trust,
        context=context,
    )
