# Phase 3 Weekly Review

Current status: Phase 3 is active, not complete.

## Real Users

- Real developers onboarded: 0
- Outreach sent: 0
- Replies: 0
- Installs: 0
- Successful real broken-agent runs: 0
- Traces received: 0
- Confirmed useful diagnoses: 0
- Payment signals: 0
- Target: 10

## External / Real-World Cases

- External OSS validations: 2
- External repos tested: `langchain-ai/langgraph`, `crewAIInc/crewAI`
- Regression cases saved: 2
- Regression folders: `real_world_cases/langgraph_tool_selection/`, `real_world_cases/crewai_tool_selection/`
- Live provider validations: 0
- Live provider status: blocked because no `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` was available.

## Diagnosis Accuracy

- Confirmed real-world diagnoses: 0
- Correct real-world diagnoses: 0
- Accuracy estimate: unknown
- Target: around 70%+
- External OSS regression accuracy: 2/2 so far.
- Note: External OSS regression accuracy is not a substitute for real user accuracy.

## Confidence Calibration

- Unknown for real traces.
- Current rule: low confidence is preferred over a confident unsupported diagnosis.

## Most Common Failure Types

- Real user traces: unknown until real traces arrive.
- External OSS validations observed `tool_selection`.

## Most Useful Fixes

- Unknown until users try suggested fixes.
- External OSS validations produced actionable tool-description/routing fixes, but no real user has confirmed they saved time yet.

## Biggest Trust Failures

- Not observed yet from real users.
- Live provider validation is still missing, which remains a trust gap.
- Risk: users may distrust overconfident diagnoses if traces are sparse or messy.
- Track every miss in `docs/trust_failures.md`.

## What Users Actually Care About

- Unknown until beta calls.
- Hypothesis: exact failed step, concrete fix, and whether the explanation matches their trace.

## Biggest Onboarding Friction

- Unknown until the first beta call.
- Track install friction and setup confusion in `feedback/users.csv`.
- Track recurring setup failures in `docs/onboarding_failures.md`.
- Known setup blocker: real provider validation requires a valid OpenAI or Anthropic key.

## Top User Requests

- Unknown until real beta calls.

## UI vs Accuracy

- No evidence users need UI yet.
- Current priority remains better diagnosis accuracy from real traces.

## Exit Criteria

Do not move to Phase 4 until all are true:

- 10+ real developers used AgentLens.
- Around 70%+ confirmed diagnosis usefulness.
- At least 3 users explicitly said they would pay.
- Onboarding friction is manageable.
- Users trust diagnoses.
- Real-world traces validate the RCA engine.

## Next Actions

- Stop internal OSS validation unless a new real-user trace reveals a failure mode.
- Run live provider validation once a real OpenAI or Anthropic API key is available.
- DM 10 target developers using `launch/dm_template.md`.
- Run one beta user through `docs/beta_test_checklist.md`.
- Use `docs/beta_onboarding_script.md` during onboarding.
- Save anonymized traces in `real_world_cases/`.
- Use `agentlens anonymize <run_id>` before asking for a shared trace.
- Use `agentlens feedback-template <run_id>` after diagnosis.
- Update `feedback/users.csv` after every interaction.
- Update `feedback/outreach.csv` after every outreach attempt.
- Add unknown patterns to `docs/new_failure_patterns.md` instead of expanding categories immediately.
- Add trust failures to `docs/trust_failures.md`.
- Run `agentlens evaluate` after each real-world case is added.
