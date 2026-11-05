---
name: supervaizer-integration
description: Use when a user has an existing Python agent and wants to integrate it with Supervaizer v2 and Supervaize Studio, or wants to add a v2 capability to an integrated agent (Configure screen, human-in-the-loop, resources, dashboards, scheduled start, rule checkpoints, guided setup, billing). This skill analyzes the agent, designs the v2 Job/Case/Step/Resource/Surface/Action mapping, installs supervaizer, and generates v2 controller scaffolding with A2A JSON-RPC and A2UI surfaces.
---

# Supervaizer Integration

Integrate an existing Python agent with Supervaizer v2. Treat v2 as the only supported target. Do not scaffold v1 job fields, `dynamic_choices`, `job_poll`, ACP, or callback-shaped UI logic. A v2 agent needs no v1 `methods`.

This skill targets **Supervaizer 1.9 or later** (Python 3.12+). Check the installed version before you rely on a feature; the capability table below names the release that added each one.

## Core Model

Use this language consistently:

- `Job`: a user-visible unit of work started or synchronized by Studio.
- `Case`: a business item inside a Job. Use `lane` as a rendering hint. Default lane is `work`; common lanes are `setup`, `work`, and `deliverable`.
- `Step`: work inside a Case. Use `activity`, `status`, optional `awaiting`, `outputs`, and `cost`.
- `Resource`: agent-owned business data Studio may list, edit, import, or relate through generic v2 actions.
- `Dataset`: agent-owned queryable analytics data.
- `Surface`: an A2UI document returned through `supervaizer/surface.load`.
- `Action`: typed business command invoked through `supervaizer/action.invoke`.
- `Artifact`: agent-owned output vocabulary. Do not make agent-specific artifact names protocol enums.

Failure is a status, not a step kind. Human input is `status="awaiting"` plus an `awaiting` object, not a step kind. Dynamic UI behavior must be either A2UI local logic or typed v2 action calls.

## Reference Material

Read the source of truth before you generate code. Prefer a local checkout of the SDK when the project has one; otherwise use these:

- Supervaizer v2 guide (registration, surfaces, actions, `job_state`): https://github.com/supervaize/supervaizer/blob/main/docs/2026_05_SUPERVAIZER_v2.md
- Protocol split (A2A, A2UI, workspace authorization): https://github.com/supervaize/supervaizer/blob/main/docs/2026_05_PROTOCOLS.md
- Workspace agent grants: https://github.com/supervaize/supervaizer/blob/main/docs/2026_05_WORKSPACE_AGENT_GRANTS.md
- Local testing: https://github.com/supervaize/supervaizer/blob/main/docs/2025_10_LOCAL_TESTING.md
- Job Configurator (Configure screen) guide: https://docs.runwaize.com/docs/supervaizer-controller/job-configurator
- Job and mission analytics guide: https://docs.runwaize.com/docs/supervaizer-controller/job-analytics
- SDK changelog: https://github.com/supervaize/supervaizer/blob/main/docs/CHANGELOG.md
- Hello World, a working agent that uses most capabilities below: https://github.com/runwaize/supervaize_hello_world

## Workflow

### 1. Discover The Agent

Inspect the project before generating code:

- package manager: `pyproject.toml`, `requirements.txt`, `setup.py`
- existing web framework
- existing agent entrypoint
- environment variables and secrets
- user-facing inputs
- agent-owned data
- outputs, reports, transcripts, metrics, or files
- places where human review is required
- an existing `supervaizer_control.py` (then extend it; do not overwrite it)

Optional helper:

```bash
python supervaizer_integration/scripts/supervaize_cli_helper.py analyze-agent \
  --project-root /path/to/agent \
  --pretty
```

### 2. Design The V2 Mapping

Ask only what is needed to make the v2 contract explicit:

