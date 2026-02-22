#!/usr/bin/env python3
"""Helper for integrating an existing Python agent with the Supervaizer controller."""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import typer


DEFAULT_TIMEOUT = 30
SUPERVAIZE_ENV_VARS = (
    "SUPERVAIZE_API_KEY",
    "SUPERVAIZE_WORKSPACE_ID",
    "SUPERVAIZE_API_URL",
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Integration helper for wiring an existing Python agent into the Supervaizer controller.",
)


def _print_json(data: dict[str, Any] | list[Any], pretty: bool = False) -> None:
    if pretty:
        print(json.dumps(data, indent=2, sort_keys=True))
        return
    print(json.dumps(data, separators=(",", ":"), sort_keys=True))


def _mask_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _normalize_controller_url(url: str) -> str:
    return url.rstrip("/")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "value"


def _module_from_filename(filename: str) -> str:
    return Path(filename).stem


def _read_json_file(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise ValueError(f"Refusing to overwrite existing file without --force: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_params(params_json: str | None, params_file: str | None) -> dict[str, Any]:
    if params_file:
        payload = _read_json_file(params_file)
    elif params_json:
        payload = json.loads(params_json)
    else:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("params payload must be a JSON object")
    return payload


def _controller_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _http_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, Any]:
    raw = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url=url, data=raw, method=method.upper())
    for key, value in (headers or {}).items():
        request.add_header(key, value)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            if not text.strip():
                return response.status, None
            try:
                return response.status, json.loads(text)
            except json.JSONDecodeError:
                return response.status, {"raw_text": text}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(text) if text else None
        except json.JSONDecodeError:
            payload = {"raw_text": text}
        raise RuntimeError(json.dumps({"status": exc.code, "url": url, "error": payload})) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(json.dumps({"url": url, "error": str(exc.reason)})) from exc


def _handle(pretty: bool, fn: Any, *args: Any, **kwargs: Any) -> None:
    try:
        fn(*args, **kwargs)
    except json.JSONDecodeError as exc:
        _print_json({"ok": False, "error": f"Invalid JSON input: {exc.msg}", "position": exc.pos}, pretty=pretty)
        raise typer.Exit(code=2)
    except ValueError as exc:
        _print_json({"ok": False, "error": str(exc)}, pretty=pretty)
        raise typer.Exit(code=2)
    except RuntimeError as exc:
        try:
            payload = json.loads(str(exc))
        except json.JSONDecodeError:
            payload = {"error": str(exc)}
        _print_json({"ok": False, **payload}, pretty=pretty)
        raise typer.Exit(code=1)
    except Exception as exc:
        _print_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, pretty=pretty)
        raise typer.Exit(code=1)


def _questions_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "questions",
        "goal": "Identify the correct Job, Case, and Step boundaries before writing Supervaizer integration code.",
        "questions": [
            {
                "id": "agent_entrypoint",
                "category": "Target Function",
                "question": "What Python function should Supervaizer call to start the agent workflow (module path + function)?",
                "why": "This becomes the `job_start` method target and the wrapper call in `sv_main.py`.",
            },
            {
                "id": "job_definition",
                "category": "Job Mapping",
                "question": "What does one invocation represent in business terms (the Job)?",
                "why": "The Job should match a single user-visible run in Supervaize.",
            },
            {
                "id": "case_definition",
                "category": "Case Mapping",
                "question": "Does one job process multiple items? If yes, what is the per-item unit (email, phone number, document, lead, etc.)?",
                "why": "Each repeated item is usually one Case.",
            },
            {
                "id": "case_source_field",
                "category": "Case Mapping",
                "question": "Which input field contains the case items (e.g., `emails`, `phone_numbers`) and how is it encoded (CSV/list/single)?",
                "why": "Used to build the case loop in `sv_main.py`.",
            },
            {
                "id": "step_list",
                "category": "Flow Mapping",
                "question": "What are the ordered steps inside each case (fetch, parse, classify, generate, send, review, etc.)?",
                "why": "These become Supervaizer case nodes and runtime case updates.",
            },
            {
                "id": "human_in_the_loop",
                "category": "Flow Mapping",
                "question": "Where do humans approve/review/answer? Which steps are HITL?",
                "why": "HITL steps should use a compatible node type and request/receive human input.",
            },
            {
                "id": "start_fields",
                "category": "UI Fields",
                "question": "Which user-provided inputs should appear in the Supervaize job start form (fields, types, defaults, required)?",
                "why": "These become `job_start.fields` in `supervaizer_control.py`.",
            },
            {
                "id": "agent_parameters",
                "category": "Secrets / Env",
                "question": "Which environment variables/secrets should be requested as agent parameters (API keys, credentials, endpoints)?",
                "why": "These become `ParametersSetup` and can be injected into env at runtime.",
            },
            {
                "id": "function_param_mapping",
                "category": "Function Mapping",
                "question": "How do `fields` map to the target function parameters (including type conversion)?",
                "why": "This determines the wrapper call signature and prevents runtime mismatches.",
            },
            {
                "id": "result_payload",
                "category": "Outputs",
                "question": "What should the final JobResponse payload contain, and what per-case result should be attached when closing cases?",
                "why": "Defines the observability/output contract for Supervaize UI and downstream consumers.",
            },
        ],
    }


