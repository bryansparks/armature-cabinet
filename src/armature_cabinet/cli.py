"""`armature-cabinet build <folder>` — compile a cabinet agent into an Armature bundle."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import yaml

from .loader import load_package
from .compiler import compile_agent, compile_safety_fragment


def _dump(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False, width=100)


def cmd_build(args: argparse.Namespace) -> int:
    pkg = load_package(args.folder)
    include = args.skill or None

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="armature-cabinet")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="compile a cabinet agent folder into an Armature bundle")
    b.add_argument("folder", help="path to the cabinet agent folder (containing cabinet.yaml)")
    b.add_argument("-o", "--out", help="output directory (default: dist/<id>/)")
    b.add_argument("--skill", action="append",
                   help="attach only this skill id (repeatable); default attaches all")
    b.add_argument("--no-safety", action="store_true", help="skip the advisory safety fragment")
    b.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