- What is one Job?
- What are the Cases? Are they one per input item, session, contact, document, lead, or something else?
- Which lanes should Studio render? Use `work` by default; add `setup` and `deliverable` only when useful.
- What Steps exist in each Case? What does each Step cost?
- Which Steps await a human? What A2UI fields should be submitted through `step.awaiting.submit`?
- What Resources should Studio manage, at which scope (`workspace`, `mission`, `job`)?
- Which Resource operations are allowed: `list`, `get`, `create`, `update`, `delete`, `import`?
- Which Datasets or Vega-Lite dashboards should Studio render, on the mission page, on each job page, or both?
- Does a job need setup that an operator edits on the job page (a Configure screen)? Which sections, and how do they change after launch?
- What Artifacts does the agent produce?
- What external source can `job.sync` use to converge status?
- Which optional capabilities below does the agent need? Add only those the business asks for.

No guessing: if workspace identity, resource scope, required secrets, or business validation rules are missing, ask or fail clearly.

### 3. Generate A Spec

Use the helper to create a v2 spec:

```bash
python supervaizer_integration/scripts/supervaize_cli_helper.py wizard \
  --output-file integration_spec.json \
  --pretty
```

Or start from:

```bash
python supervaizer_integration/scripts/supervaize_cli_helper.py spec-template \
  --output-file integration_spec.json \
  --pretty
```

Review the spec before scaffolding. The spec is the contract design surface; do not use generated defaults as a substitute for business decisions. Set `integration.scheduled_start` to `true` when Studio may start the agent on a schedule. Artifact types are keyed by `type` (`{"type": "report", "label": "Report"}`).

### 4. Install Supervaizer

Use the target project's package manager:

```bash
uv add supervaizer
uv sync
```

or:

```bash
pip install supervaizer
```

### 5. Scaffold V2 Integration

```bash
python supervaizer_integration/scripts/supervaize_cli_helper.py scaffold-integration \
  --spec-file integration_spec.json \
  --output-dir /path/to/agent \
  --force \
  --pretty
```

Generated files:

- `supervaizer_control.py`: v2 registration, Agent, Server, surface/action registration.
- `agent_impl.py`: A2UI surface handlers, v2 action dispatcher (`job.start`, `job.sync`, `job.stop`, `step.awaiting.submit`, resource actions), `job_state` snapshot builder.

For an agent with no existing controller and no mapping to design, the SDK's own `supervaizer scaffold` command writes a smaller `supervaizer_control.py` (one registration, one surface, one action).

Customize all TODOs before using the integration. In particular:

- enforce tenant/workspace scope in every resource/action handler, from the verified `workspace_authorization` context, never from a caller-supplied slug
- wire `job.start` to the real agent entrypoint and replace the in-memory job store
- implement `job.sync` and `job.stop`
- return accurate Case/Step snapshots
- implement Resource operations with explicit validation
- add HITL `awaiting` forms only where business logic requires human input

### 6. Smoke Test

Run without Studio in local mode. The controller then needs no Studio account and accepts v2 calls without a workspace token. The API key defaults to `local-dev`.

```bash
SUPERVAIZER_LOCAL_MODE=true python supervaizer_control.py
```

Inspect discovery:

```bash
curl http://127.0.0.1:8000/.well-known/agents.json
```

Load a surface:

```bash
python supervaizer_integration/scripts/supervaize_cli_helper.py load-surface \
  --controller-url http://127.0.0.1:8000 \
  --controller-api-key local-dev \
  --agent-slug my-agent \
  --surface job.start \
  --workspace-slug test_wkpsc \
  --mission-id local-mission \
  --pretty
```

Invoke a v2 action:

```bash
python supervaizer_integration/scripts/supervaize_cli_helper.py invoke-action \
  --controller-url http://127.0.0.1:8000 \
  --controller-api-key local-dev \
  --agent-slug my-agent \
  --action job.start \
  --surface job.start \
  --workspace-slug test_wkpsc \
  --mission-id local-mission \
  --params-json '{"goal":"hello"}' \
  --pretty
```

Then write tests that post the same JSON-RPC requests to `server.app` with FastAPI's `TestClient`. The Hello World `tests/` folder shows the pattern, including a signed workspace token.

### 7. Connect To Studio