def _spec_template() -> dict[str, Any]:
    return {
        "project": {
            "name": "my_agent_project",
            "output_dir": ".",
            "controller_filename": "supervaizer_control.py",
            "workflow_filename": "sv_main.py",
        },
        "integration": {
            "agent_slug": "my_agent",
            "agent_display_name": "My Agent",
            "agent_description": "Describe the agent's purpose for Supervaize users.",
            "workflow_wrapper_function": "process_my_agent_workflow",
            "job_start_description": "Describe what the start job does.",
        },
        "target_agent": {
            "module": "my_agent.main",
            "function": "run_workflow",
            "kwargs_from_fields": ["input_text"],
            "case_item_param": None,
        },
        "job_mapping": {
            "job_definition": "One execution processes a user request end-to-end.",
            "case_strategy": "single_case",
            "case_collection_field": None,
            "case_items_format": "single",
            "case_item_label": "item",
            "case_name_prefix": "Case",
            "case_description_template": "Process one case item",
        },
        "steps": [
            {
                "id": "prepare",
                "name": "Prepare Inputs",
                "description": "Validate and normalize inputs.",
                "type": "STATUS_UPDATE",
            },
            {
                "id": "execute",
                "name": "Run Agent Logic",
                "description": "Call the existing Python agent function.",
                "type": "STATUS_UPDATE",
            },
            {
                "id": "finalize",
                "name": "Finalize Result",
                "description": "Prepare final payload and close the case.",
                "type": "DELIVERABLE",
            },
        ],
        "start_fields": [
            {
                "name": "input_text",
                "type": "str",
                "field_type": "CharField",
                "required": True,
                "description": "Primary user input",
            }
        ],
        "agent_parameters": [
            {
                "name": "EXAMPLE_API_KEY",
                "description": "API key used by the agent",
                "is_environment": True,
                "is_secret": True,
            }
        ],
        "supervaize_env": {
            "workspace_id_env": "SUPERVAIZE_WORKSPACE_ID",
            "api_key_env": "SUPERVAIZE_API_KEY",
            "api_url_env": "SUPERVAIZE_API_URL",
        },
        "notes": {
            "job_case_step_mapping": "Replace with your concrete mapping before scaffolding.",
            "hitl_steps": [],
        },
    }


def _parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _wizard_impl(output_file: str, pretty: bool) -> None:
    typer.echo("Supervaizer Integration Wizard (existing Python agent -> Supervaizer controller)")
    project_name = typer.prompt("Project name", default="my_agent_project")
    agent_slug = _slug(typer.prompt("Agent slug (machine name)", default="my_agent"))
    agent_display_name = typer.prompt("Agent display name", default=agent_slug.replace("_", " ").title())
    agent_description = typer.prompt("Agent description", default="Existing Python agent integrated with Supervaizer")

    target_module = typer.prompt("Target agent module (dotted path)", default=f"{agent_slug}.main")
    target_function = typer.prompt("Target agent function name", default="run_workflow")
    kwargs_from_fields_csv = typer.prompt(
        "Target function kwargs sourced from job fields (comma-separated)",
        default="input_text",
    )

    job_definition = typer.prompt(
        "What is one Job (business meaning)?",
        default="One end-to-end agent execution",
    )
    case_strategy = typer.prompt(
        "Case strategy (single_case/per_item)",
        default="single_case",
    ).strip()
    case_collection_field = None
    case_items_format = "single"
    case_item_label = "item"
    case_item_param = None
    if case_strategy == "per_item":
        case_collection_field = typer.prompt("Field containing case items", default="items")
        case_items_format = typer.prompt("Case items format (csv/list/single)", default="csv")
        case_item_label = typer.prompt("Per-case item label", default="item")
        case_item_param = typer.prompt(
            "Target function kwarg name for the current case item (blank to skip)",
            default=case_item_label,
        ).strip() or None

    steps_csv = typer.prompt(
        "Ordered per-case steps (comma-separated)",
        default="prepare,execute,finalize",
    )
    start_fields_csv = typer.prompt(
        "Job start form fields (comma-separated, default all string required)",
        default=kwargs_from_fields_csv,
    )
    agent_params_csv = typer.prompt(
        "Agent parameter env vars/secrets (comma-separated, blank if none)",
        default="",
        show_default=False,
    )

    steps: list[dict[str, Any]] = []
    step_names = _parse_csv_list(steps_csv)
    for idx, step in enumerate(step_names):
        step_id = _slug(step)
        default_type = "DELIVERABLE" if idx == len(step_names) - 1 else "STATUS_UPDATE"
        steps.append(
            {
                "id": step_id,
                "name": step.replace("_", " ").title(),
                "description": f"{step.replace('_', ' ').title()} step",
                "type": default_type,
            }
        )

    start_fields = [
        {
            "name": field,
            "type": "str",
            "field_type": "CharField",
            "required": True,
            "description": f"Input field: {field}",
        }
        for field in _parse_csv_list(start_fields_csv)
    ]

    agent_parameters = [
        {
            "name": name,
            "description": f"{name} environment variable",
            "is_environment": True,
            "is_secret": True if name.endswith("KEY") or "PASSWORD" in name else False,
        }
        for name in _parse_csv_list(agent_params_csv)
    ]

    spec = _spec_template()
    spec["project"]["name"] = project_name
    spec["integration"].update(
        {
            "agent_slug": agent_slug,
            "agent_display_name": agent_display_name,
            "agent_description": agent_description,
            "workflow_wrapper_function": f"process_{agent_slug}_workflow",
            "job_start_description": job_definition,
        }
    )
    spec["target_agent"].update(
        {
            "module": target_module,
            "function": target_function,
            "kwargs_from_fields": _parse_csv_list(kwargs_from_fields_csv),
            "case_item_param": case_item_param,
        }
    )
    spec["job_mapping"].update(
        {
            "job_definition": job_definition,
            "case_strategy": case_strategy,
            "case_collection_field": case_collection_field,
            "case_items_format": case_items_format,
            "case_item_label": case_item_label,
            "case_name_prefix": case_item_label.replace("_", " ").title(),
            "case_description_template": f"Process one {case_item_label}",
        }
    )
    spec["steps"] = steps
    spec["start_fields"] = start_fields
    spec["agent_parameters"] = agent_parameters
    spec["notes"]["job_case_step_mapping"] = (
        "Review this mapping carefully. Confirm the Job, each Case boundary, and the exact ordered Steps before scaffolding."
    )

    out_path = Path(output_file)
    _write_text(out_path, json.dumps(spec, indent=2) + "\n", force=True)
    _print_json(
        {
            "ok": True,
            "operation": "wizard",
            "spec_file": str(out_path),
            "next_steps": [
                "Review and edit the generated spec (especially job_mapping, steps, start_fields, and agent_parameters).",
                "Run analyze-agent on the target project if you need help choosing the target function.",
                "Run scaffold-integration with this spec to generate supervaizer_control.py and sv_main.py.",
            ],
            "spec": spec if pretty else None,
        },
        pretty=pretty,
    )


