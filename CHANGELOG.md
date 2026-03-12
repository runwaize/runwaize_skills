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
