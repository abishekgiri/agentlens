# AgentLens Phase 0

AgentLens is a lightweight root-cause explainer for failed AI agent runs.

This Phase 0 prototype focuses on a single local Python script that:

- loads an agent trace from JSON
- scans the steps for simple failure patterns
- prints a structured RCA report in the terminal

## Supported failure patterns

- wrong tool selection
- repeated loop
- tool error not handled
- missing final answer

## Usage

From the project root:

```bash
python engine/analyze.py tests/sample_trace.json
```

## Notes

- Python only
- no database
- no web framework
- no external API
- intended to stay simple and readable

# agentlens-
