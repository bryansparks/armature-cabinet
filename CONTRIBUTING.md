# Contributing to armature-cabinet

Thanks for considering a contribution. This is a small, early project — keep PRs
focused and readable.

## Setup

```bash
pip install -e ".[dev]"
pytest                 # 76 tests
ruff check src tests    # clean
```

CI runs the same lint + test + wheel build on every push and PR.

## What's welcome

- **Bug fixes and clean error messages.** The compiler raises `CabinetError`
  with a plain message — never a traceback for bad input. Keep that invariant.
- **New reference agents** under `agents/` that exercise the format in a new
  domain. Copy the structure of an existing one (e.g. `agents/gmail-reader`)
  and validate it: `armature-cabinet validate agents/<id>`.
- **Doc improvements.** Docs are deliberately *dual-audience* — human-readable
  prose **and** AI-ingestible structured reference (explicit field schemas, the
  validation rules stated outright, complete copyable examples). Keep both
  audiences in mind when editing.

## Invariants to preserve

- **Compiler purity** — `loader` / `compiler` / `validate` / `select` are pure:
  folder in → `AgentPackage` / dict / `ValidationResult` / ids out. No I/O,
  network, or LLM inside the compile core. Only the CLI writes files; the `new`
  wizard and the `team` run-handoff are separate surfaces.
- **One-directional boundary** — cabinet compiles; Armature runs. Don't edit
  Armature core from here; don't parse the folder format in core.
- **Soft/hard guardrail split** — behavioral intent (refusals, halt-and-ask,
  show-work, cite, flag-uncertainty) folds into role prose so the agent
  self-governs; hard enforcement (forbidden actions, contract limits, gates)
  goes in the advisory `*.safety.yaml` fragment the workflow merges. Never
  smuggle hard enforcement into the bundle — `{ role, skill_library }` can't
  carry it.
- **`x_` metadata only** on `Role` / `SkillDef` (both `extra="allow"`); no
  invented fields elsewhere.
- **`cabinet.yaml` = source; `agent.yaml` = output.** Don't confuse them.

See `docs/armature-cabinet.md` §11 for the full principles list.

## Commit style

Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, …). Keep history
readable; one logical change per commit.