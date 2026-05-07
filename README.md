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

To generate and analyze the deliberately broken Day 2 trace:

```bash
python tests/broken_agent.py
python engine/analyze.py tests/real_trace.json
```

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
