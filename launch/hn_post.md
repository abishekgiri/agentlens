Show HN: AgentLens - a local CLI that explains why AI agents fail

I built AgentLens because debugging agent failures often turns into reading giant traces and guessing where the run went wrong.

AgentLens is a local Python SDK + CLI. It captures a structured run trace, then diagnoses:

- exact failure step
- root cause category
- why the agent made the wrong decision
- one concrete fix
- confidence

It currently focuses on six failure modes:

- wrong tool selection
- contradictory instructions
- loops
- state drift
- bad tool output cascades
- context overflow

It is intentionally not a hosted observability product. No dashboard, no DB, no auth, no billing.

I am looking for 10 developers with real broken agent runs to test whether this actually saves debugging time.

Repo:
https://github.com/abishekgiri/agentlens-

Install:

```bash
git clone https://github.com/abishekgiri/agentlens-.git
cd agentlens-
pip install -e .
```

The main question I am trying to answer:

Does this genuinely help developers debug AI agents faster?
