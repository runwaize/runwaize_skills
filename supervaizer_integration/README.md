# Supervaizer Integration

Integrate an existing Python agent with [Supervaizer v2](https://github.com/supervaize/supervaizer) and [Supervaize Studio](https://supervaize.com).

This skill targets Supervaizer v2 only. It guides the Job/Case/Step/Resource/Surface/Action mapping, then builds the controller from the SDK's own `supervaizer scaffold`, its reference docs and the Hello World example. It does not scaffold v1 job fields, `dynamic_choices`, `job_poll`, or ACP routes.

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
- Job and mission analytics: https://docs.runwaize.com/docs/supervaizer-controller/job-analytics
- Hello World example: https://github.com/runwaize/supervaize_hello_world

The skill holds the integration process and the design questions. For the contract and the code patterns it points to the SDK scaffold, the SDK docs, the guides above and the Hello World example, so it stays in step with the installed SDK.

Full skill documentation: https://docs.runwaize.com/docs/integrations/skills/supervaizer-integration