A Studio-registered controller needs:

- `SUPERVAIZE_API_KEY`, `SUPERVAIZE_WORKSPACE_ID`, `SUPERVAIZE_API_URL` for the `Account`.
- `SUPERVAIZER_API_KEY` for the controller's own `X-API-Key`.
- Workspace authorization trust: `SUPERVAIZER_WORKSPACE_AUTH_ISSUER` (the Studio SPA origin shown on its Developer page) and `SUPERVAIZER_WORKSPACE_AUTH_JWKS_URL` (or `SUPERVAIZER_WORKSPACE_AUTH_PUBLIC_KEY`).

Studio signs each v2 call with a workspace authorization token. The SDK verifies it and fails closed. A wrong issuer makes job start fail with "Workspace authorization token issuer does not match this server configuration".

When the registration gains an action, the workspace must accept the agent grant again in Studio before that action can be called.

## Runtime Rules

Apply these to every handler you write or review:

- **Declare action metadata.** `capabilities.actions` holds `V2ActionDefinition` objects. A bare id string means `mutating=True, scope="job"`. Declare read-only actions with `V2ActionDefinition(id=..., mutating=False)` and set `scope` to `workspace` or `mission` where that applies. Studio authorizes from these fields, never from the id text. Register handlers with `action.id`.
- **Return `job_state` at the top level** of the action result. Studio projects cases only from there, never from an effect.
- **Report the job cost** in `job_state.job.information.cost.total_cost`. Studio adds step costs into the case cost but reads the job cost from the snapshot.
- **Be idempotent.** `job.start` and other mutating actions carry an `idempotency_key`. Studio retries with the same key after an uncertain result and for each scheduled occurrence. Return the original result; create nothing new.
- **Push, do not expect polling.** Studio does not poll a v2 job. Return the new state from the action, or send the controller event `supervaizer.v2.job.refresh_requested` so Studio calls `job.sync`.
- **Trust verified context only.** Use `request.workspace_authorization` for workspace identity. Workspace and tenant slugs in the payload are routing hints.
- **Use mission context when present.** Requests and DataResource calls may carry `mission` (`id`, `name`, `metadata`), passed through from Studio uninterpreted.
- **Keep secrets out of results and logs.** Agent parameter values are not serialized by the SDK; do not echo them in effects or case metadata.

## Optional Capabilities

Add a capability only when the mapping in step 2 calls for it. Each row names the declaration, the SDK release, and where to copy a working pattern from.