def _default_field_type(field_type_name: str) -> str:
    mapping = {
        "str": "CharField",
        "int": "IntegerField",
        "float": "FloatField",
        "bool": "BooleanField",
        "list[str]": "JSONField",
        "dict": "JSONField",
    }
    return mapping.get(field_type_name, "CharField")


def _python_type_expr(type_name: str) -> str:
    mapping = {
        "str": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "dict": "dict",
        "list": "list",
        "list[str]": "str",
    }
    return mapping.get(type_name, "str")


def _render_field_dict(field: dict[str, Any]) -> str:
    parts: list[str] = []
    name = field["name"]
    type_name = str(field.get("type", "str"))
    field_type = field.get("field_type") or _default_field_type(type_name)
    parts.append(f'"name": {name!r}')
    parts.append(f'"type": {_python_type_expr(type_name)}')
    parts.append(f'"field_type": {field_type!r}')
    if "description" in field:
        parts.append(f'"description": {str(field.get("description", ""))!r}')
    parts.append(f'"required": {bool(field.get("required", False))!r}')
    if "default" in field and field.get("default") is not None:
        parts.append(f'"default": {field["default"]!r}')
    if "choices" in field and field.get("choices"):
        parts.append(f'"choices": {field["choices"]!r}')
    return "{" + ", ".join(parts) + "}"


def _render_parameter_block(param: dict[str, Any]) -> str:
    return textwrap.indent(
        textwrap.dedent(
            f"""\
            Parameter(
                name={param['name']!r},
                description={str(param.get('description', param['name']))!r},
                is_environment={bool(param.get('is_environment', True))!r},
                is_secret={bool(param.get('is_secret', False))!r},
            ),
            """
        ).rstrip(),
        "    ",
    )


def _render_step_node(step: dict[str, Any]) -> str:
    step_id = _slug(str(step["id"]))
    step_name = str(step.get("name") or step_id.replace("_", " ").title())
    step_desc = str(step.get("description") or step_name)
    step_type = str(step.get("type", "STATUS_UPDATE")).upper()
    return textwrap.indent(
        textwrap.dedent(
            f"""\
            CaseNode(
                name={step_id!r},
                description={step_desc!r},
                type=CaseNodeType.{step_type},
                factory=lambda **payload: CaseNodeUpdate(
                    name={step_name!r},
                    payload=(payload or None),
                    is_final=False,
                ),
            ),
            """
        ).rstrip(),
        "    ",
    )


