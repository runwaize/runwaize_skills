#!/usr/bin/env python3
"""Chatbot access helper for interacting with Supervaize SaaS via REST API and MCP."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import typer

DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_LIMIT = 5
DEFAULT_EVENT_LIMIT = 200

ENV_SAAS_API_KEY = "SUPERVAIZE_API_KEY"
ENV_SAAS_WORKSPACE = "SUPERVAIZE_WORKSPACE_ID"
ENV_SAAS_API_URL = "SUPERVAIZE_API_URL"

ALL_ENV_VARS = (
    ENV_SAAS_API_KEY,
    ENV_SAAS_WORKSPACE,
    ENV_SAAS_API_URL,
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Supervaize SaaS access helper for chatbots (REST API + MCP).",
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


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _default_profile_path() -> Path:
    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "supervaize_access" / "profile.json"
    return Path.home() / ".supervaize_access" / "profile.json"


def _read_json_file(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_profile(profile_path: str | None) -> dict[str, Any]:
    path = Path(profile_path).expanduser() if profile_path else _default_profile_path()
    if not path.exists():
        return {"_profile_path": str(path), "_profile_exists": False}
    data = _read_json_file(path)
    if not isinstance(data, dict):
        raise ValueError(f"Profile file must contain a JSON object: {path}")
    data["_profile_path"] = str(path)
    data["_profile_exists"] = True
    return data


def _save_profile(profile_path: str | None, data: dict[str, Any]) -> str:
    path = Path(profile_path).expanduser() if profile_path else _default_profile_path()
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    _write_json_file(path, clean)
    return str(path)


def _profile_value(profile: dict[str, Any], key: str) -> str | None:
    value = profile.get(key)
    return value if isinstance(value, str) and value else None


def _resolve_value(arg_value: str | None, env_name: str, profile: dict[str, Any], profile_key: str) -> str | None:
    return arg_value or os.getenv(env_name) or _profile_value(profile, profile_key)


def _resolve_value_arg_profile_only(arg_value: str | None, profile: dict[str, Any], profile_key: str) -> str | None:
    """Resolve from CLI arg or profile only (no env). Used for MCP URL."""
    return arg_value or _profile_value(profile, profile_key)


def _resolve_access_config(
    *,
    profile_path: str | None,
    api_key: str | None = None,
    workspace_id: str | None = None,
    api_url: str | None = None,
    mcp_url: str | None = None,
) -> dict[str, Any]:
    profile = _load_profile(profile_path)
    cfg = {
        "profile_path": profile.get("_profile_path"),
        "profile_exists": bool(profile.get("_profile_exists")),
        "api_key": _resolve_value(api_key, ENV_SAAS_API_KEY, profile, "api_key"),
        "workspace_id": _resolve_value(workspace_id, ENV_SAAS_WORKSPACE, profile, "workspace_id"),
        "api_url": _resolve_value(api_url, ENV_SAAS_API_URL, profile, "api_url"),
        "mcp_url": _resolve_value_arg_profile_only(mcp_url, profile, "mcp_url"),
    }
    if cfg["api_url"]:
        cfg["api_url"] = _normalize_url(str(cfg["api_url"]))
    if cfg["mcp_url"]:
        cfg["mcp_url"] = _normalize_url(str(cfg["mcp_url"]))
    elif cfg["api_url"]:
        cfg["mcp_url"] = _normalize_url(cfg["api_url"]) + "/api/mcp"
    return cfg


def _require_saas(cfg: dict[str, Any]) -> None:
    missing = [name for name, val in (("api_key", cfg.get("api_key")), ("workspace_id", cfg.get("workspace_id")), ("api_url", cfg.get("api_url"))) if not val]
    if missing:
        raise ValueError(f"Missing Supervaize SaaS config: {', '.join(missing)}")


def _require_mcp(cfg: dict[str, Any]) -> None:
    if not cfg.get("mcp_url"):
        raise ValueError(
            "Missing MCP URL. Set --mcp-url or register profile; or set api_url so MCP URL is derived as api_url/api/mcp."
        )


def _http_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | list[Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, Any]:
    raw = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url=url, data=raw, method=method.upper())
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            if not text.strip():
                return resp.status, None
            try:
                return resp.status, json.loads(text)
            except json.JSONDecodeError:
                return resp.status, {"raw_text": text}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(text) if text else None
        except json.JSONDecodeError:
            payload = {"raw_text": text}
        raise RuntimeError(json.dumps({"status": exc.code, "url": url, "error": payload})) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(json.dumps({"url": url, "error": str(exc.reason)})) from exc


def _api_headers(api_key: str, workspace_id: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api_key}",
    }
    if workspace_id:
        headers["workspace"] = workspace_id
    return headers


def _saas_url(cfg: dict[str, Any], path: str) -> str:
    _require_saas(cfg)
    base = str(cfg["api_url"])
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


def _paginate_rest(
    start_url: str,
    *,
    headers: dict[str, str],
    timeout_seconds: int,
    page_limit: int,
    item_limit: int | None = None,
) -> dict[str, Any]:
    items: list[Any] = []
    pages = 0
    next_url: str | None = start_url
    while next_url and pages < page_limit:
        pages += 1
        _, payload = _http_json("GET", next_url, headers=headers, timeout=timeout_seconds)
        if isinstance(payload, dict) and isinstance(payload.get("results"), list):
            page_items = list(payload.get("results", []))
            items.extend(page_items)
            if item_limit is not None and len(items) >= item_limit:
                items = items[:item_limit]
                return {"items": items, "pages_fetched": pages, "truncated": True, "next": payload.get("next")}
            nxt = payload.get("next")
            next_url = urllib.parse.urljoin(next_url, str(nxt)) if nxt else None
        elif isinstance(payload, list):
            items.extend(payload)
            return {"items": items, "pages_fetched": pages, "truncated": False, "next": None}
        else:
            raise ValueError(f"Unexpected paginated response shape from {next_url}")
    return {"items": items, "pages_fetched": pages, "truncated": bool(next_url), "next": next_url}


def _mcp_rpc(mcp_url: str, method: str, params: dict[str, Any] | None, timeout_seconds: int) -> dict[str, Any]:
    rpc_id = str(uuid.uuid4())
    payload = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": method,
    }
    if params is not None:
        payload["params"] = params
    _, response = _http_json(
        "POST",
        mcp_url,
        body=payload,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=timeout_seconds,
    )
    if not isinstance(response, dict):
        raise ValueError("Unexpected MCP response shape")
    return response


def _mcp_extract_text_content(response: dict[str, Any]) -> Any:
    if response.get("error"):
        return {"mcp_error": response["error"]}
    result = response.get("result")
    if not isinstance(result, dict):
        return result
    content = result.get("content")
    if not isinstance(content, list):
        return result
    texts: list[Any] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text")
            if not isinstance(text, str):
                texts.append(text)
                continue
            try:
                texts.append(json.loads(text))
            except json.JSONDecodeError:
                texts.append(text)
        else:
            texts.append(item)
    return texts


def _load_params(params_json: str | None, params_file: str | None) -> dict[str, Any]:
    if params_json and params_file:
        raise ValueError("Use only one of --params-json or --params-file")
    if params_file:
        payload = _read_json_file(params_file)
    elif params_json:
        payload = json.loads(params_json)
    else:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("Params payload must be a JSON object")
    return payload


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
        "questions": [
            "Which Supervaize workspace/team slug should I use?",
            "Do you already have SUPERVAIZE_API_KEY / SUPERVAIZE_API_URL?",
            "For case/step viewing: do you have a job_id, case_id, or n8n execution_id?",
            "For agent-specific queries: what is the agent_slug (preferred)?",
        ],
    }


def _env_status_impl(profile_path: str | None, shell_template: bool, pretty: bool) -> None:
    if shell_template:
        sys.stdout.write(
            "\n".join(
                [
                    'export SUPERVAIZE_API_KEY="..."',
                    'export SUPERVAIZE_WORKSPACE_ID="team_1"',
                    'export SUPERVAIZE_API_URL="https://app.supervaize.com"',
                ]
            )
            + "\n"
        )
        return
    cfg = _resolve_access_config(profile_path=profile_path)
    _print_json(
        {
            "ok": bool(cfg.get("api_key") and cfg.get("workspace_id") and cfg.get("api_url")),
            "operation": "env-status",
            "profile_path": cfg.get("profile_path"),
            "profile_exists": cfg.get("profile_exists"),
            "required_saas": [ENV_SAAS_API_KEY, ENV_SAAS_WORKSPACE, ENV_SAAS_API_URL],
            "values": {
                "api_key": _mask_secret(cfg.get("api_key")),
                "workspace_id": cfg.get("workspace_id"),
                "api_url": cfg.get("api_url"),
                "mcp_url": cfg.get("mcp_url"),
            },
        },
        pretty=pretty,
    )


def _register_to_supervaize_impl(
    profile_path: str | None,
    api_key: str | None,
    workspace_id: str | None,
    api_url: str | None,
    mcp_url: str | None,
    save_profile: bool,
    timeout_seconds: int,
    page_limit: int,
    pretty: bool,
) -> None:
    cfg = _resolve_access_config(
        profile_path=profile_path,
        api_key=api_key,
        workspace_id=workspace_id,
        api_url=api_url,
        mcp_url=mcp_url,
    )
    _require_saas(cfg)

    teams_url = _saas_url(cfg, "/w/api/teams/")
    teams_result = _paginate_rest(
        teams_url,
        headers=_api_headers(str(cfg["api_key"])),
        timeout_seconds=timeout_seconds,
        page_limit=page_limit,
        item_limit=200,
    )
    teams = teams_result["items"]

    workspace_match = None
    for team in teams:
        if not isinstance(team, dict):
            continue
        if str(team.get("slug") or "") == str(cfg["workspace_id"]):
            workspace_match = team
            break
        if str(team.get("name") or "") == str(cfg["workspace_id"]):
            workspace_match = team

    saved_to = None
    if save_profile:
        saved_to = _save_profile(
            profile_path,
            {
                "api_key": cfg.get("api_key"),
                "workspace_id": cfg.get("workspace_id"),
                "api_url": cfg.get("api_url"),
                "mcp_url": cfg.get("mcp_url"),
            },
        )

    _print_json(
        {
            "ok": True,
            "operation": "register-to-supervaize",
            "workspace_id": cfg.get("workspace_id"),
            "api_url": cfg.get("api_url"),
            "validated": {
                "teams_list_access": True,
                "workspace_match_found": bool(workspace_match),
            },
            "workspace_match": workspace_match,
            "teams_count_seen": len(teams),
            "teams_pages_fetched": teams_result.get("pages_fetched"),
            "saved_profile": bool(save_profile),
            "saved_to": saved_to,
            "notes": [
                "Registration here means local chatbot session/profile registration to a Supervaize workspace using API credentials.",
                "If workspace_match_found is false, verify SUPERVAIZE_WORKSPACE_ID/team slug and API key access scope.",
            ],
        },
        pretty=pretty,
    )


def _list_agents_impl(
    profile_path: str | None,
    api_key: str | None,
    workspace_id: str | None,
    api_url: str | None,
    page_limit: int,
    timeout_seconds: int,
    pretty: bool,
) -> None:
    cfg = _resolve_access_config(profile_path=profile_path, api_key=api_key, workspace_id=workspace_id, api_url=api_url)
    _require_saas(cfg)
    url = _saas_url(cfg, f"/w/{cfg['workspace_id']}/api/v1/agents/")
    result = _paginate_rest(
        url,
        headers=_api_headers(str(cfg["api_key"])),
        timeout_seconds=timeout_seconds,
        page_limit=page_limit,
        item_limit=500,
    )
    _print_json(
        {
            "ok": True,
            "operation": "list-agents",
            "workspace_id": cfg.get("workspace_id"),
            "count": len(result["items"]),
            "agents": result["items"],
            "truncated": result.get("truncated"),
        },
        pretty=pretty,
    )


def _get_agent_by_slug(cfg: dict[str, Any], agent_slug: str, timeout_seconds: int) -> dict[str, Any]:
    url = _saas_url(cfg, f"/w/{cfg['workspace_id']}/api/v1/agents/by-slug/{agent_slug}/")
    _, payload = _http_json("GET", url, headers=_api_headers(str(cfg["api_key"])), timeout=timeout_seconds)
    if not isinstance(payload, dict):
        raise ValueError("Unexpected agent response")
    return payload


def _resolve_agent_impl(
    cfg: dict[str, Any],
    *,
    agent_slug: str | None,
    agent_id: str | None,
    agent_name: str | None,
    timeout_seconds: int,
    page_limit: int,
) -> dict[str, Any]:
    _require_saas(cfg)
    if agent_slug:
        return _get_agent_by_slug(cfg, agent_slug, timeout_seconds)
    if not (agent_id or agent_name):
        raise ValueError("Provide --agent-slug (preferred) or --agent-id/--agent-name")
    url = _saas_url(cfg, f"/w/{cfg['workspace_id']}/api/v1/agents/")
    result = _paginate_rest(
        url,
        headers=_api_headers(str(cfg["api_key"])),
        timeout_seconds=timeout_seconds,
        page_limit=page_limit,
        item_limit=500,
    )
    for item in result["items"]:
        if not isinstance(item, dict):
            continue
        if agent_id and str(item.get("id")) == agent_id:
            return item
        if agent_name and str(item.get("name")) == agent_name:
            return item
    raise ValueError("Agent not found with provided identifier(s)")


def _create_mission_impl(
    profile_path: str | None,
    api_key: str | None,
    workspace_id: str | None,
    api_url: str | None,
    name: str,
    description: str | None,
    budget: str | None,
    status_value: str | None,
    priority: str | None,
    start_date: str | None,
    end_date: str | None,
    timeout_seconds: int,
    dry_run: bool,
    pretty: bool,
) -> None:
    cfg = _resolve_access_config(profile_path=profile_path, api_key=api_key, workspace_id=workspace_id, api_url=api_url)
    _require_saas(cfg)
    body: dict[str, Any] = {"name": name}
    if description is not None:
        body["description"] = description
    if budget is not None:
        body["budget"] = budget
    if status_value is not None:
        body["status"] = status_value
    if priority is not None:
        body["priority"] = priority
    if start_date is not None:
        body["start_date"] = start_date
    if end_date is not None:
        body["end_date"] = end_date

    url = _saas_url(cfg, f"/w/{cfg['workspace_id']}/api/v1/missions/")
    headers = _api_headers(str(cfg["api_key"]))
    if dry_run:
        _print_json(
            {
                "ok": True,
                "operation": "create-mission",
                "dry_run": True,
                "endpoint": url,
                "headers": {"Authorization": "Api-Key ***", "Content-Type": "application/json", "Accept": "application/json"},
                "payload": body,
            },
            pretty=pretty,
        )
        return
    status_code, response = _http_json("POST", url, body=body, headers=headers, timeout=timeout_seconds)
    _print_json(
        {
            "ok": True,
            "operation": "create-mission",
            "status_code": status_code,
            "request": body,
            "response": response,
        },
        pretty=pretty,
    )


def _list_missions(cfg: dict[str, Any], timeout_seconds: int, page_limit: int) -> dict[str, Any]:
    url = _saas_url(cfg, f"/w/{cfg['workspace_id']}/api/v1/missions/")
    return _paginate_rest(
        url,
        headers=_api_headers(str(cfg["api_key"])),
        timeout_seconds=timeout_seconds,
        page_limit=page_limit,
        item_limit=1000,
    )


def _mission_relation_keys_present(mission: dict[str, Any]) -> bool:
    keys = {
        "agent",
        "agent_id",
        "agent_slug",
        "agents",
        "agent_ids",
        "agent_slugs",
        "active_agents",
    }
    return any(k in mission for k in keys)


def _matches_agent_token(value: Any, agent: dict[str, Any], agent_slug: str | None, agent_id: str | None, agent_name: str | None) -> bool:
    tokens = {str(v) for v in [agent.get("id"), agent.get("slug"), agent.get("name"), agent.get("alias"), agent_slug, agent_id, agent_name] if v}
    if isinstance(value, dict):
        return any(_matches_agent_token(v, agent, agent_slug, agent_id, agent_name) for v in value.values())
    if isinstance(value, list):
        return any(_matches_agent_token(v, agent, agent_slug, agent_id, agent_name) for v in value)
    if value is None:
        return False
    return str(value) in tokens


def _show_missions_for_agent_impl(
    profile_path: str | None,
    api_key: str | None,
    workspace_id: str | None,
    api_url: str | None,
    agent_slug: str | None,
    agent_id: str | None,
    agent_name: str | None,
    timeout_seconds: int,
    page_limit: int,
    pretty: bool,
) -> None:
    cfg = _resolve_access_config(profile_path=profile_path, api_key=api_key, workspace_id=workspace_id, api_url=api_url)
    _require_saas(cfg)
    agent = _resolve_agent_impl(
        cfg,
        agent_slug=agent_slug,
        agent_id=agent_id,
        agent_name=agent_name,
        timeout_seconds=timeout_seconds,
        page_limit=page_limit,
    )
    missions_result = _list_missions(cfg, timeout_seconds=timeout_seconds, page_limit=page_limit)
    missions = [m for m in missions_result["items"] if isinstance(m, dict)]

    relation_fields_present = any(_mission_relation_keys_present(m) for m in missions)
    if not relation_fields_present:
        _print_json(
            {
                "ok": False,
                "operation": "show-missions-for-agent",
                "workspace_id": cfg.get("workspace_id"),
                "agent": agent,
                "limitation": {
                    "reason": "Public mission API responses do not expose agent linkage fields in this spec/response shape.",
                    "api_endpoint": f"/w/{cfg['workspace_id']}/api/v1/missions/",
                    "suggestions": [
                        "Use an internal endpoint that exposes mission-agent associations.",
                        "Extend the public API serializer to include mission.agents.",
                        "Provide a separate mapping source to the chatbot (mission IDs per agent).",
                    ],
                },
                "missions_seen": len(missions),
            },
            pretty=pretty,
        )
        return

    filtered = [m for m in missions if _matches_agent_token(m, agent, agent_slug, agent_id, agent_name)]
    _print_json(
        {
            "ok": True,
            "operation": "show-missions-for-agent",
            "workspace_id": cfg.get("workspace_id"),
            "agent": agent,
            "missions": filtered,
            "missions_count": len(filtered),
            "missions_scanned": len(missions),
            "matching_mode": "relation-field-filter",
        },
        pretty=pretty,
    )


def _list_ctrl_events(
    cfg: dict[str, Any],
    *,
    timeout_seconds: int,
    page_limit: int,
    event_limit: int,
) -> dict[str, Any]:
    _require_saas(cfg)
    url = _saas_url(cfg, f"/w/{cfg['workspace_id']}/api/v1/ctrl-events/")
    return _paginate_rest(
        url,
        headers=_api_headers(str(cfg["api_key"]), workspace_id=str(cfg["workspace_id"])),
        timeout_seconds=timeout_seconds,
        page_limit=page_limit,
        item_limit=event_limit,
    )


def _flatten_scalars(obj: Any) -> list[str]:
    out: list[str] = []
    stack = [obj]
    seen_ids: set[int] = set()
    while stack:
        cur = stack.pop()
        if isinstance(cur, (dict, list)):
            ident = id(cur)
            if ident in seen_ids:
                continue
            seen_ids.add(ident)
        if isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
        elif cur is None:
            continue
        else:
            out.append(str(cur))
    return out


def _event_matches_agent(event: dict[str, Any], *, agent: dict[str, Any], agent_slug: str | None, agent_id: str | None, agent_name: str | None) -> bool:
    tokens = {str(v) for v in [agent.get("id"), agent.get("slug"), agent.get("name"), agent.get("alias"), agent_slug, agent_id, agent_name] if v}
    if not tokens:
        return False
    values = _flatten_scalars({"source": event.get("source"), "details": event.get("details")})
    return any(v in tokens for v in values)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_job_id(event: dict[str, Any]) -> str | None:
    source = _safe_dict(event.get("source"))
    details = _safe_dict(event.get("details"))
    for key in ("job", "job_id"):
        if source.get(key):
            return str(source[key])
        if details.get(key):
            return str(details[key])
    nested_source = details.get("source")
    if isinstance(nested_source, dict):
        for key in ("job", "job_id"):
            if nested_source.get(key):
                return str(nested_source[key])
    return None


def _extract_case_id_or_ref(event: dict[str, Any]) -> str | None:
    source = _safe_dict(event.get("source"))
    details = _safe_dict(event.get("details"))
    for key in ("case", "case_id"):
        if source.get(key):
            return str(source[key])
        if details.get(key):
            return str(details[key])
    for key in ("case_ref", "execution_id", "original_case_id"):
        if details.get(key):
            return str(details[key])
    return None


def _aggregate_jobs(events: list[dict[str, Any]]) -> dict[str, Any]:
    jobs: dict[str, dict[str, Any]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        if not event_type.startswith("agent.job."):
            continue
        job_id = _extract_job_id(event) or "unknown"
        created_at = event.get("created_at")
        entry = jobs.setdefault(
            job_id,
            {
                "job_id": None if job_id == "unknown" else job_id,
                "events": 0,
                "event_types": {},
                "latest_event_type": None,
                "latest_created_at": None,
                "status_guess": None,
                "sample_agent_hints": [],
            },
        )
        entry["events"] += 1
        entry["event_types"][event_type] = int(entry["event_types"].get(event_type, 0)) + 1
        if created_at and (entry["latest_created_at"] is None or str(created_at) >= str(entry["latest_created_at"])):
            entry["latest_created_at"] = created_at
            entry["latest_event_type"] = event_type
        if event_type.endswith(".end"):
            entry["status_guess"] = "completed"
        elif event_type.endswith(".error"):
            entry["status_guess"] = "error"
        elif event_type.endswith(".timeout"):
            entry["status_guess"] = "timeout"
        elif event_type.endswith(".status"):
            details = _safe_dict(event.get("details"))
            if details.get("status"):
                entry["status_guess"] = str(details["status"])
        elif entry["status_guess"] is None and event_type.endswith(".start"):
            entry["status_guess"] = "started"

        hints = _flatten_scalars({"source": event.get("source"), "details": event.get("details")})
        for hint in hints:
            if hint not in entry["sample_agent_hints"] and len(entry["sample_agent_hints"]) < 10:
                entry["sample_agent_hints"].append(hint)

    return {
        "jobs": sorted(jobs.values(), key=lambda j: (str(j.get("latest_created_at") or ""), str(j.get("job_id") or "")), reverse=True),
        "job_count": len(jobs),
    }


def _aggregate_cases(events: list[dict[str, Any]]) -> dict[str, Any]:
    cases: dict[str, dict[str, Any]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        if not event_type.startswith("agent.case."):
            continue
        case_key = _extract_case_id_or_ref(event) or "unknown"
        job_id = _extract_job_id(event)
        details = _safe_dict(event.get("details"))
        created_at = event.get("created_at")
        source = _safe_dict(event.get("source"))

        entry = cases.setdefault(
            case_key,
            {
                "case_key": case_key,
                "case_id": source.get("case") or details.get("case_id"),
                "case_ref": details.get("case_ref") or details.get("execution_id") or details.get("original_case_id"),
                "job_id": job_id,
                "name": details.get("name"),
                "description": details.get("description"),
                "events": 0,
                "event_types": {},
                "latest_event_type": None,
                "latest_created_at": None,
                "status_guess": None,
                "steps": [],
                "step_count": 0,
            },
        )
        entry["events"] += 1
        entry["event_types"][event_type] = int(entry["event_types"].get(event_type, 0)) + 1
        if job_id and not entry.get("job_id"):
            entry["job_id"] = job_id
        if details.get("name") and not entry.get("name"):
            entry["name"] = details.get("name")
        if details.get("description") and not entry.get("description"):
            entry["description"] = details.get("description")
        if created_at and (entry["latest_created_at"] is None or str(created_at) >= str(entry["latest_created_at"])):
            entry["latest_created_at"] = created_at
            entry["latest_event_type"] = event_type

        if event_type.endswith(".start"):
            entry["status_guess"] = entry.get("status_guess") or "started"
        elif event_type.endswith(".end"):
            entry["status_guess"] = "completed"
        elif event_type.endswith(".error"):
            entry["status_guess"] = "error"
        elif event_type.endswith(".status") and details.get("status"):
            entry["status_guess"] = str(details.get("status"))
        elif event_type.endswith(".update"):
            step = {
                "index": details.get("index"),
                "name": details.get("name"),
                "payload": details.get("payload"),
                "cost": details.get("cost"),
                "is_final": details.get("is_final"),
                "error": details.get("error"),
                "created_at": created_at,
            }
            entry["steps"].append(step)
            entry["step_count"] = len(entry["steps"])
            if details.get("is_final") and entry.get("status_guess") in (None, "started"):
                entry["status_guess"] = "completed"

    ordered = sorted(cases.values(), key=lambda c: (str(c.get("latest_created_at") or ""), str(c.get("case_key") or "")), reverse=True)
    return {"cases": ordered, "case_count": len(ordered)}


def _view_cases_steps_api_impl(
    cfg: dict[str, Any],
    *,
    job_id: str | None,
    case_id: str | None,
    page_limit: int,
    event_limit: int,
    timeout_seconds: int,
    pretty: bool,
) -> None:
    events_result = _list_ctrl_events(cfg, timeout_seconds=timeout_seconds, page_limit=page_limit, event_limit=event_limit)
    raw_events = [e for e in events_result["items"] if isinstance(e, dict)]
    filtered = []
    for event in raw_events:
        et = str(event.get("event_type") or "")
        if not et.startswith("agent.case."):
            continue
        if job_id and (_extract_job_id(event) != job_id):
            continue
        if case_id and (_extract_case_id_or_ref(event) != case_id):
            continue
        filtered.append(event)

    agg = _aggregate_cases(filtered)
    _print_json(
        {
            "ok": True,
            "operation": "view-cases-steps",
            "backend": "api",
            "workspace_id": cfg.get("workspace_id"),
            "filters": {"job_id": job_id, "case_id": case_id},
            "events_scanned": len(raw_events),
            "events_matched": len(filtered),
            "pages_fetched": events_result.get("pages_fetched"),
            "truncated": events_result.get("truncated"),
            **agg,
            "notes": [
                "This view reconstructs cases/steps from ctrl-events (best effort).",
                "Public OpenAPI does not expose generic REST /cases or /steps endpoints in the provided spec.",
            ],
        },
        pretty=pretty,
    )


def _view_cases_steps_mcp_impl(
    cfg: dict[str, Any],
    *,
    execution_id: str,
    team_slug: str | None,
    correlation_id: str | None,
    timeout_seconds: int,
    pretty: bool,
) -> None:
    _require_mcp(cfg)
    team = team_slug or cfg.get("workspace_id")
    if not team:
        raise ValueError("Provide --team-slug or set SUPERVAIZE_WORKSPACE_ID")
    params = {
        "name": "get_case_status",
        "arguments": {
            "execution_id": execution_id,
            "team_slug": team,
        },
    }
    if correlation_id:
        params["arguments"]["correlation_id"] = correlation_id
    response = _mcp_rpc(str(cfg["mcp_url"]), "tools/call", params, timeout_seconds=timeout_seconds)
    parsed = _mcp_extract_text_content(response)
    _print_json(
        {
            "ok": "error" not in response,
            "operation": "view-cases-steps",
            "backend": "mcp",
            "mcp_url": cfg.get("mcp_url"),
            "tool": "get_case_status",
            "arguments": params["arguments"],
            "mcp_response": response,
            "parsed_content": parsed,
        },
        pretty=pretty,
    )


def _job_status_for_agent_impl(
    profile_path: str | None,
    api_key: str | None,
    workspace_id: str | None,
    api_url: str | None,
    agent_slug: str | None,
    agent_id: str | None,
    agent_name: str | None,
    timeout_seconds: int,
    page_limit: int,
    event_limit: int,
    pretty: bool,
) -> None:
    cfg = _resolve_access_config(profile_path=profile_path, api_key=api_key, workspace_id=workspace_id, api_url=api_url)
    _require_saas(cfg)
    agent = _resolve_agent_impl(
        cfg,
        agent_slug=agent_slug,
        agent_id=agent_id,
        agent_name=agent_name,
        timeout_seconds=timeout_seconds,
        page_limit=page_limit,
    )
    events_result = _list_ctrl_events(cfg, timeout_seconds=timeout_seconds, page_limit=page_limit, event_limit=event_limit)
    all_events = [e for e in events_result["items"] if isinstance(e, dict)]
    job_events = [e for e in all_events if str(e.get("event_type") or "").startswith("agent.job.")]
    matched_events = [e for e in job_events if _event_matches_agent(e, agent=agent, agent_slug=agent_slug, agent_id=agent_id, agent_name=agent_name)]

    if not matched_events:
        _print_json(
            {
                "ok": False,
                "operation": "job-status-for-agent",
                "workspace_id": cfg.get("workspace_id"),
                "agent": agent,
                "job_events_scanned": len(job_events),
                "matched_events": 0,
                "limitation": {
                    "reason": "No job events matched the agent identifiers in ctrl-events source/details.",
                    "note": "Job status for agent is best-effort when the public API exposes ctrl-events but not a dedicated jobs endpoint.",
                    "suggestions": [
                        "Increase page_limit/event_limit to scan more events.",
                        "Verify controller emits agent slug/name/id in job event source/details.",
                        "Use an internal jobs endpoint if available.",
                    ],
                },
            },
            pretty=pretty,
        )
        return

    agg = _aggregate_jobs(matched_events)
    _print_json(
        {
            "ok": True,
            "operation": "job-status-for-agent",
            "workspace_id": cfg.get("workspace_id"),
            "agent": agent,
            "job_events_scanned": len(job_events),
            "matched_events": len(matched_events),
            "pages_fetched": events_result.get("pages_fetched"),
            "truncated": events_result.get("truncated"),
            **agg,
            "notes": [
                "Status is derived from controller event lifecycle (best effort).",
                "Public OpenAPI spec provided does not expose a generic jobs REST endpoint.",
            ],
        },
        pretty=pretty,
    )


def _start_job_impl(pretty: bool) -> None:
    """Job start is not exposed via public REST or MCP; return structured limitation."""
    _print_json(
        {
            "ok": False,
            "operation": "start-job",
            "limitation": {
                "reason": "Current public Supervaize REST API and MCP do not expose a generic job-start command.",
                "suggestions": [
                    "Start jobs via the Studio UI or via a Supervaizer (use supervaizer_integration skill for agent-side).",
                    "For telemetry only, emit controller events to Studio via /ctrl-events.",
                ],
            },
        },
        pretty=pretty,
    )


def _mcp_tools_impl(profile_path: str | None, mcp_url: str | None, timeout_seconds: int, pretty: bool) -> None:
    cfg = _resolve_access_config(profile_path=profile_path, mcp_url=mcp_url)
    _require_mcp(cfg)
    response = _mcp_rpc(str(cfg["mcp_url"]), "tools/list", {}, timeout_seconds=timeout_seconds)
    _print_json(
        {
            "ok": "error" not in response,
            "operation": "mcp-tools",
            "mcp_url": cfg.get("mcp_url"),
            "response": response,
        },
        pretty=pretty,
    )


def _mcp_call_impl(
    profile_path: str | None,
    mcp_url: str | None,
    tool_name: str,
    arguments_json: str | None,
    arguments_file: str | None,
    timeout_seconds: int,
    pretty: bool,
) -> None:
    cfg = _resolve_access_config(profile_path=profile_path, mcp_url=mcp_url)
    _require_mcp(cfg)
    arguments = _load_params(arguments_json, arguments_file)
    response = _mcp_rpc(
        str(cfg["mcp_url"]),
        "tools/call",
        {"name": tool_name, "arguments": arguments},
        timeout_seconds=timeout_seconds,
    )
    _print_json(
        {
            "ok": "error" not in response,
            "operation": "mcp-call",
            "mcp_url": cfg.get("mcp_url"),
            "tool": tool_name,
            "arguments": arguments,
            "mcp_response": response,
            "parsed_content": _mcp_extract_text_content(response),
        },
        pretty=pretty,
    )


@app.command("questions")
def questions(pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output.")) -> None:
    """Print the access-discovery questions to ask before acting."""
    _print_json(_questions_payload(), pretty=pretty)


@app.command("env-status")
def env_status(
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional profile JSON path."),
    shell_template: bool = typer.Option(False, "--shell-template", help="Print export template for SUPERVAIZE_* env vars."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Check env/profile config or print env export template."""
    _handle(pretty, _env_status_impl, profile_path, shell_template, pretty)


