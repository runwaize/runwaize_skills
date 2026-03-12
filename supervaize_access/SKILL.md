---
name: supervaize_access
version: "1.0.0"
description: For Supervaize users: use when a chatbot/CLI/IDE agent should interact with a Supervaize workspace (register with API key, create/manage missions and agents, inspect cases/steps, human-in-the-loop) via the Supervaize REST API and/or MCP server. Includes a helper CLI that maps natural-language commands to REST/MCP/controller calls.
---

# Supervaize Access

**This skill is for Supervaize users** (customers) to give to their AI assistant (e.g. Cursor, Claude CLI, Gemini CLI, Codex) so it can manage their Supervaize workspace with their API key. Install it from the [runwaize_skills](https://github.com/supervaize/runwaize_skills) repo so the agent can list and edit agents, create and manage missions, and use case/step and human-in-the-loop via MCP.

Use this skill when the user wants a chatbot or IDE agent to **operate against an existing Supervaize workspace**.

This is a **separate skill** from `supervaizer_integration`.

- `supervaizer_integration` = add Supervaizer controller instrumentation to a custom Python agent
- `supervaize_access` = use Supervaize APIs/MCP from a chatbot/IDE after credentials/workspace are known

## REST and MCP (Studio URLs and permissions)

- **REST base**: `{base_url}/w/{team_slug}/api/v1/` — full CRUD for **agents** and **missions**. Auth: `Api-Key: <key>`.
- **MCP endpoint**: `{base_url}/api/mcp/` (root-level; not under `/w/{team_slug}/`). Same API key or Bearer (n8n). Tools: `report_case_start`, `report_case_step`, `request_human_input`, `get_case_status`, `report_case_status`, `register_agent_parameters`. All require `team_slug` in arguments.
- **Permissions**: MCP enforces the same as REST: the key’s user must be a member of the workspace; read-only users are denied write tools.
- **Gaps**: No REST CRUD with API key for jobs or cases (create/list/detail/start/stop are session-only). Case creation and step reporting are via MCP. See [reference.md](reference.md) for full REST path list and MCP tool args.

## What This Skill Enables

Map the user's phrases to helper commands:

- "Register to supervaize" -> `register-to-supervaize`
- "Create a mission" -> `create-mission`
- "Start a job" -> `start-job`
- "View case(s) / step(s)" -> `view-cases-steps`
- "Show the missions for this agent" -> `show-missions-for-agent`
- "What is the status of the jobs for this agent" -> `job-status-for-agent`

## Backends and Limits (Important)

The helper supports **three backends** because no single surface exposes everything:

1. Supervaize SaaS REST API (OpenAPI / attached YAML)
   - Works for teams, agents, missions, and controller events (`ctrl-events`)
2. Supervaize MCP HTTP endpoint (`{base_url}/api/mcp/` — root-level, no team in path)
   - Works for MCP tools like `get_case_status`, `report_case_start`, `report_case_step`, `request_human_input`, `report_case_status`, `register_agent_parameters`
3. Supervaizer controller (optional)
   - Needed for actual generic `start-job` (`POST /job/start`)

Current public API limitation (from the provided OpenAPI YAML):

- No public generic `/jobs` REST endpoint is exposed in the spec
- No public generic `/cases`/`/steps` REST endpoints are exposed in the spec
- `show-missions-for-agent` may require fallback behavior if the mission-agent relation is not included in API responses

When a command cannot be fulfilled directly from the current REST/MCP surfaces, the helper returns a **structured explanation** instead of guessing.

## Required Env Vars (SaaS)

```bash
export SUPERVAIZE_API_KEY=...
export SUPERVAIZE_WORKSPACE_ID=team_1
export SUPERVAIZE_API_URL=https://app.supervaize.com
```

Optional (for MCP / controller flows):

```bash
# MCP is at root; no /w/team_slug in path
export SUPERVAIZE_MCP_URL=https://app.supervaize.com/api/mcp
export SUPERVAIZE_CONTROLLER_URL=http://127.0.0.1:8000
export CONTROLLER_AUTH_KEY=...
```

## Helper CLI (Typer)

File: `scripts/supervaize_access_helper.py`

Dependency:

```bash
pip install typer
```

## Mandatory Chatbot Workflow

### 1) Ask the right questions first

Before running commands, ask only the missing items:

- Which workspace/team slug (`SUPERVAIZE_WORKSPACE_ID`) should I use?
- Do you have a Supervaize API key (`SUPERVAIZE_API_KEY`) already?
- Are we using SaaS REST API, MCP endpoint, controller, or a combination?
- For `start-job`: do you have a controller URL (`/job/start`) and controller auth key?
- For `view case(s)/step(s)`: do you have a `job_id`, `case_id`, or n8n `execution_id`?
- For agent-specific queries: what is the `agent_slug` (preferred) or `agent_id`?

### 2) Register the chatbot session to the workspace

```bash
python scripts/supervaize_access_helper.py register-to-supervaize --pretty
```

This validates creds/workspace and stores a local profile for later commands.

### 3) Run user-facing commands through the helper

Examples:

```bash
python scripts/supervaize_access_helper.py create-mission \
  --name "Outbound Follow-up" \
  --description "Q1 sales follow-up campaign" \
  --status draft \
  --pretty
```

```bash
python scripts/supervaize_access_helper.py start-job \
  --backend controller \
  --agent-name my_agent \
  --agent-method start \
  --user-id cli-user \
  --params-json '{"fields":{"prompt":"Hello"}}' \
  --pretty
```

```bash
python scripts/supervaize_access_helper.py view-cases-steps \
  --backend api \
  --job-id 01H... \
  --pretty
```

```bash
python scripts/supervaize_access_helper.py view-cases-steps \
  --backend mcp \
  --execution-id n8n-exec-123 \
  --pretty
```

## Command Guidance

### `register-to-supervaize`

Use first. It validates API key + workspace and saves a local profile.

### `create-mission`

Creates a mission through the SaaS REST API.

### `start-job`

Use `--backend controller` for real job starts.

If the user only provides SaaS REST API / MCP access, explain that the current public OpenAPI spec and MCP tools do not expose a generic job-start endpoint.

### `view-cases-steps`

Use one of these modes:

- `--backend api`: read `ctrl-events` and reconstruct case/step activity (best effort)
- `--backend mcp`: call `get_case_status` for a known `execution_id`

### `show-missions-for-agent`

Try REST API first. If mission objects do not expose agent linkage, return a structured limitation message and suggest:

- providing internal endpoint access, or
- using another source that explicitly maps agent <-> mission

### `job-status-for-agent`

Uses `ctrl-events` and aggregates job lifecycle events (best effort). Make clear that accuracy depends on agent identifiers being present in event `source`/`details`.

## References (Use as needed)

- **REST paths and MCP tool args**: [reference.md](reference.md) in this skill folder.
- **Studio documentation**: [Workspace API](https://github.com/supervaize/studio/blob/main/Documentation/workspace_api.md) in the Supervaize Studio repo.
- OpenAPI: `{base_url}/api/doc`, `{base_url}/api/doc/swagger-ui/`, `{base_url}/api/doc/redoc/`

## Output Style

Return structured JSON from the helper whenever possible so another chatbot/CLI can parse it.
