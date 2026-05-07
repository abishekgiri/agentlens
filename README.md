# AgentLens

AgentLens is a Python SDK that captures AI agent runs as structured JSON so failures can later be diagnosed.

It is focused on one job: make broken agent runs inspectable locally.

## What AgentLens Is Not

- not a web UI
- not a hosted API
- not analytics
- not a database
- not prompt management
- not eval infrastructure
- not cost monitoring

## Install

Local install placeholder:

```bash
pip install -e .
```

Optional provider SDKs:

```bash
pip install -e ".[anthropic,openai]"
```

## Two-Line Setup

```python
import agentlens
agentlens.init(api_key="al_local")

import anthropic
client = anthropic.Anthropic()
```

After `agentlens.init(...)`, supported provider clients are intercepted automatically.

## Run Context

```python
import agentlens

agentlens.init(api_key="al_local")

@agentlens.run(name="customer_support_agent")
def run_agent(query):
    ...
```

All captured LLM calls, tool selections, tool outputs, and errors inside the function are grouped under one `run_id`.

Runs are saved locally in:

```text
.agentlens/runs/<run_id>.json
```

## CLI

List recent local runs:

```bash
agentlens runs list
```

Show one run:

```bash
agentlens runs show <run_id>
```

Phase 2 RCA placeholder:

```bash
agentlens diagnose <run_id>
```

For now, `diagnose` prints:

```text
RCA engine is coming in Phase 2. Run captured successfully.
```

## Examples

Run the Anthropic-style broken agent:

```bash
python examples/anthropic_broken_agent.py
agentlens runs list
agentlens runs show <run_id>
```

Run the OpenAI-style broken agent:

```bash
python examples/openai_broken_agent.py
agentlens runs list
agentlens runs show <run_id>
```

Both examples define two deliberately ambiguous tools:

- `search_web`: `find info about a topic`
- `query_db`: `find info about a topic`

The model chooses `search_web`, the tool fails, and AgentLens captures the run locally.

## Captured Data

AgentLens currently captures:

- run name
- run ID
- start and end timestamps
- run status
- provider name
- model
- input messages
- tools passed to the model
- response content
- stop reason
- token usage
- latency
- tool selections
- tool outputs
- errors

## Phase 0 Analyzer

The earlier Phase 0 CLI analyzer still exists:

```bash
python engine/analyze.py tests/sample_trace.json
```

Phase 2 will connect captured runs to real RCA logic. Week 2 only adds capture and viewing.

## Phase 1 Done Criteria

Phase 1 is done when:

- developer can install locally
- developer adds two lines
- broken agent runs
- JSON trace appears automatically
- CLI shows trace in readable format
- Anthropic capture works
- OpenAI capture works
- `codex.md`, `.agentlens/`, `.env`, API keys, and generated run JSON files are not committed
