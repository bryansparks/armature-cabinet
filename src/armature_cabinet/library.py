"""Agent library management: enumerate + bulk-compile a directory of agents."""
from __future__ import annotations
from pathlib import Path

import yaml

from .loader import load_package
from .validate import validate_package
from .compiler import compile_agent, compile_safety_fragment

_YAML = dict(sort_keys=False, default_flow_style=False, width=100)


def _agent_dirs(library_dir):
    """Subdirectories of library_dir that contain cabinet.yaml, sorted by name."""
    root = Path(library_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a library directory: {root}")
    return [d for d in sorted(root.iterdir()) if d.is_dir() and (d / "cabinet.yaml").exists()]


def list_agents(library_dir) -> list[dict]:
    """Enumerate agents in library_dir; return [{id,name,kind,skills,valid,errors}] sorted by id.

    Never raises: load/validate failures are captured per-agent as valid=False + errors.
    """
    rows: list[dict] = []
    for d in _agent_dirs(library_dir):
        row = {"id": d.name, "name": d.name, "kind": "?", "skills": 0, "valid": False, "errors": []}
        try:
            pkg = load_package(d)
            r = validate_package(pkg)
            row.update({"name": pkg.name, "kind": pkg.kind, "skills": len(pkg.skills),
                        "valid": r.ok, "errors": list(r.errors)})
        except Exception as e:  # CabinetError or other load failure -> not fatal
            row["errors"] = [str(e)]
        rows.append(row)
    rows.sort(key=lambda r: r["id"])
    return rows


def build_all(library_dir, out_dir, no_safety=False) -> tuple[list[Path], list[str]]:
    """Compile every agent in library_dir to <out_dir>/<id>/.

    Returns (compiled bundle paths, per-agent error messages). Continues on
    per-agent failure (compiles as many as possible); does not abort on the first.
    """
    out = Path(out_dir)
    bundles: list[Path] = []
    errors: list[str] = []
    for d in _agent_dirs(library_dir):
        try:
            pkg = load_package(d)
            r = validate_package(pkg)
            if not r.ok:
                errors.append(f"{d.name}: " + "; ".join(r.errors))
                continue
            bundle = compile_agent(pkg)
            bdir = out / pkg.id
            bdir.mkdir(parents=True, exist_ok=True)
            (bdir / "agent.yaml").write_text(yaml.safe_dump(bundle, **_YAML), encoding="utf-8")
            if not no_safety:
                frag = compile_safety_fragment(pkg)
                if len(frag) > 1:
                    (bdir / f"{pkg.id}.safety.yaml").write_text(
                        yaml.safe_dump(frag, **_YAML), encoding="utf-8")
            bundles.append(bdir / "agent.yaml")
        except Exception as e:  # CabinetError or other failure -> report, keep going
            errors.append(f"{d.name}: {e}")
    return bundles, errors
