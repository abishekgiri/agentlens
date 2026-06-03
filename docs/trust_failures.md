# Trust Failures

Track every case where the user does not trust the diagnosis.

This is more important than adding new features.

## Categories

- Hallucinated diagnosis
- Wrong confidence
- Vague fix
- Incorrect failed step
- Misleading explanation
- User could not map fix back to their code
- Trace was too sparse for a confident answer

## Template

### Case name

- Date:
- User/source:
- Trace folder:
- Diagnosis category:
- Confidence:
- What failed:
- Why the user did not trust it:
- What evidence the engine missed:
- Follow-up change:
- Should this become a regression case:

## Current Log

### LangGraph tool selection validation

- Date: 2026-06-02
- User/source: External OSS validation using `langchain-ai/langgraph`
- Trace folder: `real_world_cases/langgraph_tool_selection/`
- Diagnosis category: `tool_selection`
- Confidence: `0.90`
- What failed: No trust failure observed. AgentLens correctly identified `search_web` as the failed tool-selection step.
- Why the user did not trust it: Not applicable.
- What evidence the engine missed: None observed for this case.
- Follow-up change: Preserve as a regression case and continue testing on real provider traces.
- Should this become a regression case: Yes.

### Live provider validation gap

- Date: 2026-06-02
- User/source: Local environment check
- Trace folder: Not available
- Diagnosis category: Not available
- Confidence: Not available
- What failed: No OpenAI or Anthropic API key was available, so live provider validation could not be run.
- Why the user did not trust it: Not a diagnosis failure, but it remains a product trust gap until tested with a real provider call.
- What evidence the engine missed: No live trace existed.
- Follow-up change: Run one real OpenAI or Anthropic workflow before treating Phase 3 validation as strong.
- Should this become a regression case: No, but it should remain tracked as a validation blocker.
