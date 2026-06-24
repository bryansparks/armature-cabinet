"""Apply a FileProposal to an agent folder. Frontmatter-aware: parses YAML
frontmatter, applies set/remove changes, applies section-anchored body edits,
re-serializes, then re-validates the whole folder via validate_package.

Rejects (PatchReject) when: target file missing, anchor not found, the patch
corrupts frontmatter, or the resulting folder fails validation (invariant #4).
On rejection the target file is left untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..loader import load_package, split_frontmatter
from ..validate import validate_package
from .types import FileProposal


class PatchReject(Exception):
    """The patch could not be applied cleanly or failed validation."""


def _apply_body(body: str, changes: list[dict]) -> str:
    for ch in changes:
        op = ch.get("op", "replace")
        anchor = ch.get("anchor", "")
        content = ch.get("content", "")
        idx = body.find(anchor)
        if idx == -1:
            raise PatchReject(f"anchor not found in body: {anchor!r}")
        if op == "replace":
            # replace from the anchor to the next blank-line-delimited section or EOF
            rest = body[idx + len(anchor):]
            nxt = re.search(r"\n#{2,} ", rest)
            end = idx + len(anchor) + (nxt.start() if nxt else len(rest))
            body = body[:idx] + content + body[end:]
        elif op == "insert":
            body = body[:idx] + content + "\n\n" + body[idx:]
        else:
            raise PatchReject(f"unknown body op: {op!r}")
    return body


def _apply_frontmatter(meta: dict, changes: dict) -> dict:
    for key, spec in changes.items():
        if not isinstance(spec, dict):
            raise PatchReject(
                f"frontmatter change for {key!r} must be {{'set': v}} or {{'remove': true}}"
            )
        if "remove" in spec:
            meta.pop(key, None)
        elif "set" in spec:
            meta[key] = spec["set"]
        else:
            raise PatchReject(f"frontmatter change for {key!r} missing set/remove")
    return meta


def apply_patch_to_folder(folder: Path, proposal: FileProposal) -> None:
    target = folder / proposal.target_file
    if not target.exists():
        raise PatchReject(f"target file missing: {proposal.target_file}")

    original = target.read_text(encoding="utf-8")
    meta, body = split_frontmatter(original, source=proposal.target_file)

    meta = _apply_frontmatter(meta, proposal.frontmatter_changes)
    body = _apply_body(body, proposal.body_changes)

    if meta:
        dumped = yaml.safe_dump(
            meta, sort_keys=False, default_flow_style=False, width=100
        ).strip()
        new_text = f"---\n{dumped}\n---\n\n{body}"
    else:
        new_text = body

    # Write the candidate, then re-validate the whole folder (invariant #4).
    # If validation fails we roll back so the folder is never left invalid.
    target.write_text(new_text, encoding="utf-8")
    pkg = load_package(folder)
    r = validate_package(pkg)
    if not r.ok:
        # Roll back to original — reject without leaving a corrupted folder.
        target.write_text(original, encoding="utf-8")
        raise PatchReject(f"folder failed validation after patch: {r.errors}")
