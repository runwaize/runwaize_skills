---
name: supervaizer_integration
description: Use when a user has an existing Python agent and wants to integrate the Supervaizer controller into it. This skill analyzes the agent logic, interactively gathers requirements, installs the supervaizer package, and generates fully customized controller files.
---

# Supervaizer Integration

Automate the integration of the Supervaizer Controller into any Python AI agent project. This skill analyzes the user's existing agent code, interactively gathers requirements, installs the supervaizer package, and generates the controller configuration and workflow adapter.

## When to use

Use this skill when the user wants to:
- Integrate the Supervaizer Controller into their Python AI agent
- Add Supervaize platform connectivity to an existing agent
- Set up A2A (Agent-to-Agent) protocol support for their agent
- Add human-in-the-loop workflows to their agent
- Make their agent discoverable and operable through the Supervaize platform

## Reference Integrations

Use these as real-world pattern references when reasoning about the mapping:

- **Callagen** (phone call agent with HITL): https://github.com/alain-sv/callagen
  - `supervaizer_control.py` — controller config with HITL human_answer method
  - `callagen/call_agent.py` — job lifecycle (job_start, job_stop, job_status, human_answer)
  - `callagen/steps.py` — CaseNode workflow definitions as factory functions
  - Pattern: one Case per phone number, steps for confirm → call → monitor → validate → retry

- **Email AI Agent** (LangGraph email processor): https://github.com/alain-sv/Email-AI-Agent
  - `supervaizer_control.py` — controller config with ParametersSetup for email/API secrets
  - `sv_main.py` — workflow adapter bridging Supervaize fields to LangGraph
  - Pattern: single case per email, steps for filter → summarize → respond

## Instructions

Follow these phases in order. Each phase must complete before moving to the next.

### Phase 1: Project Discovery & Analysis

1. **Scan the project structure** to understand:
   - Package manager: check for `pyproject.toml` (uv/poetry) vs `requirements.txt` (pip) vs `setup.py`
   - Web framework: check for FastAPI, Flask, Django, or no web framework
   - Existing agent code: look for Python files that implement AI agent logic (LangChain, CrewAI, AutoGen, OpenAI, Anthropic SDK, or custom)
   - Existing supervaizer integration: check if `supervaizer` is already installed or configured
   - Entry point: identify the main application file (the project will typically already have a `main.py`)

2. **Analyze the agent's workflow** by reading the main agent files:
   - What does the agent do? (summarize its purpose)
   - What are its inputs? (API keys, user prompts, configuration)
   - What are its outputs? (generated content, decisions, reports)
   - What external services does it call? (LLMs, APIs, databases)
   - Does it have distinct processing stages or steps?

   Optionally use the helper CLI for automated analysis:
   ```bash
   python scripts/supervaize_cli_helper.py analyze-agent \
     --project-root /path/to/user-agent \
     --pretty
   ```

3. **Present findings** to the user with a summary like:
   ```
   Project Analysis:
   - Package manager: [uv/pip/poetry]
   - Framework: [FastAPI/Flask/none]
   - Agent type: [LangChain/CrewAI/custom/etc.]
   - Agent purpose: [brief description]
   - Detected inputs: [list]
   - Detected outputs: [list]
   - Detected stages: [list]
   ```

### Phase 2: Interactive Requirements Gathering

Ask the user the following questions using `AskUserQuestion`. Pre-fill suggested answers based on Phase 1 analysis.

**Question Set 1 - Agent Identity:**
- Agent name and description (suggest based on code analysis)
- Author name and email
- Version string
- Tags for discoverability

**Question Set 2 - Cases & Steps:**
- "What constitutes a single 'case' in your agent's workflow?" (suggest based on detected workflow units - e.g., "processing one phone call", "handling one email", "generating one report")
- "What are the distinct steps within each case?" (suggest based on detected processing stages - e.g., "1. Parse input, 2. Call LLM, 3. Format output")
- "Can your agent process multiple cases in a single job?" (yes/no, suggest based on whether the code has loops or batch processing)

**Question Set 3 - Data Reporting:**
- "What data should be reported to the Supervaize platform at each step?" For each detected step, ask what payload data matters. Common options:
  - Input data received
  - LLM tokens used / model called
  - Intermediate results
  - Final output / deliverable
  - Error details
  - Custom metrics
