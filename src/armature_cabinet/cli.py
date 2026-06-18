"""`armature-cabinet build|validate <folder>` — compile / check a cabinet agent."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import yaml

from .errors import CabinetError
from .loader import load_package
from .compiler import compile_agent, compile_safety_fragment
from .validate import validate_package
from .select import select_skills


def _dump(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False, width=100)


def _report(r) -> None:
    for w in r.warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in r.errors:
        print(f"error: {e}", file=sys.stderr)


def cmd_build(args: argparse.Namespace) -> int:
    if args.when is not None and args.skill:
        print("error: --when and --skill are mutually exclusive (pick one selection mode)",
              file=sys.stderr)
        return 1
    pkg = load_package(args.folder)
    if args.when is not None:
        include = select_skills(pkg, args.when)
        if not include:
            print(f'warning: no skills matched task: "{args.when}"; building with 0 skills',
                  file=sys.stderr)
    else:
        include = args.skill or None

    r = validate_package(pkg, include)
    _report(r)
    if not r.ok:
        return 1

    bundle = compile_agent(pkg, include=include)
    out_dir = Path(args.out) if args.out else Path("dist") / pkg.id
    bundle_path = out_dir / "agent.yaml"
    _dump(bundle, bundle_path)

    msg = [f"compiled '{pkg.id}' ({pkg.kind})", f"  bundle  -> {bundle_path}"]
    msg.append(f"  role    -> {len(bundle['role']['skills'])} skill(s), "
               f"{len(bundle['role']['tools'])} tool(s)")

    if not args.no_safety:
        fragment = compile_safety_fragment(pkg)
        if len(fragment) > 1:  # more than just the _note
            frag_path = out_dir / f"{pkg.id}.safety.yaml"
            _dump(fragment, frag_path)
            msg.append(f"  safety  -> {frag_path}  (advisory; merge into your workflow)")

    print("\n".join(msg))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    if args.when is not None and args.skill:
        print("error: --when and --skill are mutually exclusive (pick one selection mode)",
              file=sys.stderr)
        return 1
    pkg = load_package(args.folder)
    if args.when is not None:
        include = select_skills(pkg, args.when)
        if include:
            print(f"matched {len(include)} skill(s): {', '.join(include)}")
        else:
            print(f'warning: no skills matched task: "{args.when}"', file=sys.stderr)
    else:
        include = args.skill or None

    r = validate_package(pkg, include)
    compile_agent(pkg, include=include)
    _report(r)
    if r.ok:
        print(f"ok: {pkg.id} ({pkg.kind})")
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="armature-cabinet")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="compile a cabinet agent folder into an Armature bundle")
    b.add_argument("folder", help="path to the cabinet agent folder (containing cabinet.yaml)")
    b.add_argument("-o", "--out", help="output directory (default: dist/<id>/)")
    b.add_argument("--skill", action="append",
                   help="attach only this skill id (repeatable); default attaches all")
    b.add_argument("--when", help="attach skills whose 'when' overlaps this task string")
    b.add_argument("--no-safety", action="store_true", help="skip the advisory safety fragment")
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("validate",
                       help="load + validate + compile in memory; writes no files")
    v.add_argument("folder", help="path to the cabinet agent folder")
    v.add_argument("--skill", action="append",
                   help="check only this skill id (repeatable); default checks all")
    v.add_argument("--when", help="preview skills whose 'when' overlaps this task string")
    v.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CabinetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
