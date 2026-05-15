# AgentLens Terminal Demo

Short terminal recording script for a sub-60-second demo.

```text
$ python examples/phase2_failure_cases.py
Wrote tests/phase2_runs/phase2_tool_selection.json and .agentlens/runs/phase2_tool_selection.json
...

$ agentlens runs list
AgentLens Runs

run_id                                name                      status    timestamp                  spans
phase2_tool_selection                 tool_selection_case       error     2026-05-07T04:00:00+00:00  4

$ agentlens diagnose phase2_tool_selection
ROOT CAUSE:
tool_selection

FAILED AT:
Step 2 (search_web)

WHY:
Step 2 chose 'search_web' but the trace marks 'query_db' as the expected tool.

FIX:
Rewrite the tool descriptions so 'search_web' is clearly for external lookup and 'query_db' is clearly for this request, then route this case to 'query_db'.

SECONDARY:
None

CONFIDENCE: 0.94
```

Suggested caption:

AgentLens captures a broken agent run locally, then shows the exact failed step, why it failed, and the smallest useful fix.
