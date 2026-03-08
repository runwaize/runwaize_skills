# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dual-skill CLI helper system for the Supervaize platform, providing two standalone Typer-based Python CLI tools:

1. **supervaizer_integration** — Guides developers through integrating Python agents with the Supervaizer controller. Workflow: discovery questions → JSON spec → code scaffold → customize.
2. **supervaize_access** — Enables chatbots/CLI agents to interact with Supervaize SaaS workspaces via three backends: REST API, MCP HTTP endpoint, and local Supervaizer controller.

## Running the Tools

```bash
# Integration helper
python supervaizer_integration/scripts/supervaize_cli_helper.py --help
python supervaizer_integration/scripts/supervaize_cli_helper.py <command> [options]

# Access helper
python supervaize_access/scripts/supervaize_access_helper.py --help
python supervaize_access/scripts/supervaize_access_helper.py <command> [options]
```

Only external dependency: `typer` (`pip install typer`).

## Architecture

### Shared Patterns Across Both Tools

- **Typer CLI app** with `add_completion=False, no_args_is_help=True` and `@app.command()` decorators
- **`_http_json(method, url, *, body, headers, timeout)`** — stdlib `urllib` wrapper returning `(status_code, parsed_json)`. No `requests` library.
- **JSON output** — all commands emit structured JSON via `_print_json(obj, pretty)` for machine parseability
- **Error handling** — exceptions converted to JSON error responses through a `_handle(pretty, fn, ...)` wrapper
- **Environment variables** — `SUPERVAIZE_API_KEY`, `SUPERVAIZE_WORKSPACE_ID`, `SUPERVAIZE_API_URL` for SaaS; controller URL separate

### supervaizer_integration (1,366 lines)

- **Specification-driven code generation**: JSON spec defines job/case/step mapping, then `scaffold-integration` generates `supervaizer_control.py` and `sv_main.py`
- **AST-based agent analysis**: `analyze-agent` scans Python files for entrypoint functions using `ast` module, scoring by parameter count and loop detection
- Key commands: `questions`, `spec-template`, `wizard`, `analyze-agent`, `scaffold-integration`, `env-status`, `discover-controller`, `trigger-job`

### supervaize_access (1,474 lines)

- **Multi-backend**: Commands gracefully degrade when a backend (REST/MCP/Controller) is unavailable, returning structured explanations
- **Profile-based config**: Credentials persisted in `~/.supervaize_access/profile.json` (or `$CODEX_HOME/supervaize_access/profile.json`)
- **Config resolution chain**: CLI arg → env var → profile file → None
- **Event-driven status**: Reconstructs job/case/step status from controller event streams
- Key commands: `register-to-supervaize`, `list-agents`, `resolve-agent`, `create-mission`, `show-missions-for-agent`, `job-status-for-agent`, `view-cases-steps`, `start-job`, `mcp-tools`, `mcp-call`

## Skill Definitions

Each skill has a `SKILL.md` that defines its purpose, workflow, and constraints. These files are the authoritative reference for how each tool should behave and are designed to be consumed by AI agents. Read them before modifying tool behavior.

## No Build/Test/Lint System

There is no package manager config, test suite, CI/CD, or linter configuration. Tools are run directly as Python scripts. Python 3.9+ required (uses `str | None` union syntax).
