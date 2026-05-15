I spent hours debugging broken AI agents, so I built a CLI that tells you why the agent failed.

AgentLens captures a local trace of your agent run, then prints a root-cause diagnosis:

- exact failed step
- why it made the wrong decision
- likely failure category
- one concrete fix
- confidence

It is not an observability platform. No dashboard, no hosted service, no database.

I am looking for 10 developers building agents who have real broken runs and are willing to try it.

Ideal test case:

- agent picks the wrong tool
- agent loops
- agent loses the goal
- bad tool output causes later failure
- huge context makes it forget something important

Install:

```bash
git clone https://github.com/abishekgiri/agentlens-.git
cd agentlens-
pip install -e .
```

Run:

```bash
agentlens diagnose <run_id>
```

What I want to learn:

- Was the diagnosis correct?
- Did it save debugging time?
- Was the suggested fix useful?
- Would you pay for this if it worked reliably?

If you have a broken agent run, I would love to test it with you.
