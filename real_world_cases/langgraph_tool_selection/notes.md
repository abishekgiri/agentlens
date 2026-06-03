# LangGraph Tool Selection Regression Case

Date captured: 2026-05-21

## Source

- External repo: `langchain-ai/langgraph`
- Workflow: LangGraph prebuilt ReAct agent pattern using `create_react_agent`
- Model: LangGraph fake tool-calling model from the public repo tests
- Provider keys: none used

## Failure

The agent selected `search_web` for a local customer renewal lookup. The correct tool should have been `query_db`.

The two tools intentionally had ambiguous descriptions:

- `search_web`: `find info about a topic`
- `query_db`: `find info about a topic`

`search_web` returned an error saying customer renewal records were only available in `query_db`.

## Expected Diagnosis

- Category: `tool_selection`
- Failed step: `2`
- Failed tool: `search_web`

## Actual Diagnosis

AgentLens correctly diagnosed `tool_selection`, identified step 2, named `search_web`, and gave a concrete fix.

## Trust Notes

This is a good regression case because the diagnosis is tied to concrete trace evidence:

- selected tool name
- ambiguous tool descriptions
- tool output saying the data belonged elsewhere

## Caveat

This was not a live provider run. Because no OpenAI or Anthropic API key was available, the LangGraph workflow used a local fake model and the harness recorded the fake model decision into AgentLens.