- "How should costs be calculated?" Options:
  - LLM API costs (auto-detect from litellm or provider SDK)
  - Fixed cost per case
  - Custom cost calculation
  - No cost tracking

**Question Set 4 - Human-in-the-Loop:**
- "Should any step require human approval before proceeding?" (suggest based on whether the agent makes consequential decisions)
- If yes: "At which step(s) should human approval be requested?"
- If yes: "What form fields should the human see?" (Approved/Rejected booleans, free text feedback, choice selection, etc.)
- If yes: "What information should be shown to the human for their decision?" (the case payload, a summary, specific fields)

**Question Set 5 - Parameters & Secrets:**
- "What API keys or secrets does your agent need?" (auto-detect from code: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
- "What other configuration parameters should be settable from the Supervaize UI?" (auto-detect from env var usage)

**Question Set 6 - Job Input Fields:**
- "What inputs should the user provide when starting a job?" (detect from the agent's main function parameters or CLI arguments)
- For each field: name, type (CharField, IntegerField, BooleanField, ChoiceField, etc.), required (yes/no), description

### Phase 3: Install Supervaizer Package

1. **Detect the package manager** and install accordingly:

   For `pyproject.toml` (uv):
   ```bash
   # Add supervaizer to dependencies if not present
   # Then run: uv sync
   ```

   For `requirements.txt` (pip):
   ```bash
   # Add supervaizer>=0.10.23 to requirements.txt
   # Then run: pip install -r requirements.txt
   ```

   For `pyproject.toml` (poetry):
   ```bash
   poetry add supervaizer
   ```

2. **Also ensure these dependencies** are present (add if missing):
   - `fastapi>=0.128.0`
   - `loguru>=0.7.3`
   - `shortuuid`

### Phase 4: Generate Integration Files

Generate the following files, customized based on the user's answers. Do NOT generate a `main.py` — the user's project already has its own entry point.

#### 4a. `supervaizer_control.py` - Main Controller Configuration

This is the central hub. It defines the agent, its methods, parameters, account, and server. The method targets point to the workflow adapter file where the actual job logic lives.

Use this structure:
```python
import os
import shortuuid
from supervaizer import (
    Agent,
    AgentMethods,
    Server,
    Account,
    AgentMethod,
    AgentMethodField,
    CaseNode,
    CaseNodes,
    CaseNodeType,
    ParametersSetup,
    Parameter,
)

# === PARAMETERS ===
# Secrets and environment variables the agent needs (from Question Set 5)
agent_parameters = ParametersSetup.from_list([
    Parameter(name="...", description="...", is_environment=True, is_secret=True),
])

# === STEP NODES ===
# Declared step flow for the job_start method (from Question Set 2)
# Can also be defined in a separate steps.py file for complex agents
all_steps_start_method = CaseNodes(nodes=[
    CaseNode(name="Step 1", node_type=CaseNodeType.STATUS_UPDATE, description="..."),
    CaseNode(name="Step 2", node_type=CaseNodeType.DELIVERABLE, description="..."),
    # CaseNode(name="Human Review", node_type=CaseNodeType.HITL, description="..."),
])

# === METHODS ===
job_start_method = AgentMethod(
    name="start",
    method="agent_impl.job_start",  # Points to the workflow adapter
    is_async=False,
    params={"action": "start"},
    nodes=all_steps_start_method,
    fields=[
        # Generated from Question Set 6
        {"name": "input_text", "type": str, "field_type": "CharField", "required": True, "description": "..."},
    ],
)

job_stop_method = AgentMethod(
    name="stop",
    method="agent_impl.job_stop",
    is_async=False,
    params={"action": "stop"},
    description="Stop the running job",
)

job_status_method = AgentMethod(
    name="status",
    method="agent_impl.job_status",
    is_async=False,
    params={"action": "status"},
    description="Get the status of the agent",
)

# If HITL is enabled (from Question Set 4):
# human_answer_method = AgentMethod(
#     name="human_answer",
#     method="agent_impl.handle_human_input",
#     is_async=False,
#     params={"action": "human_answer"},
# )

# === AGENT ===
agent_name = "..."  # From Question Set 1
agent = Agent(
    name=agent_name,
    id=shortuuid.uuid(agent_name),
    author="...",
    version="...",
    description="...",
    tags=[...],
    methods=AgentMethods(
        job_start=job_start_method,
        job_stop=job_stop_method,
        job_status=job_status_method,
        # human_answer=human_answer_method,  # If HITL enabled
    ),
    parameters_setup=agent_parameters,
)

# === ACCOUNT ===
supervaize_account = Account(
    workspace_id=os.getenv("SUPERVAIZE_WORKSPACE_ID") or "dummy_workspace_id",
    api_key=os.getenv("SUPERVAIZE_API_KEY") or "dummy_api_key",
    api_url=os.getenv("SUPERVAIZE_API_URL") or "https://app.supervaize.com",
)

# === SERVER ===
sv_server = Server(
    agents=[agent],
    a2a_endpoints=True,
    acp_endpoints=True,
    supervisor_account=supervaize_account,
)

app = sv_server.app

if __name__ == "__main__":
    sv_server.launch(log_level="DEBUG")
```

**Notes on method targets:**
- The `method` string (e.g. `"agent_impl.job_start"`) references `<module>.<function>`.
- The module name depends on the project structure. Examples from real integrations:
  - `"sv_main.process_email_workflow"` (Email AI Agent — flat adapter file)
  - `"callagen.call_agent.call_agent_start"` (Callagen — function inside a package)
- Choose a naming convention that fits the user's existing project structure.

#### 4b. Workflow Adapter File - Job/Case/Step Logic

This file bridges Supervaizer's calling convention to the user's existing agent logic. The file name should fit the project — common patterns: `agent_impl.py`, `sv_main.py`, or a module inside the agent's package (e.g., `myagent/job_handler.py`).

**For agents with multiple cases** (like Callagen — one case per phone number):
```python
from loguru import logger as log
from supervaizer import (
    Case,
    CaseNodeUpdate,
    EntityStatus,
    JobContext,
    JobInstructions,
    JobResponse,
)
from supervaizer_control import supervaize_account

# Import the user's existing agent logic
# from myagent.core import do_work


def process_case(case_id: str, job_id: str, item, **kwargs) -> Case:
    """Process a single case through all steps."""
    case = Case.start(
        job_id=job_id,
        account=supervaize_account,
        name=f"Case {case_id}",
        description=f"Processing {item}",
    )

    # Report progress at each step via CaseNodeUpdate
    case.update(CaseNodeUpdate(
        name="Step Name",
        cost=0.0,
        payload={"input": item},
        is_final=False,
    ))

    # Call the user's existing logic here
    # result = do_work(item)

    # If HITL is needed at this step:
    # case.request_human_input(
    #     CaseNodeUpdate(name="Human Review", cost=0.0, payload={...}, is_final=False),
    #     "Please review and approve.",
    # )
    # return case  # Will be resumed by handle_human_input

    case.close(case_result={...})
    return case


def job_start(**kwargs) -> JobResponse | None:
    """Main entry point called by Supervaizer."""
    log.info(f"Agent: Received kwargs: {kwargs}")

    job_fields = kwargs.get("fields", {})
    job_context: JobContext = kwargs.get("context", {})
    job_instructions: JobInstructions | None = job_context.job_instructions
    job_id = job_context.job_id

    cases = 0
    cost = 0.0

    # Extract items to process from fields
    # items = parse_items(job_fields.get("input_field"))

    for i, item in enumerate(items):
        # Check job instructions (max_cases, max_cost, stop_on_error)
        check, explanation = (
            job_instructions.check(cases=cases, cost=cost)
            if job_instructions
            else (True, "No conditions")
        )
        if not check:
            log.warning(f"Agent: STOPPING JOB: {explanation}")
            break

        try:
            case_result = process_case(case_id=f"C{i+1}", job_id=job_id, item=item, **kwargs)
            cost += getattr(case_result, "cost", 0.0)
            cases += 1
        except Exception as e:
            log.error(f"Agent: Error on case C{i+1}: {e}")
            if job_instructions and job_instructions.stop_on_error:
                raise

    return JobResponse(
        job_id=job_id,
        status=EntityStatus.COMPLETED,
        message=f"Processed {cases} cases",
        payload={"total_cases": cases, "total_cost": cost},
        cost=cost,
    )
```

**For agents with a single case** (like Email AI Agent — one email per job):
```python
def job_start(fields=None, context=None, agent_parameters=None, **kwargs):
    """Workflow adapter — bridges Supervaize fields to agent logic."""
    # Extract user-provided fields
    user_input = fields.get("input_text", "")

    # Call the user's existing agent logic directly
    # result = existing_agent_function(user_input)

    return {
        "status": "completed",
        "result": result,
    }
```

**Always include stop and status handlers:**
```python
def job_stop(**kwargs) -> None:
    """Called when the platform requests to stop the running job."""
    job_context = kwargs.get("context") or {}
    job_id = getattr(job_context, "job_id", None) or (
        job_context.get("job_id") if isinstance(job_context, dict) else None
    )
    log.info(f"Agent: job_stop requested for job_id={job_id}")


def job_status(**kwargs):
    """Return current agent status."""
    job_context = kwargs.get("context") or {}
    job_id = getattr(job_context, "job_id", None) or (
        job_context.get("job_id") if isinstance(job_context, dict) else None
    )
    return {"status": "idle", "job_id": job_id}
```

#### 4c. Step Definitions (Optional Separate File)

For agents with complex step workflows (like Callagen), define step node functions in a separate `steps.py`:

```python
from supervaizer import CaseNode, CaseNodes, CaseNodeType, CaseNodeUpdate

# Define CaseNode declarations (used in supervaizer_control.py)
all_steps_start_method = CaseNodes(nodes=[
    CaseNode(name="confirm_action", node_type=CaseNodeType.HITL, description="Confirm before proceeding"),
    CaseNode(name="execute", node_type=CaseNodeType.STATUS_UPDATE, description="Execute main action"),
    CaseNode(name="deliver_result", node_type=CaseNodeType.DELIVERABLE, description="Final result"),
])

# Define step factory functions (called in the workflow adapter)
def confirm_action(item, **kwargs) -> CaseNodeUpdate:
    return CaseNodeUpdate(
        name=f"Confirm action for {item}",
        cost=0.0,
        payload={"item": item, "supervaizer_form": {...}},
        is_final=False,
    )

def execute(item, result, **kwargs) -> CaseNodeUpdate:
    return CaseNodeUpdate(
        name=f"Executing for {item}",
        cost=result.get("cost", 0.0),
        payload={"status": "in_progress", "item": item},
        is_final=False,
    )

def deliver_result(item, result, **kwargs) -> CaseNodeUpdate:
    return CaseNodeUpdate(
        name=f"Result for {item}",
        cost=0.0,
        payload=result,
        is_final=True,
    )
```

#### 4d. `.envrc_template` - Environment Variables

Generate with all required environment variables:
```bash
# Supervaize platform credentials
export SUPERVAIZE_API_URL=https://app.supervaize.com
export SUPERVAIZE_API_KEY=GET_FROM_APP.SUPERVAIZE.COM
export SUPERVAIZE_WORKSPACE_ID=your_workspace_slug

# Controller server settings
export SUPERVAIZER_HOST=localhost
export SUPERVAIZER_PORT=8000
export SUPERVAIZER_SCHEME=http
export SUPERVAIZER_PUBLIC_URL=http://localhost:8000
export SUPERVAIZER_SERVER_ID=TBD
export SUPERVAIZER_PRIVATE_KEY=TBD

# Agent-specific secrets (from Question Set 5)
# export OPENAI_API_KEY=...
# export RETELL_API_KEY=...
```

### Phase 5: Validation & Next Steps

1. **Verify the generated files** compile correctly:
   ```bash
   python -c "import supervaizer_control"
   ```

2. **Present a summary** to the user:
   ```
   Supervaizer Controller Integration Complete!

   Files created/modified:
   - supervaizer_control.py (controller configuration)
   - <workflow_adapter>.py (job/case/step implementation)
   - .envrc_template (environment variables)
   - pyproject.toml / requirements.txt (dependencies updated)

   Next steps:
   1. Create your developer account at https://app.supervaize.com
   2. Generate an API key and get your workspace ID
   3. Fill in the environment variables in .envrc_template (or copy to .envrc)
   4. Run: supervaizer start (or python supervaizer_control.py)
   5. Verify at http://localhost:8000/docs
   6. For production: supervaizer deploy up
   ```

3. **Offer to help** with:
   - Customizing the case processing logic further
   - Adding additional agents
   - Setting up deployment (GCP, AWS, DigitalOcean)
   - Adding more human-in-the-loop steps

## Helper CLI (Optional)

The skill includes an optional Typer-based CLI helper for automated analysis and scaffolding.

File: `scripts/supervaize_cli_helper.py`

```bash
pip install typer
```

Available commands:
- `questions` — Print discovery questions for Job/Case/Step mapping
- `spec-template` — Generate integration spec template
- `wizard` — Interactive integration spec creation
- `analyze-agent` — Scan project for entrypoint functions
- `scaffold-integration` — Generate controller files from spec
- `env-status` — Check/template SUPERVAIZE_* env vars
- `discover-controller` — Inspect controller OpenAPI spec
- `trigger-job` — POST job request to controller

## Key Supervaizer Concepts Reference

### Entity Hierarchy
- **Server** -> hosts multiple **Agents**
- **Agent** -> receives **Jobs** (from the Supervaize platform)
- **Job** -> contains multiple **Cases** (units of work)
- **Case** -> has **Steps** (CaseNodeUpdate) that are either informational or human-in-the-loop

### Required Agent Methods
- `job_start(**kwargs)` -> `JobResponse` - Main execution entry point
- `job_stop(**kwargs)` -> `None` - Graceful stop handler
- `job_status(**kwargs)` -> `dict` - Status reporting

### Optional Agent Methods
- `human_answer(**kwargs)` -> `JobResponse` - Process human decisions
- `chat(**kwargs)` - Chat-style interaction
- `custom` methods - Any additional custom methods

### Job kwargs Structure
```python
kwargs = {
    "fields": {...},              # User-provided job input fields
    "context": JobContext,         # job_id, mission_id, workspace info, job_instructions
    "agent_parameters": {...},     # Injected secrets/env vars from Supervaize
}
```

`JobContext` provides:
- `job_id` — unique identifier for this job run
- `job_instructions` — `JobInstructions` object with `max_cost`, `max_cases`, `stop_on_error`
- `job_instructions.check(cases=N, cost=X)` — returns `(bool, explanation)` to enforce limits

### CaseNodeUpdate (Step) Fields
```python
CaseNodeUpdate(
    name="Step Name",          # Human-readable step name
    cost=0.0,                  # Cost incurred at this step
    payload={...},             # Data to report to the platform
    is_final=False,            # True if this is the last step
    error=None,                # Error message if step failed
)
```

### CaseNode Types (for step declarations in supervaizer_control.py)
- `STATUS_UPDATE` — Progress indicator
- `DELIVERABLE` — Final or intermediate output
- `HITL` — Human-in-the-loop decision point
- `INTERMEDIARY_DELIVERY` — Intermediate data snapshot
- `ERROR` — Error state
- `INFO` — Informational display

### Human-in-the-Loop Pattern

Request human input during case processing:
```python
case.request_human_input(
    CaseNodeUpdate(
        name="Human Review",
        cost=0.0,
        payload={
            "supervaizer_form": {
                "question": "Review and approve this case",
                "answer": {
                    "fields": [
                        {"name": "Approved", "type": bool, "field_type": "BooleanField", "required": False},
                        {"name": "Feedback", "type": str, "field_type": "CharField", "required": False},
                    ]
                }
            }
        },
        is_final=False,
    ),
    "Please review and approve.",
)
```

Receive human response:
```python
response = case.receive_human_input()
approved = response.get("Approved", False)
```

### AgentMethodField Types
- `CharField` - Text input
- `IntegerField` - Integer input
- `BooleanField` - True/False toggle
- `ChoiceField` - Single selection dropdown
- `MultipleChoiceField` - Multi-select
- `JSONField` - Raw JSON input

## Key Principle

The most important integration decision is **semantic mapping**, not syntax:

- Job = one user-visible run
- Case = one repeated unit inside the run (if applicable)
- Step = one meaningful stage inside a case

If this mapping is wrong, the controller code may run but the Supervaize UI/telemetry will be misleading.
