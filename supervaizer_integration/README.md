# supervaizer_integration

Skill for integrating an **existing Python agent** with the **Supervaizer controller** and Supervaize SaaS.

The primary goal is not just to start a controller. It is to correctly map the user's agent workflow to:

- **Job**: one end-to-end run
- **Case**: one repeated unit inside the job (email, phone number, doc, lead, etc.)
- **Steps**: meaningful stages inside each case

Once that mapping is clear, the skill scaffolds and helps customize:

- `supervaizer_control.py` (or `supervaizer_controll.py` if a project uses that spelling)
- `sv_main.py`

## Reference Integrations

Use these examples as models for reasoning and implementation:

- Email AI Agent (Supervaizer branch): [github.com/alain-sv/Email-AI-Agent/tree/supervaizer](https://github.com/alain-sv/Email-AI-Agent/tree/supervaizer)
- Callagen local integration:
  - `/Users/alp/GitRepo/SUPERVAIZE/9agents/callagen/supervaizer_control.py`
  - `/Users/alp/GitRepo/SUPERVAIZE/9agents/callagen/callagen/call_agent.py`
  - `/Users/alp/GitRepo/SUPERVAIZE/9agents/callagen/callagen/steps.py`

## Environment Variables (Supervaize SaaS)

```bash
export SUPERVAIZE_API_KEY=...
export SUPERVAIZE_WORKSPACE_ID=team_1
export SUPERVAIZE_API_URL=https://app.supervaize.com
```

Optional local controller auth:

```bash
export CONTROLLER_AUTH_KEY=...
```

## Helper CLI

Path:

`/Volumes/SSDext1TB/Documents/GitRepo/SUPERVAIZE/runwaize_skills/supervaizer_integration/scripts/supervaize_cli_helper.py`

Dependency:

```bash
pip install typer
```

Run commands from inside the skill folder, or use absolute paths.

## Recommended Workflow

### 1) Print the discovery questions (Job / Case / Step mapping)

```bash
python scripts/supervaize_cli_helper.py questions --pretty
```

### 2) Analyze the user's agent to find likely entrypoints and loops

```bash
python scripts/supervaize_cli_helper.py analyze-agent \
  --project-root /path/to/user-agent \
  --pretty
```

This returns candidate functions with signatures and loop hints to help determine:

- what should become the Supervaizer `job_start` target
- what repeated loop item should become a Case
- what loop stages should become Steps

### 3) Create an integration spec (interactive wizard)

```bash
python scripts/supervaize_cli_helper.py wizard \
  --output-file integration_spec.json \
  --pretty
```

Or create a template and fill it manually:

```bash
python scripts/supervaize_cli_helper.py spec-template \
  --output-file integration_spec.json \
  --pretty
```

The spec captures:

- target module/function
- job/case/step mapping
- `job_start.fields`
- `ParametersSetup` env vars/secrets
- wrapper function naming and generated filenames

### 4) Scaffold `supervaizer_control.py` and `sv_main.py`

```bash
python scripts/supervaize_cli_helper.py scaffold-integration \
  --spec-file integration_spec.json \
  --output-dir /path/to/user-agent \
  --force \
  --pretty
```

If the project expects `supervaizer_controll.py`:

```bash
python scripts/supervaize_cli_helper.py scaffold-integration \
  --spec-file integration_spec.json \
  --output-dir /path/to/user-agent \
  --controller-filename supervaizer_controll.py \
  --force
```

### 5) Customize the generated wrappers (required)

The scaffolds are a structured starting point. You must still:

- move the target function call to the correct Step(s)
- add field parsing/type conversions
- implement HITL steps where needed
- enrich case payloads and final job output
- tune `CaseNodes` types and descriptions in the controller file

## Controller Runtime Utilities

### Check env vars

```bash
python scripts/supervaize_cli_helper.py env-status --pretty
python scripts/supervaize_cli_helper.py env-status --shell-template
```

### Discover controller routes

```bash
python scripts/supervaize_cli_helper.py discover-controller \
  --controller-url http://127.0.0.1:8000 \
  --pretty
```

### Trigger a job (dry-run)

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

## Important Integration Rule

The integration is successful only when the **semantic flow is correct**:

- the Job corresponds to one real user run
- Cases represent the repeated work units users care about
- Steps represent the meaningful milestones they want to observe/approve

If needed, revisit the mapping before coding further.