| Capability | How to declare it | Since | Pattern |
| --- | --- | --- | --- |
| Human in the loop | Step `status="awaiting"` with `awaiting` (`reason`, `surface`, `action`, `fields`, optional `reopenable`); `case.step.awaiting` surface; `step.awaiting.submit` action | 1.0 (`reopenable` 1.6) | Hello World `agent_v2.py`, `tests/test_hitl.py` |
| File upload fields | Awaiting field `type: "file"` with `accept`, `max_bytes`, `storage` (`studio` or `inline`) | 1.9 | v2 guide, "Step" |
| Resources | `resources=[V2ResourceDefinition(...)]` with `scope`, `operations`, `auto_surface` | 1.0 | Hello World `agent_data_resource.py` |
| Datasets and dashboards | `datasets=[...]` (query action derived, `mutating=False`); `mission.analytics` and `job.analytics` surfaces returning a `Dashboard` | 1.0 (`scope` 1.6) | See "Analytics Dashboards" below |
| Artifacts and deliverables | `artifact_types=[{"type", "label"}]`; step `outputs`; read-only `artifact.get` action | 1.0 | Hello World `agent_deliverable.py` |
| Workspace binding | `workspace_binding` metadata with `workspace_binding.options` and `workspace_binding.create` | 1.1 | Workspace agent grants doc |
| Agent-level actions | `AgentMethods` standard actions such as `agent.refresh`, plus custom agent actions | 1.2 | v2 guide, "Actions" |
| Context assignment | Handle the `context.assign` action (`V2_ACTION_CONTEXT_ASSIGN`, `V2ContextAssignment`) | 1.3 | v2 guide, "Context assignment semantics" |
| Job setup policy | `job_policy={"setup": {...}}` (`preview_action`, `start_action`, `submit_action`, `action_scopes`, `plan`) | 1.5 | v2 guide, "Action metadata" |
| Labels and tooltips | `V2SurfaceDefinition(id, label, description)`; `label` and `description` on `V2ActionDefinition` (300 characters) | 1.7 | v2 guide, "Display text" |
| Rule checkpoints | `rule_checkpoints={"phases": ["before", "after"]}`; `RuleCheckpointGate` or `Case.run_guarded_step()`; `rule.checkpoint.resume` action | 1.7 | Hello World `agent_rules.py` |
| Scheduled start | `scheduled_start=True` (needs `job.start`); Studio owns the clock and sends a `schedule` object | 1.8 | Hello World `tests/test_scheduling.py` |
| Job Configurator | `job.configurator` surface returning a `Configurator` document; job-scoped actions bound to its buttons | Studio feature, any v2 SDK | See below |
| Agent introduction | `Agent(introduction=...)`: `tagline`, `summary`, `example_goals`, `avatar_url` | 1.9 | v2 guide, "Introduction" |
| Full description | `Agent(full_description=...)`: `format` (`markdown` or `html`) and `content` | 1.9 | v2 guide, "Full description" |
| Guided setup | Typed `V2SetupPlan` (steps, `cost_estimate`), field schema (`depends_on`, `{value, label}` choices, `min_rows`, validation), help actions, dry runs | 1.9 | v2 guide, "Setup plan and field schema", "Help actions and dry runs" |
| Billable consumption | `Agent(billing_catalog=[...])` and `Account.report_consumption(records, agent_slug=...)` | after 1.9.0 | SDK doc `2026_10_BILLABLE_CONSUMPTION.md` |

Every optional field is omitted from the registration when unset, so adding one capability does not change the others.

## Job Configurator (Configure Screen)

Use it when a job needs setup that an operator edits on the job page: parameters, participants, a prompt or template, a readiness checklist, a launch button, export links. Follow the guide at https://docs.runwaize.com/docs/supervaizer-controller/job-configurator and copy from Hello World `agent_configurator.py`.

The contract in short:

1. Declare the `job.configurator` surface and every action the document binds. Bound actions must be declared and job-scoped.
2. The surface handler returns `{"type": "Configurator", "id", "schema_version", "revision", "title", "sections", "readiness", "primary_action"}`.
3. Each section has `id`, `label`, `policy` (`editable`, `read_only`, `editable_with_confirmation`, `hidden`) and one `component`: `Form`, `ResourceList`, `TemplateComposer`, `Review`, or `Table` (schema `"2"` only).
4. A binding is `{"action_id", "target_scope": "job", "payload_source": "component" | "document"}` with an optional `confirmation`.
5. Studio adds `revision` to every action input. Compare it first; answer a stale one with `status="error"` and a `configurator.conflict` effect carrying `current_revision`.
6. Negotiate the schema from `input.supported_schema_versions`; return a `ConfiguratorError` document with `code: "unsupported_schema"` when none is shared.
7. A surface load never writes state. Validate again in every action: policies and readiness are presentation.
8. Studio refuses the whole document on a contract error, including any key that normalizes to `html`, `script`, `iframe`, `src`, `style`, `css`, `import`, `expression`, `targetid`, `jobid`, `missionid`, `caseid` or `stepid`. Test every emitted document for these.
9. Optional `job_state.job.display` (`entity_label`, `state_label`, `primary_action_label`) labels the job in Studio lists.

Design the sections with the user. The catalog covers these needs:

