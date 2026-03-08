# runwaize_skills

Agent skills for the Supervaize / Supervaizer ecosystem. Each subfolder is a self-contained skill that a chatbot (Claude CLI, Cursor Codex, Gemini CLI, etc.) can load and follow.

## Skills

### [`supervaizer_integration`](./supervaizer_integration/)

Integrate an **existing Python agent** with the Supervaizer controller and Supervaize SaaS.

The goal is to map the agent's workflow to the Supervaizer model:

| Concept | Meaning |
|---------|---------|
| **Job** | One end-to-end agent run |
| **Case** | One repeated unit inside the job (email, lead, document, …) |
| **Step** | A meaningful stage inside a case |

Once the mapping is defined, the skill scaffolds and customises `supervaizer_control.py` and `sv_main.py`.

→ See [`supervaizer_integration/README.md`](./supervaizer_integration/README.md)

---

### [`supervaize_access`](./supervaize_access/)

Operate against an **existing Supervaize workspace** from a chatbot or CLI agent.

Maps natural-language commands to REST / MCP / controller calls:

| Phrase | Command |
|--------|---------|
| "Register to supervaize" | `register-to-supervaize` |
| "Create a mission" | `create-mission` |
| "Start a job" | `start-job` |
| "View cases / steps" | `view-cases-steps` |
| "Show missions for this agent" | `show-missions-for-agent` |
| "Job status for this agent" | `job-status-for-agent` |

Supports three backends: Supervaize SaaS REST API, MCP HTTP endpoint, and local Supervaizer controller.

→ See [`supervaize_access/SKILL.md`](./supervaize_access/SKILL.md)

---

## When to use which skill

```
Agent code exists and needs Supervaizer instrumentation  →  supervaizer_integration
Workspace is live and you want to call/query it          →  supervaize_access
```

## Common env vars

```bash
export SUPERVAIZE_API_KEY=...
export SUPERVAIZE_WORKSPACE_ID=team_1
export SUPERVAIZE_API_URL=https://app.supervaize.com

# Optional
export SUPERVAIZE_MCP_URL=https://app.supervaize.com/w/team_1/api/mcp
export SUPERVAIZE_CONTROLLER_URL=http://127.0.0.1:8000
export CONTROLLER_AUTH_KEY=...
```

## Dependencies

```bash
pip install typer
```
