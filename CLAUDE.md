# CLAUDE.md — AgentLens

## The One-Line Pitch

> **When your AI agent breaks, AgentLens tells you exactly which decision caused it — and what to change. Not logs. Not traces. The answer.**

Works with: Anthropic · OpenAI · LangGraph · CrewAI · raw API

---

## What We Are Building

AgentLens is the **Sentry for AI agents**.

Sentry built a $245M ARR business on one idea: when traditional software breaks, Sentry catches the exception and tells you exactly where it happened. Every developer uses it. Two lines of code to install. Free to start. Paid when you need teams.

We are doing the same thing for AI agents — except the bug is not an exception. The bug is a **bad decision**. The agent chose the wrong tool. It looped without exit. It lost the original goal. It used corrupted tool output downstream. These failures don't throw errors — they silently produce wrong answers.

No existing tool catches this. LangSmith shows you traces. Langfuse shows you traces. AgentOps shows you replays. **AgentLens tells you which decision was wrong and what to change.** That is the entire product.

---

## The Market (Why Now)

- The agentic AI market hit **$10.8B in 2026**, up from $7.6B in 2025
- **79% of organizations** have adopted AI agents (PwC 2025) but most cannot trace failures through multi-step workflows
- Galileo AI raised **$68M** specifically on the "why did my agent fail" angle — proving investors believe in the category
- LangChain reached a **$1.1B valuation** ($100M Series B, Sequoia + Benchmark)
- Langfuse was **acquired by ClickHouse** (a $15B company) in January 2026
- Developer tools + AI is the #1 funded category at YC right now (~40% of recent batches)

The category is proven. The question is where AgentLens fits — and our research shows the exact gap nobody has filled.

---

## Competitive Landscape

| Tool | Strength | Weakness vs. AgentLens |
|---|---|---|
| **LangSmith** ($1.1B val) | Deep LangGraph integration, best traces | Cloud-only, LangChain-tied, no diagnosis |
| **Langfuse** (acq. ClickHouse) | Open-source, self-hostable, framework-agnostic | Still a traces tool — shows what happened, not why |
| **Galileo AI** ($68M raised) | "Agent reliability," Luna-2 evaluator, prescriptive fixes | 151-person company, full SaaS, not for solo devs |
| **AgentOps** | 400+ LLMs/frameworks, session replay, time-travel debug | No diagnosis — tells you what happened, not why |
| **Arize Phoenix** (Series C) | ML-grade rigor, enterprise-grade | Built for ML teams, not agent developers |
| **Helicone** | Simplest install, drop-in proxy | Logging only, no RCA |
| **Datadog LLM Obs.** | Enterprise default for Datadog shops | Massive platform buy-in required |
| **Sentry Seer** | AI debugging for traditional software errors | Does not understand AI agent decision logic |

### The Gap Nobody Has Filled

Every tool above is either:
1. **Traces only** — shows you what happened, you still have to figure out why
2. **Cloud-heavy** — requires signup, account, and often a paid plan to get started
3. **Framework-locked** — LangSmith only shines if you use LangChain
4. **Enterprise-grade** — Galileo and Arize are built for teams with budgets, not solo builders

**AgentLens is the only tool that is local-first, zero-signup, pip-installable, and gives you a specific diagnosis with a concrete fix.** That is our moat while we are small, and it is the right distribution strategy to build a user base before we need to raise money.

---

## The Unique Idea — "Sentry for AI Agents"

Sentry's playbook, applied to AI agents:

```
Sentry model:
  Free open-source SDK  →  2-line install  →  no cloud required  →  
  catches exceptions  →  paid cloud for teams + dashboards

AgentLens model:
  Free open-source SDK  →  2-line install  →  no cloud required  →
  catches bad decisions  →  paid cloud for teams + deeper LLM diagnosis
```

The framing immediately answers every question:
- **"What do you do?"** — Sentry for AI agents
- **"How is it different?"** — Sentry catches code exceptions. We catch agent decision failures.
- **"How do I try it?"** — `pip install agentlens`, two lines of code, done
- **"How do you make money?"** — Same as Sentry: free SDK forever, pay for cloud dashboards + team features

The reason this works: every developer building an AI agent will eventually have it break in a way they cannot explain. That moment — staring at a JSON trace trying to figure out what went wrong — is our acquisition moment.

---

## What We Have Built (Phase 1–3 Complete)

### SDK (`sdk/collector.py`)
- `agentlens.init()` monkeypatches `anthropic.Anthropic` and `openai.OpenAI` at import time
- Zero changes to existing agent code — just add two lines before your existing client
- `@agentlens.run(name="...")` decorator groups all spans into one run and auto-saves
- Captures: LLM calls, tool calls, errors, latency, token usage, stop reason
- Saves runs to `.agentlens/runs/<run_id>.json` — fully local, no cloud
- Works with: Anthropic `messages.create()`, OpenAI `chat.completions.create()`, OpenAI `responses.create()`

