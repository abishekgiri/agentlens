Hey — I am testing a small CLI tool for debugging failed AI agents.

The pain I am trying to solve:

When an agent fails, you often have to read a long trace and guess where the bad decision started.

AgentLens captures a local trace and prints:

- exact failed step
- why the agent made the wrong decision
- one concrete fix
- confidence

No dashboard or hosted service. It is just local CLI debugging.

Would you be open to trying it on one real broken agent run?

What I would ask:

1. Install it locally.
2. Run one broken agent.
3. Send me the diagnosis output, not secrets.
4. Tell me whether it was correct and whether the fix helped.

There is also:

```bash
agentlens anonymize <run_id>
agentlens feedback-template <run_id>
```

I am trying to learn whether this saves debugging time before building anything bigger.
