"""Validate a loaded AgentPackage: logical rules returned as errors + warnings.

Structural problems (missing folder/cabinet.yaml, malformed YAML) are raised as
``CabinetError`` by the loader. The rules here are logical authoring mistakes
that produce a degraded bundle if ignored; they are *returned*, not raised, so
the CLI can print them all at once.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .model import AgentPackage

_VALID_KINDS = {"partner", "clone"}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_package(pkg: AgentPackage, include: list[str] | None = None) -> ValidationResult:
    r = ValidationResult()
    man = pkg.manifest

    id_val = man.get("id")
    if id_val is None:
        r.errors.append("cabinet.yaml: missing required 'id'")
    elif not isinstance(id_val, str) or not id_val:
        r.errors.append("cabinet.yaml: 'id' must be a non-empty string")
    if not man.get("name"):
        r.warnings.append("cabinet.yaml: missing 'name' (defaulting to id)")
    kind = man.get("kind")
    if kind is None:
        r.warnings.append("cabinet.yaml: missing 'kind' (defaulting to 'partner')")
    elif kind not in _VALID_KINDS:
        r.errors.append(
            f"cabinet.yaml: invalid kind {kind!r} (expected one of {sorted(_VALID_KINDS)})"
        )
    if not man.get("schema_version"):
        r.warnings.append("cabinet.yaml: missing 'schema_version'")

    seen: set[str] = set()
    for s in pkg.skills:
        if not s.id:
            r.errors.append("skill: missing 'id'")
        elif s.id in seen:
            r.errors.append(f"duplicate skill id {s.id!r}")
        else:
            seen.add(s.id)
        for ref in s.context:
            if ref not in pkg.context:
                r.errors.append(f"skill {s.id!r}: context ref {ref!r} not found")

    if include:
        have = {s.id for s in pkg.skills}
        for want in include:
            if want not in have:
                r.errors.append(f"--skill {want!r}: not present in package")

    return r