def _render_controller_py(spec: dict[str, Any], controller_filename: str, workflow_filename: str) -> str:
    integration = spec["integration"]
    target = spec["target_agent"]
    project = spec["project"]
    job_mapping = spec["job_mapping"]
    steps = spec.get("steps", [])
    start_fields = spec.get("start_fields", [])
    agent_parameters = spec.get("agent_parameters", [])
    envs = spec.get("supervaize_env", {})

    workflow_module = _module_from_filename(workflow_filename)
    workflow_fn = integration.get("workflow_wrapper_function", f"process_{_slug(integration['agent_slug'])}_workflow")
    agent_slug = _slug(integration["agent_slug"])

    params_block = "\n".join(_render_parameter_block(p) for p in agent_parameters) if agent_parameters else "    # No agent parameters defined yet. Add Parameter(...) entries here."
    fields_block = (
        ",\n        ".join(_render_field_dict(f) for f in start_fields)
        if start_fields
        else '{"name": "input_text", "type": str, "field_type": "CharField", "required": True, "description": "Primary input"}'
    )
    nodes_block = "\n".join(_render_step_node(s) for s in steps) if steps else "    # Add CaseNode(...) definitions for the per-case step flow."

    workspace_env = envs.get("workspace_id_env", "SUPERVAIZE_WORKSPACE_ID")
    api_key_env = envs.get("api_key_env", "SUPERVAIZE_API_KEY")
    api_url_env = envs.get("api_url_env", "SUPERVAIZE_API_URL")

    notes = f"""# Generated by supervaizer_integration helper.
# Review and customize:
# - `agent_parameters` (runtime secrets/envs requested by Supervaize)
# - `job_start_method.fields` (UI form inputs)
# - `all_steps_start_method` (declared case-step flow)
# - method target `{workflow_module}.{workflow_fn}` in `{workflow_filename}`
#
# Job mapping: {job_mapping.get('job_definition', '')}
# Case strategy: {job_mapping.get('case_strategy', 'single_case')}
# Target agent call: {target.get('module')}.{target.get('function')}
"""

    return textwrap.dedent(
        f"""\
        {notes}
        import os

        from supervaizer import (
            Account,
            Agent,
            AgentMethod,
            AgentMethods,
            CaseNode,
            CaseNodes,
            CaseNodeType,
            CaseNodeUpdate,
            Parameter,
            ParametersSetup,
            Server,
        )


        agent_parameters = ParametersSetup.from_list([
        {params_block}
        ])


        all_steps_start_method = CaseNodes(nodes=[
        {nodes_block}
        ])


        job_start_method = AgentMethod(
            name="start",
            method={f"{workflow_module}.{workflow_fn}"!r},
            is_async=False,
            params={{}},
            nodes=all_steps_start_method,
            fields=[
                {fields_block}
            ],
            description={repr(str(integration.get('job_start_description') or integration.get('agent_description') or ''))},
        )

        job_stop_method = AgentMethod(
            name="stop",
            method={f"{workflow_module}.stop"!r},
            is_async=False,
            description="Stop the running job (placeholder wrapper)",
        )

        job_status_method = AgentMethod(
            name="status",
            method={f"{workflow_module}.check_status"!r},
            is_async=False,
            description="Return job status (placeholder wrapper)",
        )


        agent = Agent(
            name={repr(str(integration.get('agent_display_name') or agent_slug))},
            description={repr(str(integration.get('agent_description') or ''))},
            methods=AgentMethods(
                job_start=job_start_method,
                job_stop=job_stop_method,
                job_status=job_status_method,
                chat=None,
                custom=None,
            ),
            parameters_setup=agent_parameters,
        )


        account = Account(
            workspace_id=os.getenv({workspace_env!r}) or "dummy_workspace_id",
            api_key=os.getenv({api_key_env!r}) or "dummy_api_key",
            api_url=os.getenv({api_url_env!r}) or "https://app.supervaize.com",
        )


        server = Server(
            agents=[agent],
            a2a_endpoints=True,
            acp_endpoints=True,
            supervisor_account=account,
        )


        if __name__ == "__main__":
            server.launch(log_level="DEBUG")
        """
    )


def _safe_identifier(name: str) -> str:
    ident = _slug(name)
    if ident and ident[0].isdigit():
        ident = f"x_{ident}"
    return ident