### Diagnosis Engine (`engine/`)
Full pipeline: `agentlens diagnose <run_id>` → preprocess spans → LLM or fallback → generate fix

- **Preprocess** (`preprocess.py`): converts raw spans to compact diagnosis input. Handles deduplication, malformed spans, 4000-char truncation, 200-span cap
- **Classify** (`classifier.py` + `diagnose.py`): LLM path (gpt-4.1-mini or claude-3-5-sonnet) if API key present, evidence-based fallback if not
- **Fix** (`fixes.py`): concrete fix template per failure category
- **Validate**: checks all required fields, confidence range, category is known

Six failure categories, all passing at 100% on internal fixtures:

| Category | What It Catches |
|---|---|
| `tool_selection` | Agent chose wrong tool due to ambiguous descriptions |
| `context_pollution` | Contradictory instructions diluted the goal |
| `loop` | Agent repeated same steps without exit |
| `state_drift` | Agent lost original goal mid-run |
| `cascade` | Bad tool output corrupted later steps |
| `overflow` | Important context pushed out of context window |

If confidence < 0.6, output shows `LOW CONFIDENCE` with likely causes instead of pretending certainty.

### CLI (`agentlens.py`)
```bash
agentlens runs list                  # show recent runs
agentlens runs show <run_id>         # inspect spans
agentlens diagnose <run_id>          # root cause analysis
agentlens anonymize <run_id>         # redact secrets before sharing
agentlens feedback-template <run_id> # structured feedback form
agentlens evaluate                   # fixture + real-world accuracy check
```

### Launch Materials (ready to send)
- `launch/reddit_post.md` — r/LocalLLaMA, r/MachineLearning
- `launch/hn_post.md` — Hacker News Show HN
- `launch/twitter_post.md` — X/Twitter thread
- `launch/discord_post.md` — LangChain Discord, AI builder communities
- `launch/dm_template.md` — direct outreach to developers
- `feedback/outreach.csv` — outreach pipeline tracker
- `feedback/users.csv` — beta user tracker
- `docs/beta_onboarding_script.md` — onboarding under 10 minutes

### Evaluation Infrastructure
- 6 fixture runs in `tests/phase2_runs/` covering all 6 categories
- `agentlens evaluate` splits fixture accuracy from real-world accuracy
- `real_world_cases/` folder for anonymized user traces + expected diagnosis

---

## What Does Not Work Yet

These are the remaining gaps between what we have and the full vision:

| Gap | Impact | Priority |
|---|---|---|
| **No async support** | Async Anthropic/OpenAI calls bypass tracing entirely | 🔴 High — blocks most production agents |
| **No LangGraph integration** | LangGraph users get no node-level spans | 🔴 High — LangGraph is the dominant framework |
| **No CrewAI integration** | CrewAI debugging is "painful" per developer reports | 🟡 Medium |
| **Tool results are manual** | Devs must call `record_tool_result()` after each tool | 🟡 Medium |
| **0 real users** | Internal fixture accuracy ≠ real-world accuracy | 🔴 Critical — Phase 3 blocker |

---

## Completed Fixes (2026-05-18 audit)

The following bugs and architectural issues were found in an internal audit and resolved:

