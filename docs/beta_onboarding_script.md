# Beta Onboarding Script

Goal: get from zero to one diagnosis in under 10 minutes.

## 1. Install

```bash
git clone https://github.com/abishekgiri/agentlens-.git
cd agentlens-
pip install -e .
```

If they use Anthropic or OpenAI locally:

```bash
pip install -e ".[anthropic,openai]"
```

## 2. Add AgentLens

Add this before creating the model client:

```python
import agentlens
agentlens.init(api_key="al_local")
```

Wrap the broken agent run:

```python
@agentlens.run(name="my_broken_agent")
def run_agent():
    ...
```

## 3. Run Diagnosis

```bash
agentlens runs list
agentlens diagnose <run_id>
```

## 4. Anonymize Trace

```bash
agentlens anonymize <run_id>
```

This writes:

```text
<run_id>.anonymized.json
```

Ask the user to review it before sharing.

## 5. Send Feedback

```bash
agentlens feedback-template <run_id>
```

Ask for:

- What broke?
- Was diagnosis correct?
- Did the fix work?
- What was confusing?
- Would they use it again?
- Would they pay?

## Common Setup Issues

- Wrong Python environment: run `which python` and `which agentlens`.
- Package not installed: rerun `pip install -e .`.
- Provider SDK missing: install the optional provider extra.
- No run appears: confirm the code is inside `@agentlens.run(...)`.
- Trace has secrets: run `agentlens anonymize <run_id>` and manually review output.
- Diagnosis is low confidence: ask for the anonymized trace and do not overclaim.
