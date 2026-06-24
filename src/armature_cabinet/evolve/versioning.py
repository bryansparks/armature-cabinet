# src/armature_cabinet/evolve/versioning.py
"""Versioned agent folders with HQS-gated promotion. Re-implements the tiny
promotion-policy abstraction LOCALLY (the one-directional boundary forbids importing
armature.adapters.policy). Structurally identical to Armature's policy.py but operates
on Cabinet AgentVersion / HQS, not AdapterMetadata.
"""
from __future__ import annotations
import json
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from .types import AgentVersion


class PromotionPolicy(ABC):
    @abstractmethod
    def should_promote(self, new_hqs: float, current_hqs: float | None) -> bool: ...


@dataclass
class ThresholdPromotionPolicy(PromotionPolicy):
    min_gain: float = 0.02

    def should_promote(self, new_hqs: float, current_hqs: float | None) -> bool:
        if current_hqs is None:
            return True
        return (new_hqs - current_hqs) >= self.min_gain


def _versions_dir(folder: Path) -> Path:
    return folder / "versions"


def _latest_file(folder: Path) -> Path:
    return _versions_dir(folder) / "latest.txt"


def write_version(folder: Path, *, version: str, hqs: float | None,
                  predicted_fixes: list[str] | None = None) -> AgentVersion:
    vdir = _versions_dir(folder) / version
    vdir.mkdir(parents=True, exist_ok=True)
    for p in folder.iterdir():
        if p.name == "versions":
            continue
        dest = vdir / p.name
        if p.is_dir():
            shutil.copytree(p, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(p, dest)
    av = AgentVersion(version=version, hqs=hqs, predicted_fixes=list(predicted_fixes or []))
    (vdir / ".proposal.json").write_text(json.dumps({
        "version": version, "hqs": hqs, "predicted_fixes": av.predicted_fixes,
    }), encoding="utf-8")
    return av


def read_latest(folder: Path) -> str | None:
    lf = _latest_file(folder)
    if lf.exists():
        return lf.read_text(encoding="utf-8").strip() or None
    return None


def promote(folder: Path, version: str, *, policy: PromotionPolicy,
            current_hqs: float | None, new_hqs: float, force: bool = False) -> bool:
    if force or policy.should_promote(new_hqs, current_hqs):
        _latest_file(folder).parent.mkdir(parents=True, exist_ok=True)
        _latest_file(folder).write_text(version, encoding="utf-8")
        return True
    return False


def rollback(folder: Path, version: str) -> None:
    vdir = _versions_dir(folder) / version
    if not vdir.exists():
        raise FileNotFoundError(f"version not found: {version}")
    for p in list(folder.iterdir()):
        if p.name == "versions":
            continue
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    for p in vdir.iterdir():
        if p.name == ".proposal.json":
            continue
        dest = folder / p.name
        if p.is_dir():
            shutil.copytree(p, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(p, dest)
    _latest_file(folder).write_text(version, encoding="utf-8")
