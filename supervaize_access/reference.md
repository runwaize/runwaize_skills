# Supervaize workspace access: reference

## REST routes that accept an API key

Base: `{base}` = `{base_url}/w/{workspace}/api/v1/`. Header: `Authorization: Api-Key <key>`. Add the header `workspace: <workspace slug>` for the controller events.

| Method | Path | Description |
| --- | --- | --- |
| GET | `{base}agents/` | List agents (paginated) |
| GET | `{base}agents/{id}/` | Retrieve an agent by ID |
| GET | `{base}agents/by-slug/{slug}/` | Retrieve an agent by slug |
| GET | `{base}ctrl-events/` | List controller events (slim list) |
| GET | `{base}ctrl-events/{id}/` | Retrieve a controller event (full details) |

The user of the key must be a member of the workspace, and the workspace needs an active subscription.

No other route accepts an API key for a chatbot. The mission, job and case routes need a signed-in Studio session.

## MCP connector (user tools)

Endpoint: `{base_url}/mcp/{workspace}`. Authentication: OAuth sign-in and consent in the chat client. An API key is not accepted.

| Area | Tools |
| --- | --- |
| Workspace | `workspace_info`, `catalog` |
| Agents | `agent_list`, `agent_action_invoke` |
| Missions | `mission_list`, `mission_get`, `mission_stats`, `mission_create` |
| Jobs | `job_list`, `job_get`, `job_setup`, `job_sync` |
| Cases and steps | `case_list`, `case_get`, `step_submit` |
| Agent data | `resource_list`, `resource_get`, `artifact_get` |
| Schedules | `schedule_list`, `schedule_get`, `schedule_create`, `schedule_update`, `schedule_pause`, `schedule_resume`, `schedule_run_now`, `schedule_delete` |

The connector gives the arguments of each tool. `agent_action_invoke`, `schedule_run_now` and `schedule_delete` are marked destructive: confirm with the user first.

Installation and consent: https://docs.runwaize.com/docs/supervaize-fleet/mcp-connector/install

## Agent runtime endpoint (not used by this skill)

`{base_url}/mcp/agent/{workspace}` is for a workflow runtime such as n8n. It needs the Bearer token of a runtime grant. Its tools report cases and steps: `report_case_start`, `report_case_step`, `request_human_input`, `get_case_status`, `report_case_status`, `register_agent_parameters`. See https://docs.runwaize.com/docs/integrations/n8n-integration

## OpenAPI

- Schema: `{base_url}/api/doc`
- Swagger UI: `{base_url}/api/doc/swagger-ui/`
- ReDoc: `{base_url}/api/doc/redoc/`
