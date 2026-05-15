# AgentLens

AgentLens is a local CLI + Python SDK that captures AI agent runs and explains why they failed.

It is for debugging broken agents, not monitoring production.

## 2-Minute Install

```bash
git clone https://github.com/abishekgiri/agentlens-.git
cd agentlens-
pip install -e .
```

Optional provider SDKs:

```bash
pip install -e ".[anthropic,openai]"
```

## Quickstart

Add AgentLens before you create your provider client:

```python
import agentlens
agentlens.init(api_key="al_local")

import anthropic
client = anthropic.Anthropic()

@agentlens.run(name="customer_support_agent")
def run_agent(query):
    return client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=256,
        messages=[{"role": "user", "content": query}],
    )
```

Run your agent. AgentLens saves the trace locally:

```text
.agentlens/runs/<run_id>.json
```

## Diagnose

```bash
agentlens runs list
agentlens diagnose <run_id>
```

Example output:

```text
ROOT CAUSE:
tool_selection

FAILED AT:
Step 2 (search_web)

WHY:
Step 2 chose 'search_web' but the trace marks 'query_db' as the expected tool.

FIX:
Rewrite the tool descriptions so 'search_web' is clearly for external lookup and 'query_db' is clearly for this request, then route this case to 'query_db'.

CONFIDENCE: 0.94
```

## Supported Providers

- Anthropic: `client.messages.create(...)`
- OpenAI: `client.chat.completions.create(...)`
- OpenAI: `client.responses.create(...)`

## Local Evaluation

Run the built-in fixture evaluation:

```bash
agentlens evaluate
```

This checks the current diagnosis engine against known failure cases and any saved cases in `real_world_cases/`.

## What This Is Not

- no dashboard
- no hosted API
- no database
- no analytics platform
- no billing
- no auth

Phase 3 goal: get 10 real developers to try AgentLens on real broken agents and learn whether the diagnosis saves time.