| Need | Component | Notes |
| --- | --- | --- |
| Settings | `Form` with a `save` binding | Field types `text`, `number`, `boolean`, `date`, `email`, `select`, `resource_ref`, `file`, `list`; keys `default`, `required`, `read_only`, `multiline`, `options`, `options_source`, `depends_on`, `description` |
| Read-only facts | `Form` of `read_only` fields | Creation date, owner, status |
| A one-click operation | `Form` whose `save` names the action | `save_label` is the button text, for example "Generate synthesis" |
| File upload | `Form` with a top-level `file` field | `accept`, `max_bytes`, `storage: "studio"`; the agent receives a stored-file reference |
| Rows to add, import, remove | `ResourceList` | Rows from `resource.<id>.list`; optional `create`, `import`, `delete` bindings; `create_selector` for a searchable picker; `resource_ref` needs `options_source` |
| Prompt or template editing | `TemplateComposer` | `nodes`, `slots`, `tokens`, `versions`, `validation`, `preview`; read-only events `validation.requested` and `selection.changed` with `local_state` |
| Checklist and launch | `Review` plus `readiness` and `primary_action` | The button shows only in the Review section |
| Results, links, downloads | `Table` (schema 2) | Cells are text, `href` links, or `artifact` descriptors opened through `artifact.get` |

Plan the screen over the life of the job:

- **No domain object yet:** one `editable` section that creates or selects it, the others `hidden`, one `blocked` readiness line.
- **Setup:** setup sections `editable`; primary action is the launch, `disabled` until readiness is all `ok`.
- **Running:** setup sections `read_only`, result sections visible, primary action changes (for example "Close", with a `confirmation`).
- **Finished:** `primary_action: null`, sections `read_only`.

Also:

- Return `job_state` from the actions that change cases or display labels.
- Studio refuses workspace-scoped or mission-scoped actions through a job binding. Declare job-scoped twins of resource mutations; only read-only `list` and `get` lookups cross the boundary.
- Derive the revision from saved state only (a counter or a hash). Display data and read-only events must not change it.
- For a refusal other than a conflict, return `status="error"` with an effect that carries a `message`.
- Hide or omit data the operator must not see (for example transcripts of an anonymized campaign): the agent decides, Studio only renders.

## Analytics Dashboards

Use them when the agent has data worth charting. Follow https://docs.runwaize.com/docs/supervaizer-controller/job-analytics and copy from Hello World `agent_dashboard.py`.

1. Declare each dataset in `datasets=[...]`. The SDK derives `dataset.<id>.query` (`mutating=False`).
2. Declare `job.analytics` for a **Job Analytics** section on every job page, `mission.analytics` for the mission page **Analytics** link, or both. One builder can serve the two.
3. The surface returns `{"type": "Dashboard", "id", "title", "datasets", "controls", "widgets", "state"}`.
4. A dataset entry has `id`, `label`, `input`, `display.columns` and `metrics`. Each metric is a KPI card with a `reducer`: `row_count`, `sum`, `avg`, `max`, `distinct_count` (need `field`) or `ratio` (`numerator_field`, `denominator_field`); optional `suffix`.
5. Controls are `segmented` (with `options` and `default`) or `date`. Studio adds each value to every dataset query under the control `id`.
6. Widgets are charts: `data: {"mode": "ref", "datasetId": ...}` or inline `data.values`, `layout: {"w", "h"}` on a 12-column grid, and `visualization: {"type": "vega-lite", "spec": {...}}`. Studio renders only `vega-lite` widgets with a `spec`.
7. The query handler returns `{"type": "dataset.queried", "dataset": "<id>", "count": n, "rows": [...]}` as an effect. Its input is the job's start fields, then the dataset `input`, then the control values.
8. For `job.analytics`, resolve the domain object from `job_id`, check it against the verified workspace, and scope every dataset through its `input`. Default to the whole life of the job. The job page shows KPI cards and charts; dataset tables show on the mission page only.

## Output Expectations

When completing a Supervaizer v2 integration, report:

- Job/Case/Step mapping
- lane vocabulary
- registered surfaces
- registered actions, with their `mutating` and `scope` values
- resource and dataset contracts
- HITL forms
- optional capabilities added, and the SDK version they need
- tenant/workspace access control assumptions
- smoke tests run
- remaining business logic TODOs
