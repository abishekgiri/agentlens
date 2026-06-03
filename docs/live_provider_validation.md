# Live Provider Validation

Current status: blocked.

## Result

- Provider: none
- Date checked: 2026-06-02
- Environment keys found: none
- `OPENAI_API_KEY`: not present
- `ANTHROPIC_API_KEY`: not present

## Workflow

No live OpenAI or Anthropic workflow was run because no provider API key was available in the local environment.

## Trace Quality

Not evaluated for a live provider in this pass.

## Diagnosis Quality

Not evaluated for a live provider in this pass.

## Issues Found

- Live provider validation is still the highest-priority technical validation gap.
- AgentLens has passed local OpenAI/Anthropic fake-provider examples and a LangGraph external OSS workflow, but it still needs at least one real provider call with a real tool call.

## Next Attempt

Run one of:

```bash
OPENAI_API_KEY=... python examples/openai_broken_agent.py
```

or:

```bash
ANTHROPIC_API_KEY=... python examples/anthropic_broken_agent.py
```

Then verify:

- trace generated
- tool call captured
- diagnosis generated
- confidence reasonable
- no crash
