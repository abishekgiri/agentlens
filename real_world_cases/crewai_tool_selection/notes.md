# CrewAI Tool Selection Regression Case

Date captured: 2026-06-03

## Source

- External repo: `crewAIInc/crewAI`
- Workflow: CrewAI `Agent` + `Task` + `Crew`
- Model: local custom `BaseLLM` implementation using CrewAI's documented custom LLM path
- Provider keys: none used

## Failure

The CrewAI agent selected `search_tickets` for a billing refund lookup. The correct tool should have been `query_billing_db`.

The two tools intentionally had overlapping descriptions:

- `search_tickets`: `find customer information by topic`
- `query_billing_db`: `find customer information by topic`

`search_tickets` returned an error saying refund records were only available in `query_billing_db`.

## Expected Diagnosis

- Category: `tool_selection`
- Failed step: `2`
- Failed tool: `search_tickets`

## Actual Diagnosis

AgentLens correctly diagnosed `tool_selection`, identified step 2, named `search_tickets`, and gave a concrete tool-description/routing fix.

## Trust Notes

This is a useful external regression case because it uses CrewAI's actual agent/task/crew orchestration while keeping the LLM local and deterministic.

An earlier CrewAI harness run produced low confidence because the trace said no callable was available, which did not contain enough evidence for a strong wrong-tool diagnosis. That low-confidence behavior was appropriate. The final saved case includes the intended realistic tool error.

## Caveat

This was not a live provider run. The workflow used CrewAI's custom LLM extension point because no OpenAI or Anthropic API key was available.
