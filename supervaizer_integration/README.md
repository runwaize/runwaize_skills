# supervaizer_integration

Skill for integrating an **existing Python agent** with the **Supervaizer controller** and Supervaize SaaS.

The primary goal is to correctly map the user's agent workflow to:

- **Job**: one end-to-end run
- **Case**: one repeated unit inside the job (email, phone number, doc, lead, etc.)
- **Steps**: meaningful stages inside each case

Once that mapping is clear, the skill generates and helps customize:

- `supervaizer_control.py` — controller configuration (agent, methods, parameters, step nodes, server)
- A **workflow adapter** file — bridges Supervaizer's calling convention to the user's existing agent logic (naming fits the project: `agent_impl.py`, `sv_main.py`, or a module inside the agent's package)
- `.envrc_template` — environment variables for Supervaize platform and agent secrets
- Optionally a separate `steps.py` for complex step node definitions

## Environment Variables (Supervaize SaaS)

```bash
export SUPERVAIZE_API_KEY=...
export SUPERVAIZE_WORKSPACE_ID=team_1
export SUPERVAIZE_API_URL=https://app.supervaize.com
```

## Workflow

The skill follows a 5-phase workflow:

1. **Project Discovery & Analysis** — scan the project structure, analyze agent code, identify inputs/outputs/stages
2. **Interactive Requirements Gathering** — ask 6 question sets covering agent identity, cases & steps, data reporting, HITL, parameters, and job input fields
3. **Install Supervaizer Package** — detect package manager and install `supervaizer` with dependencies
4. **Generate Integration Files** — create controller config, workflow adapter, env template
5. **Validation & Next Steps** — verify compilation, present summary, offer further help

See `SKILL.md` for full phase-by-phase instructions and code templates.

## Helper CLI (Optional)

Path: `scripts/supervaize_cli_helper.py`

```bash
pip install typer
```

### Commands

```bash
# Print discovery questions
python scripts/supervaize_cli_helper.py questions --pretty

# Analyze agent for entrypoints and loops
python scripts/supervaize_cli_helper.py analyze-agent \
  --project-root /path/to/user-agent --pretty

# Interactive spec wizard
python scripts/supervaize_cli_helper.py wizard \
  --output-file integration_spec.json --pretty

# Generate spec template
python scripts/supervaize_cli_helper.py spec-template \
  --output-file integration_spec.json --pretty

# Scaffold controller files from spec
python scripts/supervaize_cli_helper.py scaffold-integration \
  --spec-file integration_spec.json \
  --output-dir /path/to/user-agent --force --pretty

# Check env vars
python scripts/supervaize_cli_helper.py env-status --pretty

# Discover controller routes
python scripts/supervaize_cli_helper.py discover-controller \
  --controller-url http://127.0.0.1:8000 --pretty

# Trigger a test job
python scripts/supervaize_cli_helper.py trigger-job \
  --controller-url http://127.0.0.1:8000 \
  --agent-name my_agent --agent-method start \
  --user-id local-test \
  --params-json '{"fields":{"input_text":"hello"}}' \
  --dry-run --pretty
```

## Key Principle

The most important integration decision is **semantic mapping**, not syntax:

- Job = one user-visible run
- Case = one repeated unit inside the run (if applicable)
- Step = one meaningful stage inside a case - with or without humain in the loop

If this mapping is wrong, the controller code may run but the Supervaize UI will be misleading.
