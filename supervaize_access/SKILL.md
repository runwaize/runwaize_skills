---
name: supervaize_access
version: "2.0.0"
description: For Supervaize users: use when a chatbot/CLI/IDE agent should operate an existing Supervaize workspace. Missions, jobs, cases, steps and human-in-the-loop answers go through the Supervaize MCP connector (OAuth). A helper CLI reads agents and controller events with an API key.
---

# Supervaize Access

**This skill is for Supervaize users** (customers). It tells an AI assistant (Claude, ChatGPT, Cursor, Codex, Gemini CLI) how to operate their Supervaize workspace.

This is a **separate skill** from `supervaizer-integration`, which connects a custom Python agent to Supervaize Studio.

## Two Ways In

| Way in | Authentication | What it can do |
| --- | --- | --- |
| **Supervaize MCP connector** `{base_url}/mcp/{workspace}` | OAuth sign-in by the user, in the chat client | Missions, jobs, cases, steps, human answers, schedules. Calls run with the workspace roles of the user |
| **REST API** `{base_url}/w/{workspace}/api/v1/` | `Authorization: Api-Key <key>` | Read agents. Read controller events (`ctrl-events`). Nothing else |

An API key does not open the MCP connector. It does not create a mission, start a job, or read a case.

Studio has a second MCP endpoint, `{base_url}/mcp/agent/{workspace}`. It is for a workflow runtime (for example n8n) with a runtime grant token. This skill does not use it.

## Map The Request

Prefer the connector. Use the helper when the connector is not connected, or for the two helper-only rows.

| The user says | With the MCP connector | With the helper (API key) |
| --- | --- | --- |
| "Register to Supervaize" | Not applicable | `register-to-supervaize` |
| "List the agents" | `agent_list` | `list-agents` |
| "Show the missions" / "missions for this agent" | `mission_list`, then `mission_get` | Not possible |
| "Create a mission" | `mission_create` | Not possible |
| "Start a job" | `job_setup` | Not possible |
| "View the cases / the steps" | `case_list`, `case_get` | `view-cases-steps` (best effort) |
| "Answer the agent" (human in the loop) | `step_submit` | Not possible |
| "Status of the jobs for this agent" | `job_list`, `job_get` | `job-status-for-agent` (best effort) |

Rules for the connector:

- Start with `mission_list` to see what the workspace runs. Then go down to jobs, cases and steps.
- Read the description of a tool before the first call. The connector gives the arguments and the limits.
- A refused call means that the user does not have that right in Studio. Say so. Do not retry it through the helper.

When "Not possible" applies and the connector is not connected, say so and give the connection page: https://docs.runwaize.com/docs/supervaize-fleet/mcp-connector/install. Do not guess a REST route.

## Chatbot Workflow

### 1) Ask only for what is missing

- Is the Supervaize MCP connector connected in this chat client?
- For the helper: the workspace slug (`SUPERVAIZE_WORKSPACE_ID`) and an API key (`SUPERVAIZE_API_KEY`).
- For cases and steps: a `job_id` or a `case_id`.
- For agent questions: the `agent_slug` (preferred) or the `agent_id`.

The user creates an API key in Studio: profile menu, **Developer**, **Create API Key**. Never ask for a password.

### 2) Set the helper up (only if you use it)

```bash
export SUPERVAIZE_API_KEY=...
export SUPERVAIZE_WORKSPACE_ID=your-workspace-slug
export SUPERVAIZE_API_URL=https://app.supervaize.com

pip install typer
python scripts/supervaize_access_helper.py register-to-supervaize --pretty
```

`register-to-supervaize` reads one page of agents. This proves the key, the URL and the workspace slug together. It saves a local profile for the next commands. It creates nothing in Supervaize.

### 3) Run the command

```bash
python scripts/supervaize_access_helper.py list-agents --pretty
python scripts/supervaize_access_helper.py view-cases-steps --job-id 01H... --pretty
python scripts/supervaize_access_helper.py job-status-for-agent --agent-slug my-agent --pretty
```

## Helper Commands

| Command | What it does |
| --- | --- |
| `questions` | Prints the questions of step 1 |
| `env-status` | Shows which settings are present. `--shell-template` prints the `export` lines |
| `register-to-supervaize` | Validates the key and the workspace, saves the profile |
| `list-agents` | Lists the agents of the workspace |
| `view-cases-steps` | Rebuilds cases and steps from the controller events. Filter with `--job-id` or `--case-id` |
| `job-status-for-agent` | Summarizes the job events of one agent |

The last two commands read `ctrl-events`. They are a best effort: the result depends on the identifiers that the agent puts in its events. The connector tools `case_list` and `job_list` are exact. Say which source you used.

## Output Style

The helper prints JSON. Give the user a short answer, and keep the JSON for the next step.

## References

- REST routes and connector tools: [reference.md](reference.md).
- Skill documentation: https://docs.runwaize.com/docs/integrations/skills/supervaize-access
- Connector installation: https://docs.runwaize.com/docs/supervaize-fleet/mcp-connector/install
- OpenAPI: `{base_url}/api/doc`, `{base_url}/api/doc/swagger-ui/`, `{base_url}/api/doc/redoc/`