def _render_sv_main_py(spec: dict[str, Any], controller_filename: str, workflow_filename: str) -> str:
    integration = spec["integration"]
    target = spec["target_agent"]
    job_mapping = spec["job_mapping"]
    steps = spec.get("steps", [])

    controller_module = _module_from_filename(controller_filename)
    target_module = str(target["module"])
    target_fn = str(target["function"])
    wrapper_fn = str(integration.get("workflow_wrapper_function") or f"process_{_slug(integration['agent_slug'])}_workflow")
    case_strategy = str(job_mapping.get("case_strategy", "single_case"))
    case_collection_field = job_mapping.get("case_collection_field")
    case_items_format = str(job_mapping.get("case_items_format", "single"))
    case_item_label = str(job_mapping.get("case_item_label") or "item")
    case_name_prefix = str(job_mapping.get("case_name_prefix") or case_item_label.title())
    case_desc_tmpl = str(job_mapping.get("case_description_template") or "Process one case")
    kwargs_from_fields = [str(x) for x in target.get("kwargs_from_fields", [])]
    case_item_param = target.get("case_item_param")

    step_defs_literal = [
        {
            "id": _slug(str(step.get("id") or step.get("name") or "step")),
            "name": str(step.get("name") or step.get("id") or "Step"),
            "description": str(step.get("description") or ""),
        }
        for step in steps
    ] or [
        {"id": "execute", "name": "Run Agent Logic", "description": "Execute target function"}
    ]

    target_kwargs_lines = [f"        \"{name}\": fields.get({name!r})," for name in kwargs_from_fields]
    if case_item_param:
        target_kwargs_lines.append(f"        \"{case_item_param}\": case_item,")
    if not target_kwargs_lines:
        target_kwargs_lines = ["        # Add target function kwargs mapping from `fields` here."]
    target_kwargs_block = "\n".join(target_kwargs_lines)

    step_emissions = []
    for idx, step in enumerate(step_defs_literal):
        call_hint = "  # TODO: place/keep target function call around the correct step" if idx == 0 else ""
        step_emissions.append(
            textwrap.dedent(
                f"""\
                    _emit_case_step(
                        case,
                        step_id={step['id']!r},
                        step_name={step['name']!r},
                        payload={{"description": {step['description']!r}}},
                    ){call_hint}
                """
            ).rstrip()
        )
    steps_block = "\n\n".join(step_emissions)
    indented_steps_block = textwrap.indent(steps_block, " " * 24) if steps_block else "                        pass"

    guidance = f"""# Generated by supervaizer_integration helper.
# Customize this file to map your existing agent logic to Supervaizer runtime semantics.
#
# Job: {job_mapping.get('job_definition', '')}
# Case strategy: {case_strategy}
# Case source field: {case_collection_field!r}
# Case item format: {case_items_format}
# Steps: {[s['id'] for s in step_defs_literal]}
#
# Most important work:
# 1) Confirm what one Job is for your agent
# 2) Confirm what each Case represents (if any)
# 3) Place the target function call at the right Step(s)
# 4) Enrich case updates with payloads and HITL where needed
"""

    return textwrap.dedent(
        f"""\
        {guidance}
        from __future__ import annotations

        import os
        import re
        from datetime import datetime
        from typing import Any

        from supervaizer import Case, CaseNodeUpdate
        from supervaizer.job import EntityStatus, JobContext, JobResponse

        from {controller_module} import account
        from {target_module} import {target_fn} as target_agent_function


        CASE_STRATEGY = {case_strategy!r}
        CASE_COLLECTION_FIELD = {case_collection_field!r}
        CASE_ITEMS_FORMAT = {case_items_format!r}
        CASE_ITEM_LABEL = {case_item_label!r}
        CASE_NAME_PREFIX = {case_name_prefix!r}
        CASE_DESCRIPTION_TEMPLATE = {case_desc_tmpl!r}
        FLOW_STEPS = {step_defs_literal!r}


        def _safe_case_id(value: str) -> str:
            safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value)).strip("_").lower()
            return safe or "case"


        def _as_job_context(context_raw: Any) -> JobContext:
            if isinstance(context_raw, JobContext):
                return context_raw
            if isinstance(context_raw, dict):
                return JobContext(**context_raw)
            raise ValueError(f"context must be dict or JobContext, got {{type(context_raw)}}")


        def _apply_agent_parameters(agent_parameters: list[dict[str, Any]] | None) -> None:
            for param in agent_parameters or []:
                name = param.get("name")
                value = param.get("value")
                if name and value is not None:
                    os.environ[str(name)] = str(value)


        def _coerce_case_items(fields: dict[str, Any]) -> list[Any]:
            if CASE_STRATEGY != "per_item":
                return [None]
            raw = fields.get(CASE_COLLECTION_FIELD) if CASE_COLLECTION_FIELD else None
            if raw is None:
                return []
            if CASE_ITEMS_FORMAT == "list" and isinstance(raw, list):
                return raw
            if CASE_ITEMS_FORMAT == "csv" and isinstance(raw, str):
                return [part.strip() for part in raw.split(",") if part.strip()]
            if CASE_ITEMS_FORMAT == "single":
                return [raw]
            if isinstance(raw, list):
                return raw
            if isinstance(raw, str):
                return [part.strip() for part in raw.split(",") if part.strip()] or [raw]
            return [raw]


        def _emit_case_step(case: Case, step_id: str, step_name: str, payload: dict[str, Any] | None = None) -> None:
            case.update(
                CaseNodeUpdate(
                    name=step_name,
                    payload={{
                        "step_id": step_id,
                        **(payload or {{}}),
                    }},
                    is_final=False,
                )
            )


        def {wrapper_fn}(**kwargs: Any) -> JobResponse:
            # Supervaizer job wrapper around the existing Python agent.
            job_context = None
            try:
                fields = kwargs.get("fields", {{}}) or {{}}
                _apply_agent_parameters(kwargs.get("agent_parameters", []))
                job_context = _as_job_context(kwargs.get("context"))
                case_items = _coerce_case_items(fields)
                if CASE_STRATEGY == "per_item" and not case_items:
                    raise ValueError(
                        f"No case items found in field {{CASE_COLLECTION_FIELD!r}}. Update the job_mapping/case field mapping."
                    )

                all_results: list[dict[str, Any]] = []

                # Single-case flows still use one case so the user gets step-level observability.
                if CASE_STRATEGY != "per_item":
                    case_items = [None]

                for idx, case_item in enumerate(case_items, start=1):
                    if case_item is None:
                        case_name = f"{{CASE_NAME_PREFIX}}"
                        case_desc = CASE_DESCRIPTION_TEMPLATE
                        case_id = f"{{_safe_case_id(CASE_NAME_PREFIX)}}_{{idx}}"
                    else:
                        case_name = f"{{CASE_NAME_PREFIX}}: {{case_item}}"
                        case_desc = f"{{CASE_DESCRIPTION_TEMPLATE}} ({{CASE_ITEM_LABEL}}={{case_item}})"
                        case_id = f"{{_safe_case_id(CASE_NAME_PREFIX)}}_{{_safe_case_id(str(case_item))}}"

                    case = Case.start(
                        job_id=job_context.job_id,
                        account=account,
                        name=case_name,
                        description=case_desc,
                        case_id=case_id,
                    )

                    try:
{indented_steps_block}

                        target_kwargs = {{
{target_kwargs_block}
                        }}

                        # Remove None values by default; keep/adjust this behavior if None is meaningful.
                        target_kwargs = {{k: v for k, v in target_kwargs.items() if v is not None}}

                        # TODO: Add type conversions here (e.g., int/float/bool parsing) based on your field schema.
                        result = target_agent_function(**target_kwargs)

                        case_result = {{
                            "status": "completed",
                            "case_item": case_item,
                            "result": result,
                        }}
                        case.close(case_result=case_result, final_cost=0.0)
                        all_results.append(case_result)
                    except Exception as case_error:
                        case.close(
                            case_result={{
                                "status": "failed",
                                "case_item": case_item,
                                "error": str(case_error),
                            }},
                            final_cost=0.0,
                        )
                        raise

                return JobResponse(
                    job_id=job_context.job_id,
                    status=EntityStatus.COMPLETED,
                    message="Job completed",
                    payload={{
                        "case_count": len(all_results),
                        "results": all_results,
                    }},
                )

            except Exception as exc:
                return JobResponse(
                    job_id=(job_context.job_id if job_context else "unknown"),
                    status=EntityStatus.FAILED,
                    message=f"Job failed: {{exc}}",
                    payload={{"error": str(exc)}},
                    error=str(exc),
                )


        def stop() -> dict[str, Any]:
            return {{
                "status": "stopped",
                "timestamp": datetime.now().isoformat(),
                "message": "Implement project-specific stop behavior in sv_main.py",
            }}


        def check_status() -> dict[str, Any]:
            return {{
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "message": "Implement project-specific status behavior in sv_main.py",
            }}
        """
    )


