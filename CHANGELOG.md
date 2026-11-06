# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each skill/tool is versioned independently below.

---

## supervaize_access

### [Unreleased]

_No changes yet._

### [2.0.0] - 2026-11-06

The skill described a Studio MCP endpoint and REST routes that do not exist. It now uses only what Studio accepts.

#### Changed

- `SKILL.md` maps each request to a tool of the Supervaize MCP connector (`{base_url}/mcp/{workspace}`, OAuth) or to a helper command. Missions, jobs, cases and human answers go through the connector.
- `register-to-supervaize` validates the key and the workspace with one page of agents. Before, it called `/w/api/teams/`, which is not a route.
- `reference.md` lists the two REST route groups that accept an API key (agents, controller events) and the connector tools.

#### Removed

- `create-mission` and `show-missions-for-agent`: Studio has no mission route for an API key. Use the connector tools `mission_create` and `mission_list`.
- `start-job`: the connector tool `job_setup` starts a job.
- `mcp-tools`, `mcp-call`, `view-cases-steps --backend mcp` and the `--mcp-url` option: they called `{api_url}/api/mcp`, which Studio removed, and sent no credentials. The agent runtime endpoint (`/mcp/agent/{workspace}`) needs a runtime grant token, which a chatbot user does not have.

### [1.0.0] - 2026-03-12

#### Added

- Skill and Typer CLI helper (`supervaize_access_helper.py`) for interacting with Supervaize workspaces via REST API, MCP endpoint, and optional Supervaizer controller. Includes `SKILL.md` and `reference.md` for REST paths and MCP tool args.

#### Changed

- `SKILL.md` and `reference.md` updated (REST/MCP/controller backends, env vars, helper commands).

---

## supervaizer_integration

### [Unreleased]

_No changes yet._

### [3.0.0] - 2026-11-06

#### Changed

- In the SDK repository, the skill now interviews the developer in rounds about the mission, job, case and step mapping, and builds the integration topic by topic from the guides at docs.runwaize.com. The marketplace entry follows that version.

### [2.2.0] - 2026-11-06

#### Changed

- The skill moved to the Supervaizer SDK repository, `skills/supervaizer-integration/` (supervaize/supervaizer#165), and is released with the SDK. This repository keeps a pointer: the marketplace entry uses a `git-subdir` source, so `/plugin install supervaizer-integration` still works once the SDK change is on its default branch.

### [2.1.0] - 2026-11-06

The skill no longer holds its own copy of the contract or of the controller code. The SDK, its docs and the Hello World example are the only sources, so the skill cannot drift from them.

#### Changed

- `SKILL.md` holds the process and the design questions only. A "Sources Of Truth" table and the capability table point to the SDK scaffold, the SDK docs, the Configure and analytics guides, and the Hello World files. Contract details (field names, document shapes, environment variables) are removed.
- `scaffold-integration` runs the SDK's own `supervaizer scaffold`, then prints a checklist built from the spec; each item names the reference to copy from. It needs the `supervaizer` command in the environment.
- New capabilities covered by reference: Job Configurator, job and mission analytics, guided setup, scheduled start, rule checkpoints, workspace binding, billable consumption.

#### Removed

- The helper's controller and handler code templates (about 480 lines) and the `--workflow-filename` option. The templates had drifted: the generated controller failed to import on SDK 1.9.

#### Fixed

- `load-surface` and `invoke-action` sent `actor.id`; the contract requires `actor.user_id`.
- The spec template keys an artifact type by `type`.

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
