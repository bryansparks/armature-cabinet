# Changelog

All notable changes to armature-cabinet are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added

---

## [0.2.0] - 2026-06-29

### Added

- **`forbidden_actions` are now enforced from the bundle.** `compile_agent` emits each `brakes.forbidden_actions` entry as a `safety_rules` block rule (`condition: null` = every call) on the `CompiledAgent` bundle. Requires `armature >= 0.5.0`, which merges a referenced agent's block rules into the workflow at load as a non-overridable floor (a workflow `allow` on a tool the agent forbids is dropped; the agent's block fires first). See armature 0.5.0 changelog.
- **`kind: clone` agents must declare `forbidden_actions`.** A clone that acts unattended with no hard brakes is now a hard error at `validate` **and** `build` (CabinetError, exit 1). Partner agents may omit brakes (they recommend only). **This is a behavioral change for any existing `kind: clone` folder without `forbidden_actions`.**

### Changed

- The advisory `<id>.safety.yaml` fragment no longer carries a `safety:` block — block rules now ride on the bundle. The fragment holds only advisory limits (`contracts.max_iterations`, `contracts._cost_ceiling_usd`) and `suggested_escalation_gates`, plus a `_note` explaining the split.
- Dependency floor raised to `armature-agents>=0.5.0` (was `>=0.3.5`).
- Bumped version to 0.2.0.

---

## [0.1.0] - 2026-06-23

### Added

- Initial release: pure compiler turning a cabinet agent folder (`cabinet.yaml`, `soul.md`, `mandate.md`, `brakes.md`, `trust.yaml`, `skills/`, `context/`) into an Armature `CompiledAgent` bundle plus an advisory safety fragment. CLI (`build`/`validate`/`new`/`list`/`team`), woodshop `--when` skill selection, and eight reference agents.