| ID | File | What Changed |
|---|---|---|
| P1-1 | `agentlens.py` | `diagnose_run` exception no longer surfaces as a Python traceback — caught as `ValueError` with a clean message |
| P1-2 | `agentlens_engine/diagnose.py` | All LLM call bodies wrapped in `try/except Exception: return None` so bad API keys or network errors fall through to offline fallback |
| P1-3 | `agentlens_sdk/collector.py` | `capture_tool_results_from_messages` now resolves the true tool name from prior `llm_call` spans via `tool_use_id` instead of always labelling results `"anthropic"` |
| P1-4 | `agentlens_engine/evaluate.py` | `fixture_dir` and `real_world_dir` defaults are now module-relative (`Path(__file__).resolve().parents[1]`), so `agentlens evaluate` and `agentlens doctor` work from any directory |
| P1-5 | `examples/anthropic_broken_agent.py` | Block type read via `getattr`/`dict.get` to handle real SDK objects; `next()` now has a `None` default to avoid `StopIteration` |
| P2-1 | `agentlens_engine/classifier.py` | `_detect_state_drift` hard-coded CRM guard removed; state drift is now detectable for any agent domain |
| P2-2 | `agentlens_sdk/collector.py` | `AgentLensClient.messages_create` retired its duplicated capture logic and now delegates to `_AnthropicMessagesProxy` |
| P2-3 | `agentlens_engine/preprocess.py` | `_find_failure_step` fallback changed from `steps[-1]["step"]` to `0` to avoid false diagnostic window anchoring |
| P2-4 | `pyproject.toml`, `agentlens.py` | `engine/` renamed to `agentlens_engine/`, `sdk/` renamed to `agentlens_sdk/` — eliminates top-level namespace collision risk |
| P2-5 | `agentlens_sdk/collector.py` | `load_run` prefix match now prints an explicit message when multiple runs match instead of silently returning `None` |
| P2-6 | `agentlens_engine/diagnose.py` | `_anthropic_text` backtick stripping uses `re.sub` instead of `str.strip("`")` which stripped content characters |
| P3-1 | _(deleted)_ | `engine/analyze.py` (legacy Phase 0 `steps`-format analyzer) deleted |
| P3-2 | _(deleted)_ | `tests/broken_agent.py`, `tests/real_trace.json`, `tests/sample_trace.json` (all Phase 0 `steps`-format artifacts) deleted |
| P3-3 | `tests/generate_phase2_runs.py` | Fixture generator moved from `examples/phase2_failure_cases.py` to `tests/generate_phase2_runs.py` |
| P3-4 | `agentlens_sdk/collector.py` | `_collect_tool_calls` now skips the `tool_calls` key during recursion to prevent double-collecting already-seen tool calls |
| P3-5 | `agentlens_engine/classifier.py`, `agentlens_engine/preprocess.py` | `_tool_call_signature` extracted as a shared helper; loop detection logic no longer duplicated |
| P3-6 | `agentlens_engine/classifier.py` | `_detect_state_drift` keywords expanded to catch domain-agnostic drift signals beyond weather/restaurant |
| P3-7 | `agentlens.py` | `_doctor_tool_selection_run` loads from `tests/phase2_runs/phase2_tool_selection.json` when present, falling back to inline dict |
| P3-8 | `agentlens.py` | `_doctor_imports` replaced vacuous `importlib.import_module("agentlens")` self-check with `agentlens.init` callable check |
| P3-9 | `examples/shared_tools.py` | `search_web` extracted from both example files into `examples/shared_tools.py` |

---

## Current Status: Phase 3 Active

| Phase | Status |
|---|---|
| Phase 0 — rule-based analyzer | ✅ Done |
| Phase 1 — SDK, CLI, local storage | ✅ Done |
| Phase 2 — LLM diagnosis engine | ✅ Done |
| Phase 3 — beta users, real traces | 🔴 0/10 users, 0 real traces |

**Phase 3 is not done until:**
- 10 real developers test AgentLens on real broken agents
- 3 say they would pay
- 2 unexpected real-world failure modes are documented

**The only thing blocking Phase 3 right now is sending the outreach. The materials are written.**

---

## The Way Ahead — Ordered by Impact

### Immediate (this week) — Get Real Users

This is the highest-leverage action available. Nothing else matters until real traces come in.

1. Post the HN Show HN (`launch/hn_post.md`) — this is the single highest-reach action
2. Post to r/LocalLLaMA and r/MachineLearning (`launch/reddit_post.md`)
3. Post in LangChain Discord and AI builder Discords (`launch/discord_post.md`)
4. DM 10 developers you can identify who have posted about broken agents (`launch/dm_template.md`)
5. Track every reply in `feedback/outreach.csv` immediately

**Success signal:** 3 developers install and run `agentlens diagnose` on a real trace.

### Short-term (1–2 weeks) — Fix the Critical Bugs

Once real traces come in, these will be the first things that break:

1. **Add async support** — patch `async def create()` in `_AnthropicMessagesProxy` and `_OpenAICompletionsProxy`. Without this, any agent using `await client.messages.create(...)` is invisible to AgentLens. Most production agents are async.
2. **LangGraph integration** — wrap `StateGraph.invoke()` and `stream()` to capture node-level spans. LangGraph has the best debugging story today (via LangSmith) — AgentLens needs to match it.
3. **Retire or rewrite `engine/analyze.py`** — it uses the old `steps` format and will confuse any developer who finds it. Either delete it or rewrite it to consume `spans`.

### Medium-term (1 month) — Sharpen the Diagnosis

Once real user traces come in, the diagnosis engine will expose its weaknesses:

1. Expand failure categories based on what real traces actually show
2. Improve the fallback classifier — current evidence detection is keyword-based and fragile
3. Add CrewAI integration — CrewAI's "verbose mode" produces unstructured logs; wrap the crew `kickoff()` path
4. Fix `_find_tool_calls` deduplication for nested OpenAI responses
5. Fix `_is_error_output` false positives on dicts with non-error `"error"` keys

### Growth Path — Three Real Options

**Option 1 — Apply to YC**
Strongest pitch: "We're Sentry for AI agents. Pip install, two lines of code, no cloud, tells you exactly which decision broke your agent." Developer tools + AI + local-first is exactly what YC funds. Apply to the next batch. The application writes itself if you have even 5 real users with quotes.

