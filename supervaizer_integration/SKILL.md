---
name: supervaizer-integration
description: Use when a user has an existing Python agent and wants to integrate it with Supervaizer v2 and Supervaize Studio. This skill analyzes the agent, designs the v2 Job/Case/Step/Resource/Surface/Action mapping, installs supervaizer, and generates v2 controller scaffolding with A2A JSON-RPC and A2UI surfaces.
---

# Supervaizer Integration

Integrate an existing Python agent with Supervaizer v2. Treat v2 as the only supported target. Do not scaffold v1 job fields, `dynamic_choices`, `job_poll`, ACP, or callback-shaped UI logic.

## Core Model

Use this language consistently:

- `Job`: a user-visible unit of work started or synchronized by Studio.
- `Case`: a business item inside a Job. Use `lane` as a rendering hint. Default lane is `work`; common lanes are `setup`, `work`, and `deliverable`.
- `Step`: work inside a Case. Use `activity`, `status`, optional `awaiting`, and `outputs`.
- `Resource`: agent-owned business data Studio may list, edit, import, or relate through generic v2 actions.
- `Dataset`: agent-owned queryable analytics data.
- `Surface`: an A2UI document returned through `supervaizer/surface.load`.
- `Action`: typed business command invoked through `supervaizer/action.invoke`.
- `Artifact`: agent-owned output vocabulary. Do not make agent-specific artifact names protocol enums.

Failure is a status, not a step kind. Dynamic UI behavior must be either A2UI local logic or typed v2 action calls.

## Reference Material

Prefer local docs when available:

- Supervaizer v2 concepts: `/Volumes/SSDext1TB/Documents/GitRepo/RUNWAIZE/supervaizer/docs/2026_05_SUPERVAIZER_v2.md`
- Protocol split: `/Volumes/SSDext1TB/Documents/GitRepo/RUNWAIZE/supervaizer/docs/2026_05_PROTOCOLS.md`
- Built-in Hello World v2 example: `/Volumes/SSDext1TB/Documents/GitRepo/RUNWAIZE/supervaizer/src/supervaizer/examples/local_server.py`
- Public Hello World repo: `https://github.com/supervaize/supervaize_hello_world`

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
- What Steps exist in each Case?
- Which Steps await a human? What A2UI fields should be submitted through `step.awaiting.submit`?
- What Resources should Studio manage?
- Which Resource operations are allowed: `list`, `get`, `create`, `update`, `delete`, `import`?
- Which Datasets or Vega-Lite dashboards should Studio render?
- What Artifacts does the agent produce?
- What external source can `job.sync` use to converge status?

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

Review the spec before scaffolding. The spec is the contract design surface; do not use generated defaults as a substitute for business decisions.

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
- `agent_impl.py`: A2UI surface handlers, v2 action dispatcher, `job_state` snapshot builder, resource action placeholders.

Customize all TODOs before using the integration. In particular:

- enforce tenant/workspace scope in every resource/action handler
- wire `job.start` to the real agent entrypoint
- implement `job.sync`
- return accurate Case/Step snapshots
- implement Resource operations with explicit validation
- add HITL `awaiting` forms only where business logic requires human input

### 6. Smoke Test

Start the controller:

```bash
python supervaizer_control.py
```

Inspect discovery:

```bash
curl http://127.0.0.1:8000/.well-known/agents.json
```

Load a surface:

```bash
python supervaizer_integration/scripts/supervaize_cli_helper.py load-surface \
  --controller-url http://127.0.0.1:8000 \
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
  --agent-slug my-agent \
  --action job.start \
  --surface job.start \
  --workspace-slug test_wkpsc \
  --mission-id local-mission \
  --params-json '{"goal":"hello"}' \
  --pretty
```

## Output Expectations

When completing a Supervaizer v2 integration, report:

- Job/Case/Step mapping
- lane vocabulary
- registered surfaces
- registered actions
- resource and dataset contracts
- HITL forms
- tenant/workspace access control assumptions
- smoke tests run
- remaining business logic TODOs