def _load_and_validate_spec(spec_file: str | Path) -> dict[str, Any]:
    spec = _read_json_file(spec_file)
    if not isinstance(spec, dict):
        raise ValueError("Spec file must be a JSON object")
    for key in ["project", "integration", "target_agent", "job_mapping"]:
        if key not in spec:
            raise ValueError(f"Spec file missing required top-level key: {key}")
    return spec


def _scaffold_integration_impl(
    *,
    spec_file: str,
    output_dir: str | None,
    controller_filename: str | None,
    workflow_filename: str | None,
    force: bool,
    pretty: bool,
) -> None:
    spec = _load_and_validate_spec(spec_file)
    project = spec.setdefault("project", {})

    controller_file = controller_filename or str(project.get("controller_filename") or "supervaizer_control.py")
    workflow_file = workflow_filename or str(project.get("workflow_filename") or "sv_main.py")
    out_dir = Path(output_dir or str(project.get("output_dir") or ".")).expanduser().resolve()

    controller_content = _render_controller_py(spec, controller_file, workflow_file)
    workflow_content = _render_sv_main_py(spec, controller_file, workflow_file)

    controller_path = out_dir / controller_file
    workflow_path = out_dir / workflow_file

    _write_text(controller_path, controller_content, force=force)
    _write_text(workflow_path, workflow_content, force=force)

    _print_json(
        {
            "ok": True,
            "operation": "scaffold-integration",
            "spec_file": str(Path(spec_file).resolve()),
            "output_dir": str(out_dir),
            "files": {
                "controller": str(controller_path),
                "workflow": str(workflow_path),
            },
            "next_steps": [
                "Review the generated files and customize field-to-function mapping in sv_main.py.",
                "Refine step updates (payloads, HITL, errors) to match your business workflow.",
                "Run the controller and test with trigger-job --dry-run, then a real run.",
            ],
        },
        pretty=pretty,
    )


def _function_score(name: str, has_loop: bool, returns_dict_like: bool) -> int:
    score = 0
    lname = name.lower()
    for token in ["main", "run", "process", "workflow", "start", "handle"]:
        if token in lname:
            score += 2
    if has_loop:
        score += 2
    if returns_dict_like:
        score += 1
    return score


