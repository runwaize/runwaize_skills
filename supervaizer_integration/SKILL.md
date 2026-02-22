---
name: supervaizer_integration
description: Use when a user has an existing Python custom agent and wants to integrate the Supervaizer controller into it. This skill helps analyze the agent logic, identify the correct Job/Case/Step mapping, define agent parameters and job start fields, and scaffold/customize `supervaizer_control.py`  and `sv_main.py`.
---

# Supervaizer Integration

Use this skill to integrate **any existing Python agent** with the **Supervaizer controller** and the **Supervaize SaaS platform**.

This is not just a generic controller helper. The core task is to:

1. Understand the user's existing agent logic
2. Decide what one **Job** means in that agent
3. Decide what each **Case** means (if the job processes multiple items)
4. Define the ordered **Steps** inside each case
5. Map user inputs to `job_start.fields`
6. Map secrets/config to `ParametersSetup`
7. Scaffold and customize `supervaizer_control.py` and `sv_main.py`

## Reference Integrations (Examples)

Use these as pattern references when reasoning about the mapping:

- Email AI Agent (Supervaizer branch): `supervaizer_control.py` + `sv_main.py`
  - [GitHub branch](https://github.com/alain-sv/Email-AI-Agent/tree/supervaizer)
- Callagen local example:
  - `/Users/alp/GitRepo/SUPERVAIZE/9agents/callagen/supervaizer_control.py`
  - `/Users/alp/GitRepo/SUPERVAIZE/9agents/callagen/callagen/call_agent.py`
  - `/Users/alp/GitRepo/SUPERVAIZE/9agents/callagen/callagen/steps.py`

The `callagen` example is especially useful because it shows:

- `ParametersSetup` (agent secrets/env vars)
- `job_start.fields` (user-facing start form)
- `nodes` (declared step flow)
- runtime `Case.start(...)` + `CaseNodeUpdate(...)` instrumentation in the actual agent logic

## Required Env Vars (Supervaize SaaS)

```bash
export SUPERVAIZE_API_KEY=...
export SUPERVAIZE_WORKSPACE_ID=team_1
export SUPERVAIZE_API_URL=https://app.supervaize.com
```

Optional local controller auth:

```bash
export CONTROLLER_AUTH_KEY=...
```

## Helper CLI (Typer)

File: `scripts/supervaize_cli_helper.py`

Dependency:

```bash
pip install typer
```

Run from inside this skill folder (`supervaizer_integration/`), or adapt paths.

## Mandatory Workflow (Do Not Skip)

### 1) Ask the user the right questions first

Before scaffolding, ask these questions (or use the helper's `questions` / `wizard` commands):

- What function should Supervaizer call to start the agent?
- What does one Job represent in business terms?
- Does a job process multiple items? What is one Case?
- What field contains the case items (CSV/list/single)?
- What are the ordered Steps inside each case?
- Which steps are HITL (human confirmation/review)?
- What inputs belong in `job_start.fields`?
- What env vars/secrets belong in `ParametersSetup`?
- How do form fields map to the target function parameters?
- What should the final job payload and per-case outputs contain?

### 2) Analyze the user's Python agent

Use the helper to scan the project and find likely job entrypoints and loop-based case candidates:

```bash
python scripts/supervaize_cli_helper.py analyze-agent \
  --project-root /path/to/user-agent \
  --pretty
```

This helps identify:

- likely job entry function(s)
- loop bodies that usually map to cases
- functions with signatures that match the user workflow

### 3) Create an integration spec (interactive wizard or template)

Interactive:

```bash
python scripts/supervaize_cli_helper.py wizard --output-file integration_spec.json --pretty
```

Or generate a template and edit manually:

```bash
python scripts/supervaize_cli_helper.py spec-template --output-file integration_spec.json --pretty
```

The spec is the contract for the integration mapping (Job/Case/Step + fields + agent parameters + target function).

### 4) Scaffold `supervaizer_control.py` + `sv_main.py`

```bash
python scripts/supervaize_cli_helper.py scaffold-integration \
  --spec-file integration_spec.json \
  --output-dir /path/to/user-agent \
  --force \
  --pretty
```

Notes:

- Default controller file: `supervaizer_control.py`
- If the user's project uses a different spelling (e.g. `supervaizer_controll.py`), override with:

```bash
--controller-filename supervaizer_controll.py
```

### 5) Customize the generated files (required)

The scaffolds are intentionally structured but still require project-specific edits:

- In `sv_main.py`:
  - place the target function call at the correct step(s)
  - add type conversions for fields
  - enrich case step payloads
  - implement HITL requests where needed
  - define final payloads and error handling semantics

- In `supervaizer_control.py`:
  - refine `job_start.fields`
  - refine `ParametersSetup`
  - refine `CaseNodes` types (`STATUS_UPDATE`, `HITL`, `DELIVERABLE`, etc.)
  - verify method paths and descriptions

## Controller Utilities (After Scaffolding)

### Check envs

```bash
python scripts/supervaize_cli_helper.py env-status --pretty
python scripts/supervaize_cli_helper.py env-status --shell-template
```

### Inspect controller routes

```bash
python scripts/supervaize_cli_helper.py discover-controller \
  --controller-url http://127.0.0.1:8000 \
  --pretty
```

### Trigger a test job

```bash
python scripts/supervaize_cli_helper.py trigger-job \
  --controller-url http://127.0.0.1:8000 \
  --agent-name my_agent \
  --agent-method start \
  --user-id local-test \
  --params-json '{"fields":{"input_text":"hello"}}' \
  --dry-run \
  --pretty
```

## Key Principle

The most important integration decision is **semantic mapping**, not syntax:

- Job = one user-visible run
- Case = one repeated unit inside the run (if applicable)
- Step = one meaningful stage inside a case

If this mapping is wrong, the controller code may run but the Supervaize UI/telemetry will be misleading.
