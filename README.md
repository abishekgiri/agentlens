# AgentLens

AgentLens is a lightweight root-cause explainer for failed AI agent runs.

Phase 0 focused on a local RCA analyzer. Phase 1 adds a small Python SDK that captures agent runs as structured JSON for debugging.

This is not analytics, a dashboard, or a hosted service. The goal is high-quality local traces that make failures easier to explain.

## Supported failure patterns

- wrong tool selection
- repeated loop
- tool error not handled
- missing final answer

## Usage

Analyze an existing trace:

From the project root:

```bash
python engine/analyze.py tests/sample_trace.json
```

To generate and analyze the deliberately broken Day 2 trace:

```bash
python tests/broken_agent.py
python engine/analyze.py tests/real_trace.json
```

Capture a new SDK trace from the Phase 1 broken-agent example:

```bash
python examples/broken_agent.py
```

This writes `agentlens_run.json` locally.

## Python SDK

```python
from agentlens import AgentLensClient

client = AgentLensClient(api_key="...")

response = client.messages_create(
    model="claude-3-5-sonnet-latest",
    max_tokens=256,
    messages=[{"role": "user", "content": "Help debug this run"}],
)

client.save_run()
```

The SDK captures:

- LLM inputs and outputs
- model name
- tools passed to the model
- tool selections
- tool outputs recorded by the app
- stop reason
- token usage
- latency
- errors

## AgentLens v1 Does Not

- replay runs visually
- monitor production
- track cost
- manage prompts
- run evals
- support multiple frameworks

It does one thing:

Diagnose why a run failed.

## Phase 1 Done

Phase 1 is DONE when:

You can run a broken agent, and the SDK automatically captures its trace as structured JSON locally without manual logging.

## Notes

- Python only
- no database
- no web framework
- no external API
- intended to stay simple and readable
- repository name: agentlens-
