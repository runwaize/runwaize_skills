# Supervaizer Integration

Integrate an existing Python agent with [Supervaizer v2](https://github.com/supervaize/supervaizer) and [Supervaize Studio](https://supervaize.com).

This skill targets Supervaizer v2 only. It generates A2A JSON-RPC + A2UI controller scaffolding with Jobs, Cases, Steps, Resources, Surfaces, Actions, and `job.sync` semantics. It does not scaffold v1 job fields, `dynamic_choices`, `job_poll`, or ACP routes.

## Install

In Claude Code:

```
/plugin marketplace add runwaize/runwaize_skills
/plugin install supervaizer_integration
```

Or manually:

```bash
git clone https://github.com/runwaize/runwaize_skills.git
```

Then point your coding agent to the skill definition in [`SKILL.md`](./SKILL.md).

## Documentation

Core protocol docs:

- Supervaizer v2: https://github.com/supervaize/supervaizer/blob/main/docs/2026_05_SUPERVAIZER_v2.md
- Protocols: https://github.com/supervaize/supervaizer/blob/main/docs/2026_05_PROTOCOLS.md
- Job Configurator (Configure screen): https://docs.runwaize.com/docs/supervaizer-controller/job-configurator
- Hello World example: https://github.com/runwaize/supervaize_hello_world

The skill targets Supervaizer 1.9 or later. It covers workspace authorization, local mode, action metadata, human in the loop, resources, dashboards, scheduled start, rule checkpoints, the Job Configurator, guided setup and billable consumption.

Full skill documentation: https://docs.runwaize.com/docs/integrations/skills/supervaizer-integration