@app.command("register-to-supervaize")
def register_to_supervaize(
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional profile JSON path."),
    api_key: str | None = typer.Option(None, "--api-key", help="Supervaize API key (or use SUPERVAIZE_API_KEY)."),
    workspace_id: str | None = typer.Option(None, "--workspace-id", help="Workspace/team slug (or use SUPERVAIZE_WORKSPACE_ID)."),
    api_url: str | None = typer.Option(None, "--api-url", help="Base API URL (or use SUPERVAIZE_API_URL)."),
    mcp_url: str | None = typer.Option(None, "--mcp-url", help="Optional MCP HTTP endpoint to save in profile."),
    save_profile: bool = typer.Option(True, "--save-profile/--no-save-profile", help="Persist resolved values for future commands."),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds", help="HTTP timeout in seconds."),
    page_limit: int = typer.Option(DEFAULT_PAGE_LIMIT, "--page-limit", help="Max pages to scan when validating workspace/team access."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Validate SaaS access and register local chatbot profile for a workspace."""
    _handle(
        pretty,
        _register_to_supervaize_impl,
        profile_path,
        api_key,
        workspace_id,
        api_url,
        mcp_url,
        save_profile,
        timeout_seconds,
        page_limit,
        pretty,
    )


@app.command("list-agents")
def list_agents(
    profile_path: str | None = typer.Option(None, "--profile-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
    workspace_id: str | None = typer.Option(None, "--workspace-id"),
    api_url: str | None = typer.Option(None, "--api-url"),
    page_limit: int = typer.Option(DEFAULT_PAGE_LIMIT, "--page-limit"),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """List agents in the Supervaize workspace (REST API)."""
    _handle(pretty, _list_agents_impl, profile_path, api_key, workspace_id, api_url, page_limit, timeout_seconds, pretty)


@app.command("create-mission")
def create_mission(
    name: str = typer.Option(..., "--name", help="Mission name."),
    description: str | None = typer.Option(None, "--description", help="Mission description."),
    budget: str | None = typer.Option(None, "--budget", help="Budget decimal string, e.g. 1000.00"),
    status_value: str | None = typer.Option(None, "--status", help="Mission status (draft, in_progress, completed, on_hold, cancelled)."),
    priority: str | None = typer.Option(None, "--priority", help="Mission priority enum value if supported."),
    start_date: str | None = typer.Option(None, "--start-date", help="YYYY-MM-DD"),
    end_date: str | None = typer.Option(None, "--end-date", help="YYYY-MM-DD"),
    profile_path: str | None = typer.Option(None, "--profile-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
    workspace_id: str | None = typer.Option(None, "--workspace-id"),
    api_url: str | None = typer.Option(None, "--api-url"),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print payload without sending."),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """Create a mission in the Supervaize SaaS workspace (REST API)."""
    _handle(
        pretty,
        _create_mission_impl,
        profile_path,
        api_key,
        workspace_id,
        api_url,
        name,
        description,
        budget,
        status_value,
        priority,
        start_date,
        end_date,
        timeout_seconds,
        dry_run,
        pretty,
    )


@app.command("show-missions-for-agent")
def show_missions_for_agent(
    agent_slug: str | None = typer.Option(None, "--agent-slug", help="Agent slug (preferred)."),
    agent_id: str | None = typer.Option(None, "--agent-id", help="Agent id (fallback if slug unknown)."),
    agent_name: str | None = typer.Option(None, "--agent-name", help="Agent name (fallback if slug/id unknown)."),
    profile_path: str | None = typer.Option(None, "--profile-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
    workspace_id: str | None = typer.Option(None, "--workspace-id"),
    api_url: str | None = typer.Option(None, "--api-url"),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds"),
    page_limit: int = typer.Option(DEFAULT_PAGE_LIMIT, "--page-limit"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """Show missions for an agent if mission-agent linkage is exposed by the API response."""
    _handle(
        pretty,
        _show_missions_for_agent_impl,
        profile_path,
        api_key,
        workspace_id,
        api_url,
        agent_slug,
        agent_id,
        agent_name,
        timeout_seconds,
        page_limit,
        pretty,
    )


@app.command("job-status-for-agent")
def job_status_for_agent(
    agent_slug: str | None = typer.Option(None, "--agent-slug", help="Agent slug (preferred)."),
    agent_id: str | None = typer.Option(None, "--agent-id"),
    agent_name: str | None = typer.Option(None, "--agent-name"),
    profile_path: str | None = typer.Option(None, "--profile-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
    workspace_id: str | None = typer.Option(None, "--workspace-id"),
    api_url: str | None = typer.Option(None, "--api-url"),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds"),
    page_limit: int = typer.Option(DEFAULT_PAGE_LIMIT, "--page-limit"),
    event_limit: int = typer.Option(DEFAULT_EVENT_LIMIT, "--event-limit"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """Best-effort job status summary for an agent using ctrl-events (REST API)."""
    _handle(
        pretty,
        _job_status_for_agent_impl,
        profile_path,
        api_key,
        workspace_id,
        api_url,
        agent_slug,
        agent_id,
        agent_name,
        timeout_seconds,
        page_limit,
        event_limit,
        pretty,
    )


@app.command("view-cases-steps")
def view_cases_steps(
    backend: str = typer.Option("api", "--backend", help="api or mcp"),
    job_id: str | None = typer.Option(None, "--job-id", help="Filter ctrl-events reconstruction by job ID (api backend)."),
    case_id: str | None = typer.Option(None, "--case-id", help="Filter ctrl-events reconstruction by case ID/ref (api backend)."),
    execution_id: str | None = typer.Option(None, "--execution-id", help="n8n execution ID (mcp backend)."),
    team_slug: str | None = typer.Option(None, "--team-slug", help="Workspace/team slug override for MCP get_case_status."),
    correlation_id: str | None = typer.Option(None, "--correlation-id", help="Optional correlation ID for MCP get_case_status."),
    profile_path: str | None = typer.Option(None, "--profile-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
    workspace_id: str | None = typer.Option(None, "--workspace-id"),
    api_url: str | None = typer.Option(None, "--api-url"),
    mcp_url: str | None = typer.Option(None, "--mcp-url"),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds"),
    page_limit: int = typer.Option(DEFAULT_PAGE_LIMIT, "--page-limit"),
    event_limit: int = typer.Option(DEFAULT_EVENT_LIMIT, "--event-limit"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """View cases and steps via ctrl-events reconstruction (api) or MCP get_case_status (mcp)."""
    def runner() -> None:
        cfg = _resolve_access_config(
            profile_path=profile_path,
            api_key=api_key,
            workspace_id=workspace_id,
            api_url=api_url,
            mcp_url=mcp_url,
        )
        mode = backend.lower().strip()
        if mode == "api":
            _require_saas(cfg)
            _view_cases_steps_api_impl(
                cfg,
                job_id=job_id,
                case_id=case_id,
                page_limit=page_limit,
                event_limit=event_limit,
                timeout_seconds=timeout_seconds,
                pretty=pretty,
            )
            return
        if mode == "mcp":
            if not execution_id:
                raise ValueError("--execution-id is required for --backend mcp")
            _view_cases_steps_mcp_impl(
                cfg,
                execution_id=execution_id,
                team_slug=team_slug,
                correlation_id=correlation_id,
                timeout_seconds=timeout_seconds,
                pretty=pretty,
            )
            return
        raise ValueError("Unsupported backend for view-cases-steps. Use api or mcp.")

    _handle(pretty, runner)


@app.command("start-job")
def start_job(
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """Job start is not exposed via REST/MCP; returns structured limitation and suggestions."""
    _start_job_impl(pretty=pretty)


@app.command("mcp-tools")
def mcp_tools(
    profile_path: str | None = typer.Option(None, "--profile-path"),
    mcp_url: str | None = typer.Option(None, "--mcp-url"),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """List available tools on the Supervaize MCP endpoint."""
    _handle(pretty, _mcp_tools_impl, profile_path, mcp_url, timeout_seconds, pretty)


@app.command("mcp-call")
def mcp_call(
    tool_name: str = typer.Option(..., "--tool-name", help="MCP tool name to call."),
    arguments_json: str | None = typer.Option(None, "--arguments-json", help="JSON object for tool arguments."),
    arguments_file: str | None = typer.Option(None, "--arguments-file", help="Path to JSON file for tool arguments."),
    profile_path: str | None = typer.Option(None, "--profile-path"),
    mcp_url: str | None = typer.Option(None, "--mcp-url"),
    timeout_seconds: int = typer.Option(DEFAULT_TIMEOUT, "--timeout-seconds"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """Call any MCP tool (utility command)."""
    _handle(pretty, _mcp_call_impl, profile_path, mcp_url, tool_name, arguments_json, arguments_file, timeout_seconds, pretty)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