def _analyze_file(path: Path, project_root: Path) -> list[dict[str, Any]]:
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results: list[dict[str, Any]] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._record(node, is_async=False)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._record(node, is_async=True)
            self.generic_visit(node)

        def _record(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
            params = [arg.arg for arg in node.args.args]
            if node.args.vararg:
                params.append(f"*{node.args.vararg.arg}")
            if node.args.kwarg:
                params.append(f"**{node.args.kwarg.arg}")
            loops = []
            has_loop = False
            returns_dict_like = False
            for child in ast.walk(node):
                if isinstance(child, ast.For):
                    has_loop = True
                    target = ast.unparse(child.target) if hasattr(ast, "unparse") else "<target>"
                    iter_expr = ast.unparse(child.iter) if hasattr(ast, "unparse") else "<iterable>"
                    loops.append({"target": target, "iter": iter_expr})
                if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                    returns_dict_like = True
            results.append(
                {
                    "file": str(path.relative_to(project_root)),
                    "line": node.lineno,
                    "function": node.name,
                    "is_async": is_async,
                    "params": params,
                    "has_loop": has_loop,
                    "loops": loops[:5],
                    "returns_dict_like": returns_dict_like,
                    "score": _function_score(node.name, has_loop, returns_dict_like),
                    "doc": (ast.get_docstring(node) or "")[:240],
                }
            )

    Visitor().visit(tree)
    return results


def _analyze_agent_impl(project_root: str, entry_file: str | None, max_files: int, pretty: bool) -> None:
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise ValueError(f"Project root does not exist: {root}")

    candidates: list[dict[str, Any]] = []
    scanned_files = 0
    excluded_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}

    if entry_file:
        entry_path = (root / entry_file).resolve() if not Path(entry_file).is_absolute() else Path(entry_file)
        if not entry_path.exists():
            raise ValueError(f"Entry file not found: {entry_path}")
        candidates.extend(_analyze_file(entry_path, root))
        scanned_files = 1
    else:
        for path in root.rglob("*.py"):
            if any(part in excluded_dirs for part in path.parts):
                continue
            candidates.extend(_analyze_file(path, root))
            scanned_files += 1
            if scanned_files >= max_files:
                break

    candidates.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("file")), int(item.get("line", 0))))

    top = candidates[:30]
    _print_json(
        {
            "ok": True,
            "operation": "analyze-agent",
            "project_root": str(root),
            "scanned_files": scanned_files,
            "candidate_functions": top,
            "analysis_hints": [
                "Pick the function that represents one business run (the Job).",
                "If that function loops over items, those items are strong Case candidates.",
                "The loop body stages usually become per-case Steps.",
            ],
        },
        pretty=pretty,
    )


def _discover_controller_impl(controller_url: str, controller_api_key: str | None, timeout_seconds: int, pretty: bool) -> None:
    base_url = _normalize_controller_url(controller_url)
    api_key = controller_api_key or os.getenv("CONTROLLER_AUTH_KEY")
    status, openapi = _http_json(
        "GET",
        f"{base_url}/openapi.json",
        headers=_controller_headers(api_key),
        timeout=timeout_seconds,
    )
    paths = openapi.get("paths", {}) if isinstance(openapi, dict) else {}
    job_routes: list[dict[str, Any]] = []
    for path, methods in sorted(paths.items()):
        if not isinstance(methods, dict):
            continue
        for method, spec in sorted(methods.items()):
            if not isinstance(spec, dict):
                continue
            fingerprint = " ".join(
                [
                    path,
                    method,
                    str(spec.get("summary") or ""),
                    str(spec.get("operationId") or ""),
                    " ".join(spec.get("tags", []) or []),
                ]
            ).lower()
            if "job" in fingerprint:
                job_routes.append(
                    {
                        "path": path,
                        "method": method.upper(),
                        "summary": spec.get("summary"),
                        "operation_id": spec.get("operationId"),
                        "tags": spec.get("tags", []),
                    }
                )

    _print_json(
        {
            "ok": True,
            "operation": "discover-controller",
            "controller_url": base_url,
            "status_code": status,
            "job_routes": job_routes,
            "recommended_trigger_route": "/job/start" if any(r["path"] == "/job/start" and r["method"] == "POST" for r in job_routes) else None,
        },
        pretty=pretty,
    )


def _env_status_impl(shell_template: bool, pretty: bool) -> None:
    if shell_template:
        sys.stdout.write(
            "\n".join(
                [
                    'export SUPERVAIZE_API_KEY="..."',
                    'export SUPERVAIZE_WORKSPACE_ID="team_1"',
                    'export SUPERVAIZE_API_URL="https://app.supervaize.com"',
                    "",
                    "# Optional local controller protection",
                    'export CONTROLLER_AUTH_KEY="..."',
                ]
            )
            + "\n"
        )
        return

    values = {name: os.getenv(name) for name in SUPERVAIZE_ENV_VARS}
    missing = [name for name, value in values.items() if not value]
    _print_json(
        {
            "ok": len(missing) == 0,
            "operation": "env-status",
            "required_env_vars": list(SUPERVAIZE_ENV_VARS),
            "present": [name for name, value in values.items() if value],
            "missing": missing,
            "values_masked": {k: (_mask_secret(v) if "KEY" in k else v) for k, v in values.items()},
            "controller_auth_key_present": bool(os.getenv("CONTROLLER_AUTH_KEY") or os.getenv("SUPERVAIZE_CONTROLLER_AUTH_KEY") or os.getenv("SUPERVAIZER_CONTROLLER_AUTH_KEY")),
        },
        pretty=pretty,
    )


def _trigger_job_impl(
    controller_url: str,
    route: str,
    controller_api_key: str | None,
    agent_name: str,
    agent_method: str,
    user_id: str,
    job_id: str | None,
    params_json: str | None,
    params_file: str | None,
    timeout_seconds: int,
    dry_run: bool,
    pretty: bool,
) -> None:
    base_url = _normalize_controller_url(controller_url)
    route_path = route if route.startswith("/") else f"/{route}"
    endpoint = f"{base_url}{route_path}"
    api_key = (
        controller_api_key
        or os.getenv("CONTROLLER_AUTH_KEY")
        or os.getenv("SUPERVAIZE_CONTROLLER_AUTH_KEY")
        or os.getenv("SUPERVAIZER_CONTROLLER_AUTH_KEY")
    )
    params = _load_params(params_json=params_json, params_file=params_file)
    payload = {
        "agent_name": agent_name,
        "agent_method": agent_method,
        "user_id": user_id,
        "params": params,
        "job_id": job_id or str(uuid.uuid4()),
    }

    if dry_run:
        _print_json(
            {
                "ok": True,
                "operation": "trigger-job",
                "dry_run": True,
                "endpoint": endpoint,
                "headers": {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-API-Key": "***" if api_key else None,
                },
                "payload": payload,
            },
            pretty=pretty,
        )
        return

    status, response = _http_json(
        "POST",
        endpoint,
        body=payload,
        headers=_controller_headers(api_key),
        timeout=timeout_seconds,
    )
    _print_json(
        {
            "ok": True,
            "operation": "trigger-job",
            "endpoint": endpoint,
            "status_code": status,
            "request": payload,
            "response": response,
        },
        pretty=pretty,
    )