**Option 2 — Bootstrapped SaaS**
Free SDK forever. Paid cloud dashboard at $20–50/month per developer for: shared run history, cross-agent comparison, team-level diagnosis, and LLM-powered analysis without needing your own API key. 1000 developers = $20–50K MRR. Very achievable before raising.

**Option 3 — Build to Sell**
The most likely acquirers:
- **Sentry** — they just launched "Seer" (AI debugging for traditional software). They need the AI agent side. AgentLens fits exactly.
- **Datadog** — expanding aggressively into LLM observability. Would buy a developer-beloved SDK.
- **LangChain** — want the framework-agnostic diagnosis layer to complement LangSmith.

All three paths require the same thing first: real traction, real users, real quotes.

---

## North Star Metric

**Number of developers who run `agentlens diagnose` on a real (not synthetic) broken agent and say the diagnosis saved them time.**

Everything else — async support, LangGraph integration, cloud dashboard, YC application — is secondary to this number being greater than zero.

---

## Business Model (When Ready)

```
Free forever:
  - SDK (open source, pip install)
  - Local run storage
  - CLI diagnosis (with your own API key or offline fallback)
  - 6 failure categories

Paid (planned ~$20–50/month):
  - Cloud run storage + history
  - Team run sharing
  - LLM diagnosis without your own API key
  - Cross-agent comparison
  - Slack/email alerts on high-confidence failures

Enterprise (planned):
  - SSO
  - On-prem trace storage
  - Priority support
  - Custom failure categories
```

---

## Install & Dev Notes

```bash
git clone https://github.com/abishekgiri/agentlens-.git
cd agentlens-
pip install -e .                          # local editable install
pip install -e ".[anthropic,openai]"      # with provider SDKs
```

```bash
python examples/anthropic_broken_agent.py  # run a broken agent
agentlens runs list                         # see saved runs
agentlens diagnose <run_id>                 # diagnose it
agentlens evaluate                          # check fixture accuracy
```

- `AGENTLENS_OPENAI_MODEL` env var overrides the diagnosis model (default: gpt-4.1-mini)
- `AGENTLENS_ANTHROPIC_MODEL` env var overrides the Anthropic diagnosis model (default: claude-3-5-sonnet-latest)
- No API key required — fallback classifier works fully offline
- Add real-world cases: drop `trace.json` + `expected_diagnosis.json` in `real_world_cases/<name>/`

---

## Known Risks

- **Diagnosis trust**: one confident-but-wrong diagnosis on a real trace will erode trust fast. Confidence calibration matters more than category accuracy.
- **Async gap**: most production agents are async. Until async is patched, real-world capture is severely limited.
- **Framework gap**: LangGraph is the dominant agent framework. No integration = invisible to the largest user segment.
- **Galileo competition**: they are well-funded and moving toward the same "why did it fail" positioning. Differentiation must stay sharp — we are local-first, zero-signup, and built for individual developers, not enterprise teams.
- **Sparse traces**: the fallback classifier depends on explicit string evidence. Real production traces from well-written agents may be sparse and produce low-confidence output at a high rate.

---

## Project Structure

```
agentlens/
├── agentlens.py               # Public SDK + CLI entrypoint (main())
├── agentlens_sdk/
│   ├── __init__.py            # Re-exports: AgentLensClient, init, run, record_tool_result, save_run
│   └── collector.py           # Core SDK: monkeypatching, span capture, run storage
├── agentlens_engine/
│   ├── __init__.py
│   ├── preprocess.py          # Converts SDK spans → compact diagnosis input
│   ├── classifier.py          # Evidence-based fallback + LLM prompt builder
│   ├── diagnose.py            # Diagnosis pipeline: LLM first, fallback if no API key
│   ├── fixes.py               # Fix templates per failure category
│   └── evaluate.py            # Fixture + real-world case evaluation runner
├── examples/
│   ├── shared_tools.py        # Shared fake tool implementations
│   ├── anthropic_broken_agent.py   # Fake Anthropic client demo
│   └── openai_broken_agent.py      # Fake OpenAI client demo
├── tests/
│   ├── generate_phase2_runs.py     # Regenerates the 6 fixture JSON runs
│   └── phase2_runs/               # 6 fixture JSON runs for evaluate
├── docs/                      # Beta process, trust failure tracking, onboarding
├── launch/                    # Reddit, HN, Twitter, Discord, DM templates (READY TO SEND)
├── real_world_cases/          # Drop anonymized real user traces here
├── feedback/
│   ├── users.csv              # Beta user tracking
│   └── outreach.csv           # Outreach pipeline
├── demo/terminal_recording.md # Terminal demo script
├── pyproject.toml             # pip install -e . entrypoint
├── README.md                  # External-facing docs
└── codex.md                   # Internal build log (gitignored)
```
