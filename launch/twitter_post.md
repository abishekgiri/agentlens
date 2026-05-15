I spent too much time reading broken AI agent traces and guessing why the run failed.

So I built AgentLens:

A local CLI that tells you:
- exact failure step
- why the agent made the wrong decision
- root cause category
- one concrete fix
- confidence

No dashboard.
No hosted infra.
No analytics platform.

Just:

```bash
agentlens diagnose <run_id>
```

I am looking for 10 developers with real broken agents to test whether this actually saves debugging time.

Repo: https://github.com/abishekgiri/agentlens-
