# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each skill/tool is versioned independently below.

---

## supervaize_access

### [Unreleased]

_No changes yet._

### [1.0.0] - 2026-03-12

#### Added

- Skill and Typer CLI helper (`supervaize_access_helper.py`) for interacting with Supervaize workspaces via REST API, MCP endpoint, and optional Supervaizer controller. Includes `SKILL.md` and `reference.md` for REST paths and MCP tool args.

#### Changed

- `SKILL.md` and `reference.md` updated (REST/MCP/controller backends, env vars, helper commands).

---

## supervaizer_integration

### [Unreleased]

_No changes yet._

### [2.1.0] - 2026-11-05

Updated for Supervaizer SDK 1.1 to 1.9.

#### Added

- `SKILL.md`: runtime rules (action metadata, top-level `job_state`, job cost, idempotency, verified workspace context, mission context), a table of optional capabilities with the SDK release of each (human in the loop, file fields, workspace binding, agent actions, `context.assign`, job setup policy, labels, rule checkpoints, scheduled start, introduction, full description, guided setup, billable consumption), a Job Configurator section, and a Studio connection step with the workspace authorization variables.
- `SKILL.md`: a component-by-need table and a life-of-the-job plan for the Job Configurator (checked against the Aidan interviewer agent), and an Analytics Dashboards section for `job.analytics` and `mission.analytics`.
- Scaffold: `job.stop` action, an in-memory job store so `job.sync` and a retried `job.start` return the original `job_state`, and `integration.scheduled_start` in the spec.
- Scaffold: local mode. With `SUPERVAIZER_LOCAL_MODE=true` the generated controller starts without a Studio account.

#### Changed

- Reference links point to the public SDK docs instead of local paths.
- Scaffold registration uses the short `build_v2_agent_registration` form (no `agent_id`, `controller_url` or `agent_card_url`).

#### Fixed

- The generated controller failed to import on SDK 1.9: artifact types are keyed by `type`, and `capabilities.actions` holds `V2ActionDefinition` objects, so handlers are registered with `action.id`. A spec that still uses `id` for an artifact type is converted.
- `load-surface` and `invoke-action` sent `actor.id`; the contract requires `actor.user_id`.

### [2.0.0] - 2026-05-17

#### Changed

- Skill and scaffold retargeted to Supervaizer v2 (A2A JSON-RPC, A2UI surfaces, Jobs, Cases, Steps, Resources, Actions, `job.sync`).

### [1.0.0] - 2026-03-12

#### Added

- Skill and CLI helper for integrating Python agents with the Supervaizer controller (5-phase workflow: discovery → spec → scaffold → customize). Generates `supervaizer_control.py`, workflow adapters, and optional `steps.py`.

#### Changed

- Documentation (`SKILL.md`, `README.md`, `CLAUDE.md`) revised for 5-phase workflow, file naming, and generated artifacts.
- CLI helper refactored for improved structure and user guidance.

---

## Repo

### [Unreleased]

_No changes yet._

### [1.0.0] - 2026-03-12

#### Added

- `.gitignore` for Python packaging, testing, and dev environments (Poetry, PDM, venv, etc.).
- VSCode settings and Claude plugin/marketplace metadata for both skills.
- READMEs at repo root and in `supervaizer_integration/`, `supervaize_access/` with installation and workflow guidance.

#### Changed

- Root `README.md` and branding updated for Runwaize skills; clearer descriptions and links to full docs.
