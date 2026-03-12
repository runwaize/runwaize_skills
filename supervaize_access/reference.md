# Supervaize workspace API — reference

Base URL placeholder: `{base}` = `{base_url}/w/{team_slug}/api/v1/`. Auth: `Api-Key: <key>`.

## REST paths

### Agents

| Method | Path                           | Description                       |
| ------ | ------------------------------ | --------------------------------- |
| GET    | `{base}agents/`                | List agents (paginated)           |
| POST   | `{base}agents/`                | Create agent                      |
| GET    | `{base}agents/{id}/`           | Retrieve agent by ID (hex string) |
| GET    | `{base}agents/by-slug/{slug}/` | Retrieve agent by slug            |
| PUT    | `{base}agents/{id}/`           | Full update                       |
| PATCH  | `{base}agents/{id}/`           | Partial update                    |
| DELETE | `{base}agents/{id}/`           | Delete agent                      |

Create/update body (AgentSerializer): id (read-only), name, slug, alias, server, status, onboarding_status, tags, deployment_config, methods, parameters_setup_definition (read-only).

### Missions

| Method | Path                   | Description               |
| ------ | ---------------------- | ------------------------- |
| GET    | `{base}missions/`      | List missions (paginated) |
| POST   | `{base}missions/`      | Create mission            |
| GET    | `{base}missions/{id}/` | Retrieve mission          |
| PUT    | `{base}missions/{id}/` | Full update               |
| PATCH  | `{base}missions/{id}/` | Partial update            |
| DELETE | `{base}missions/{id}/` | Delete mission            |

Create/update body (MissionSerializer): id, team_id, name, description, budget, status, priority, start_date, end_date.

### Controller events (integration)

| Method | Path                      | Description                        |
| ------ | ------------------------- | ---------------------------------- |
| GET    | `{base}ctrl-events/`      | List controller events (slim list) |
| POST   | `{base}ctrl-events/`      | Create (e.g. server registration)  |
| GET    | `{base}ctrl-events/{id}/` | Retrieve (full details)            |

## MCP tools (inputSchema summary)

Endpoint: `{base_url}/api/mcp/`. Auth: `Api-Key: <key>` or `Authorization: Bearer <token>` (n8n).

### report_case_start

- **Required**: job_id (string), execution_id (string), team_slug (string).
- **Optional**: name (string), description (string).

### report_case_step

- **Required**: execution_id (string), team_slug (string).
- **Optional**: index (integer), name (string), payload (object), cost (number), is_final (boolean), error (string).

### request_human_input

- **Required**: execution_id (string), team_slug (string), form_fields (array of { name, field_type?, description?, required? }).
- **Optional**: step_index (integer), message (string).

### get_case_status

- **Required**: execution_id (string), team_slug (string).
- **Optional**: correlation_id (string).

### report_case_status

- **Required**: execution_id (string), team_slug (string), status (string, enum: started, waiting, resumed, completed, failed, terminated).
- **Optional**: error_message (string), correlation_id (string).

### register_agent_parameters

- **Required**: workflow_id (string), team_slug (string), parameters (array of { name, description?, is_secret?, is_required?, default_value? }).

## OpenAPI / docs

- Schema: `{base_url}/api/doc`
- Swagger UI: `{base_url}/api/doc/swagger-ui/`
- ReDoc: `{base_url}/api/doc/redoc/`
