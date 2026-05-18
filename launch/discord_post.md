I am looking for a few people building agents who have real broken runs.

I kept hitting the same debugging pain:

The agent fails, the trace is huge, and I spend an hour figuring out where the bad decision actually started.

So I built AgentLens, a local CLI that captures a run and prints:

- exact failed step
- why the agent likely made the wrong decision
- one concrete fix
- confidence

No hosted service. No dashboard. No telemetry.

The thing I need to learn:

Does this actually save debugging time on real agents?

If you have an agent that:

- picks the wrong tool
- loops
- forgets the original goal
- uses bad tool output downstream
- breaks after a long context

I would love to help you try it.

Install:

```bash
git clone https://github.com/abishekgiri/agentlens-.git
cd agentlens-
pip install -e .
```

Run:

```bash
agentlens runs list
agentlens diagnose <run_id>
agentlens anonymize <run_id>
agentlens feedback-template <run_id>
```

I am not looking for stars. I am looking for traces where the diagnosis is either useful or wrong.
