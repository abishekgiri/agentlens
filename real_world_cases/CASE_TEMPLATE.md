# Real-World Case Template

Create one folder per beta-user case.

```text
real_world_cases/<case_name>/
├── trace.json
├── expected_diagnosis.json
├── actual_diagnosis.txt
└── notes.md
```

## `trace.json`

Anonymized AgentLens run JSON. Remove secrets, API keys, user data, internal URLs, and proprietary prompts unless the user explicitly approves sharing them.

## `expected_diagnosis.json`

Use this after manual review or user confirmation:

```json
{
  "root_cause_category": "tool_selection",
  "failed_at_step": 2,
  "confidence_min": 0.6,
  "confidence_max": 1.0
}
```

## `actual_diagnosis.txt`

Paste the CLI output:

```bash
agentlens diagnose <run_id>
```

## `notes.md`

Record:

- whether the user confirmed correctness
- whether the fix worked
- what was confusing
- whether they would pay
- any trust failures