@app.command("questions")
def questions(pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output.")) -> None:
    """Print the integration discovery questions (Job/Case/Step mapping first)."""
    _print_json(_questions_payload(), pretty=pretty)


@app.command("spec-template")
def spec_template(
    output_file: str | None = typer.Option(None, "--output-file", help="Write the template JSON to a file."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Print or write an integration spec template used for scaffolding."""
    template = _spec_template()
    if output_file:
        _write_text(Path(output_file), json.dumps(template, indent=2) + "\n", force=True)
    _print_json({"ok": True, "operation": "spec-template", "template": template, "output_file": output_file}, pretty=pretty)


@app.command("wizard")
def wizard(
    output_file: str = typer.Option("integration_spec.json", "--output-file", help="Where to write the generated integration spec JSON."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Interactive wizard to collect Job/Case/Step mapping and create an integration spec."""
    _handle(pretty, _wizard_impl, output_file=output_file, pretty=pretty)


@app.command("analyze-agent")
def analyze_agent(
    project_root: str = typer.Option(..., "--project-root", help="Path to the user's Python agent project."),
    entry_file: str | None = typer.Option(None, "--entry-file", help="Optional file to analyze first/only."),
    max_files: int = typer.Option(200, "--max-files", help="Max number of Python files to scan."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Heuristically scan a Python agent project to find likely Job entrypoints and Case loops."""
    _handle(pretty, _analyze_agent_impl, project_root=project_root, entry_file=entry_file, max_files=max_files, pretty=pretty)


@app.command("scaffold-integration")
def scaffold_integration(
    spec_file: str = typer.Option(..., "--spec-file", help="Path to integration spec JSON."),
    output_dir: str | None = typer.Option(None, "--output-dir", help="Override output directory for generated files."),
    controller_filename: str | None = typer.Option(
        None,
        "--controller-filename",
        help="Controller file name (default from spec, usually supervaizer_control.py; can be supervaizer_controll.py if your project uses that spelling).",
    ),
    workflow_filename: str | None = typer.Option(
        None,
        "--workflow-filename",
        help="Workflow wrapper file name (default from spec, usually sv_main.py).",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Generate and customize supervaizer_control.py + sv_main.py from an integration spec."""
    _handle(
        pretty,
        _scaffold_integration_impl,
        spec_file=spec_file,
        output_dir=output_dir,
        controller_filename=controller_filename,
        workflow_filename=workflow_filename,
        force=force,
        pretty=pretty,
    )


@app.command("env-status")
def env_status(
    shell_template: bool = typer.Option(False, "--shell-template", help="Print shell export statements for required env vars."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Check required SUPERVAIZE_* env vars or print export template."""
    _handle(pretty, _env_status_impl, shell_template=shell_template, pretty=pretty)


@app.command("discover-controller")
def discover_controller(
    controller_url: str = typer.Option(..., "--controller-url", help="Base URL, e.g. http://127.0.0.1:8000"),
    controller_api_key: str | None = typer.Option(None, "--controller-api-key", help="Optional controller auth key."),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds", help="HTTP timeout in seconds."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Inspect a controller OpenAPI spec and list job-related routes."""
    _handle(pretty, _discover_controller_impl, controller_url, controller_api_key, timeout_seconds, pretty)


@app.command("trigger-job")
def trigger_job(
    controller_url: str = typer.Option(..., "--controller-url", help="Base URL, e.g. http://127.0.0.1:8000"),
    route: str = typer.Option("/job/start", "--route", help="Trigger route (default: /job/start)"),
    controller_api_key: str | None = typer.Option(None, "--controller-api-key", help="Controller auth key (optional)"),
    agent_name: str = typer.Option(..., "--agent-name"),
    agent_method: str = typer.Option(..., "--agent-method"),
    user_id: str = typer.Option(..., "--user-id"),
    job_id: str | None = typer.Option(None, "--job-id", help="Optional job id (UUID generated if omitted)"),
    params_json: str | None = typer.Option(None, "--params-json", help="JSON object string for JobRequest.params"),
    params_file: str | None = typer.Option(None, "--params-file", help="Path to JSON file for JobRequest.params"),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds", help="HTTP timeout in seconds."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print request payload without sending."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """POST a job request to the controller after your integration is scaffolded and running."""
    _handle(
        pretty,
        _trigger_job_impl,
        controller_url,
        route,
        controller_api_key,
        agent_name,
        agent_method,
        user_id,
        job_id,
        params_json,
        params_file,
        timeout_seconds,
        dry_run,
        pretty,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
