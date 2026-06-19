"""Scaffold a cabinet agent folder from an answers dict (pure: no prompting)."""
from __future__ import annotations
import re
from pathlib import Path

import yaml

_FM_SEP = "---\n"


def slugify(name: str) -> str:
    """Make a safe filename from a skill name/id segment."""
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-_.")
    return s or "skill"


def _yaml_block(meta: dict) -> str:
    return _FM_SEP + yaml.safe_dump(meta, sort_keys=False, default_flow_style=False,
                                    width=100).strip() + "\n---\n"


def _listify(items) -> list[str]:
    return [str(i) for i in (items or []) if i]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def build_folder(answers: dict, out_dir: Path) -> Path:
    """Write a complete cabinet agent folder from an answers dict. Pure (only writes files).

    Raises ``FileExistsError`` if the target folder already exists.
    """
    root = Path(out_dir) / answers["id"]
    if root.exists():
        raise FileExistsError(f"agent folder already exists: {root}")

    # cabinet.yaml
    cabinet = {
        "schema_version": answers.get("schema_version") or "0.1.0",
        "id": answers["id"],
        "name": answers.get("name") or answers["id"],
        "kind": answers.get("kind") or "partner",
    }
    if answers.get("summary"):
        cabinet["summary"] = answers["summary"]
    blocks = {"soul": "soul.md"}
    has_mandate = any([answers.get("goal"), answers.get("success_looks_like"),
                       answers.get("out_of_scope"), answers.get("mandate_body")])
    if has_mandate:
        blocks["mandate"] = "mandate.md"
    cabinet["blocks"] = blocks
    # A confirmed-but-empty block is treated as absent so we don't write a
    # degenerate file (and so cabinet.yaml doesn't reference a missing file).
    bk = answers.get("brakes")
    has_brakes = bk is not None and any([
        bk.get("cost_ceiling_usd") is not None,
        bk.get("max_iterations") is not None,
        _listify(bk.get("forbidden_actions")),
        _listify(bk.get("halt_and_ask_when")),
        (bk.get("body") or "").strip(),
    ])
    tr = answers.get("trust")
    has_trust = tr is not None and any([
        tr.get("show_work"),
        tr.get("cite_sources"),
        tr.get("uncertainty"),
        _listify(tr.get("escalate_when")),
    ])
    blocks_extra: dict = {}
    if has_brakes:
        blocks_extra["brakes"] = "brakes.md"
    if has_trust:
        blocks_extra["trust"] = "trust.yaml"
    if answers.get("skills"):
        blocks_extra["skills"] = "skills/"
        blocks_extra["context"] = "context/"
    if blocks_extra:
        cabinet["blocks_extra"] = blocks_extra
    _write(root / "cabinet.yaml", yaml.safe_dump(cabinet, sort_keys=False,
            default_flow_style=False, width=100))

    # soul.md
    soul_meta = {"type": answers.get("kind") or "partner", "role": answers["role"]}
    if answers.get("expertise"):
        soul_meta["expertise"] = _listify(answers["expertise"])
    if answers.get("temperament"):
        soul_meta["temperament"] = answers["temperament"]
    if answers.get("standards"):
        soul_meta["standards"] = _listify(answers["standards"])
    if answers.get("refusals"):
        soul_meta["refusals"] = _listify(answers["refusals"])
    if answers.get("armature_role_type"):
        soul_meta["armature_role_type"] = answers["armature_role_type"]
    soul = _yaml_block(soul_meta)
    if answers.get("soul_body"):
        soul += answers["soul_body"].strip() + "\n"
    _write(root / "soul.md", soul)

    # mandate.md (only if any mandate field is non-empty)
    if has_mandate:
        man_meta: dict = {}
        if answers.get("goal"):
            man_meta["goal"] = answers["goal"]
        if answers.get("success_looks_like"):
            man_meta["success_looks_like"] = _listify(answers["success_looks_like"])
        if answers.get("out_of_scope"):
            man_meta["out_of_scope"] = _listify(answers["out_of_scope"])
        mandate = _yaml_block(man_meta)
        if answers.get("mandate_body"):
            mandate += answers["mandate_body"].strip() + "\n"
        _write(root / "mandate.md", mandate)

    # brakes.md (only if the block was provided AND non-empty)
    if has_brakes:
        bk_meta: dict = {}
        if bk.get("cost_ceiling_usd") is not None:
            bk_meta["cost_ceiling_usd"] = bk["cost_ceiling_usd"]
        if bk.get("max_iterations") is not None:
            bk_meta["max_iterations"] = bk["max_iterations"]
        if bk.get("forbidden_actions"):
            bk_meta["forbidden_actions"] = _listify(bk["forbidden_actions"])
        if bk.get("halt_and_ask_when"):
            bk_meta["halt_and_ask_when"] = _listify(bk["halt_and_ask_when"])
        brakes = _yaml_block(bk_meta)
        if bk.get("body"):
            brakes += bk["body"].strip() + "\n"
        _write(root / "brakes.md", brakes)

    # trust.yaml (only if the block was provided AND non-empty)
    if has_trust:
        trust: dict = {}
        if tr.get("show_work"):
            trust["show_work"] = tr["show_work"]
        if tr.get("cite_sources"):
            trust["cite_sources"] = tr["cite_sources"]
        if tr.get("uncertainty"):
            trust["uncertainty"] = tr["uncertainty"]
        if tr.get("escalate_when"):
            trust["escalate_when"] = _listify(tr["escalate_when"])
        _write(root / "trust.yaml", yaml.safe_dump(trust, sort_keys=False,
                default_flow_style=False, width=100))

    # skills/*.md + collect context refs
    context_refs: set[str] = set()
    for sk in answers.get("skills") or []:
        sid = sk["id"]
        name = sk.get("name") or sid.rsplit(".", 1)[-1]
        slug = slugify(name)
        sk_meta: dict = {"id": sid, "version": sk.get("version") or "0.1.0"}
        if sk.get("name"):
            sk_meta["name"] = sk["name"]
        if sk.get("when"):
            sk_meta["when"] = sk["when"]
        if sk.get("tools"):
            sk_meta["tools"] = _listify(sk["tools"])
        if sk.get("context"):
            sk_meta["context"] = _listify(sk["context"])
            context_refs.update(_listify(sk["context"]))
        if sk.get("cost_tier"):
            sk_meta["cost_tier"] = sk["cost_tier"]
        if sk.get("outputs"):
            sk_meta["outputs"] = sk["outputs"]
        body = (sk.get("body") or "").strip()
        _write(root / "skills" / f"{slug}.md", _yaml_block(sk_meta) + (body + "\n" if body else ""))

    # context/*.md stubs for each referenced ref
    for ref in sorted(context_refs):
        cpath = root / ref
        if not cpath.exists():
            _write(cpath, f"# {cpath.stem}\n\n<!-- TODO: fill in the reference material "
                          f"referenced by a skill. -->\n")

    # README.md
    readme = f"# {cabinet['name']}\n"
    if answers.get("summary"):
        readme += f"\n{answers['summary']}\n"
    _write(root / "README.md", readme)

    return root
