/**
 * AgentLens Node.js SDK
 *
 * Local trace capture for AI agent debugging.
 *
 * Quick start:
 *   import { init, run, recordToolResult } from 'agentlens-sdk';
 *
 *   init();
 *
 *   await run('my-agent', async () => {
 *     const client = new Anthropic();             // auto-captured
 *     const response = await client.messages.create({ ... });
 *     return response;
 *   });
 */

import { AsyncLocalStorage } from 'node:async_hooks';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as crypto from 'node:crypto';

// ── Types ───────────────────────────────────────────────────────────────────

export interface Span {
  id: string;
  run_id: string;
  type: 'llm_call' | 'tool_call' | 'error' | 'memory_snapshot';
  ts: string;
  [key: string]: unknown;
}

export interface Run {
  run_id: string;
  name: string;
  started_at: string;
  ended_at: string | null;
  status: 'running' | 'success' | 'error';
  parent_run_id?: string;
  spans: Span[];
  error?: string;
}

export interface TraceContext {
  parent_run_id: string;
}

export interface InitOptions {
  /** API key (reserved for future cloud use — not required for local capture). */
  apiKey?: string;
  /** Propagate a parent trace context for multi-agent stitching. */
  parentContext?: TraceContext;
}

export interface RunOptions {
  parentRunId?: string;
}

// ── Pricing ─────────────────────────────────────────────────────────────────

const PRICE_TABLE: Record<string, [number, number]> = {
  // Anthropic  (input $/M, output $/M)
  'claude-opus-4':      [15.00, 75.00],
  'claude-sonnet-4':    [ 3.00, 15.00],
  'claude-3-5-sonnet':  [ 3.00, 15.00],
  'claude-3-5-haiku':   [ 0.80,  4.00],
  'claude-3-opus':      [15.00, 75.00],
  'claude-3-sonnet':    [ 3.00, 15.00],
  'claude-3-haiku':     [ 0.25,  1.25],
  // OpenAI
  'gpt-4o-mini':        [ 0.15,  0.60],
  'gpt-4o':             [ 2.50, 10.00],
  'gpt-4.1-nano':       [ 0.10,  0.40],
  'gpt-4.1-mini':       [ 0.40,  1.60],
  'gpt-4.1':            [ 2.00,  8.00],
  'gpt-4-turbo':        [10.00, 30.00],
  'gpt-4':              [30.00, 60.00],
  'gpt-3.5-turbo':      [ 0.50,  1.50],
  'o1-mini':            [ 3.00, 12.00],
  'o1':                 [15.00, 60.00],
  'o3-mini':            [ 1.10,  4.40],
  'o3':                 [10.00, 40.00],
};

function computeCostUsd(
  model: string | undefined,
  usage: Record<string, number> | undefined,
): number {
  if (!model || !usage) return 0;
  const m = model.toLowerCase();
  let best = '';
  for (const key of Object.keys(PRICE_TABLE)) {
    if (m.startsWith(key) && key.length > best.length) best = key;
  }
  if (!best) return 0;
  const [inPrice, outPrice] = PRICE_TABLE[best];
  const inputTok  = (usage.input_tokens  ?? 0) + (usage.prompt_tokens     ?? 0);
  const outputTok = (usage.output_tokens ?? 0) + (usage.completion_tokens ?? 0);
  return Math.round((inputTok * inPrice + outputTok * outPrice) / 1_000_000 * 1e8) / 1e8;
}

// ── Internal state ───────────────────────────────────────────────────────────

const storage = new AsyncLocalStorage<Run>();
let RUNS_DIR = path.join('.agentlens', 'runs');

const _cfg = {
  initialized: false,
  patchedAnthropic: false,
  patchedOpenAI: false,
  parentRunId: undefined as string | undefined,
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function nowIso(): string {
  return new Date().toISOString();
}

function newUuid(): string {
  return crypto.randomUUID();
}

function toJsonable(value: unknown): unknown {
  if (value === null || value === undefined) return value;
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value;
  if (Array.isArray(value)) return value.map(toJsonable);
  if (value instanceof Error) return { message: value.message, name: value.name };
  if (typeof value === 'object') {
    if (typeof (value as { toJSON?: () => unknown }).toJSON === 'function') {
      return toJsonable((value as { toJSON: () => unknown }).toJSON());
    }
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as object)) out[k] = toJsonable(v);
    return out;
  }
  return String(value);
}

function appendSpan(spanData: Omit<Span, 'id' | 'run_id'>): Span {
  const r = storage.getStore();
  if (!r) {
    // No active run — orphan span (best-effort, not persisted)
    return { id: newUuid(), run_id: 'orphan', ...spanData } as Span;
  }
  const span: Span = { id: newUuid(), run_id: r.run_id, ...spanData } as Span;
  r.spans.push(span);
  return span;
}

function saveRun(runData: Run): void {
  try {
    fs.mkdirSync(RUNS_DIR, { recursive: true });
    const filePath = path.join(RUNS_DIR, `${runData.run_id}.json`);
    fs.writeFileSync(filePath, JSON.stringify(runData, null, 2), 'utf8');
  } catch {
    // Best-effort — never crash the user's agent
  }
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Initialize AgentLens. Patches Anthropic and OpenAI SDKs if installed.
 * Call once at process start before creating any LLM clients.
 */
export function init(options: InitOptions = {}): void {
  if (options.parentContext?.parent_run_id) {
    _cfg.parentRunId = options.parentContext.parent_run_id;
  }
  if (!_cfg.initialized) {
    patchAnthropic();
    patchOpenAI();
    _cfg.initialized = true;
  }
}

/**
 * Run an async function within a named AgentLens run.
 * All spans created inside fn() are automatically attached to this run and saved.
 *
 * @example
 * await run('customer-support-agent', async () => {
 *   const client = new Anthropic();
 *   return client.messages.create({ ... }); // auto-captured
 * });
 */
export async function run<T>(
  name: string,
  fn: () => Promise<T>,
  options: RunOptions = {},
): Promise<T> {
  const runData: Run = {
    run_id: newUuid(),
    name,
    started_at: nowIso(),
    ended_at: null,
    status: 'running',
    spans: [],
    ...(options.parentRunId ?? _cfg.parentRunId
      ? { parent_run_id: options.parentRunId ?? _cfg.parentRunId }
      : {}),
  };

  return storage.run(runData, async () => {
    try {
      const result = await fn();
      runData.status = 'success';
      return result;
    } catch (err) {
      runData.status = 'error';
      runData.error = String(err);
      appendSpan({ type: 'error', ts: nowIso(), error: String(err), context: { function: name } });
      throw err;
    } finally {
      runData.ended_at = nowIso();
      // Promote to error if any error spans exist
      if (runData.status === 'success' && runData.spans.some(s => s.type === 'error')) {
        runData.status = 'error';
      }
      saveRun(runData);
    }
  });
}

/**
 * Get the current run's trace context for multi-agent propagation.
 * Pass the returned object to init() in the child process / service.
 *
 * @example
 * const ctx = getTraceContext();
 * // In the child agent:
 * init({ parentContext: ctx });
 */
export function getTraceContext(): TraceContext | null {
  const r = storage.getStore();
  if (!r) return null;
  return { parent_run_id: r.run_id };
}

/**
 * Manually record a tool result span.
 * Use this when you call a tool outside the auto-captured LLM response loop.
 */
export function recordToolResult(options: {
  toolName: string;
  input?: unknown;
  output?: unknown;
  toolUseId?: string;
}): void {
  appendSpan({
    type: 'tool_call',
    ts: nowIso(),
    tool_name: options.toolName,
    input: toJsonable(options.input) ?? null,
    output: toJsonable(options.output) ?? null,
    tool_use_id: options.toolUseId ?? null,
  });
}

/**
 * Capture a snapshot of agent memory / state at the current point in time.
 * Enables the Memory State Snapshots view in the timeline UI.
 *
 * @example
 * recordMemorySnapshot('after_lookup', { customer: 'alex', status: 'active' });
 */
export function recordMemorySnapshot(label: string, state: Record<string, unknown>): void {
  appendSpan({
    type: 'memory_snapshot',
    ts: nowIso(),
    label,
    state: toJsonable(state),
  });
}

// ── Anthropic patch ──────────────────────────────────────────────────────────

function patchAnthropic(): void {
  if (_cfg.patchedAnthropic) return;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const sdk = require('@anthropic-ai/sdk') as { Anthropic: new (...args: unknown[]) => unknown };
    const OriginalAnthropic = sdk.Anthropic;

    // Wrap the constructor with a Proxy so every new Anthropic() instance gets patched.
    sdk.Anthropic = new Proxy(OriginalAnthropic, {
      construct(Target, args) {
        const instance = new Target(...args) as {
          messages: { create: (...a: unknown[]) => Promise<unknown>; stream: (...a: unknown[]) => unknown };
        };

        const origCreate = instance.messages.create.bind(instance.messages);
        instance.messages.create = async (params: Record<string, unknown>) => {
          const started = Date.now();
          const msgs = params['messages'] ?? [];
          try {
            const response = await origCreate(params);
            const resp = response as { content?: unknown; stop_reason?: string; usage?: Record<string, number> };
            const content = toJsonable(resp.content);
            const usage = resp.usage;
            const model = params['model'] as string | undefined;
            appendSpan({
              type: 'llm_call',
              provider: 'anthropic',
              ts: nowIso(),
              latency_ms: Date.now() - started,
              input_messages: toJsonable(msgs),
              tools: toJsonable(params['tools'] ?? []),
              model,
              response_content: content,
              stop_reason: resp.stop_reason ?? null,
              usage: toJsonable(usage),
              cost_usd: computeCostUsd(model, usage),
            });
            return response;
          } catch (err) {
            appendSpan({
              type: 'error',
              ts: nowIso(),
              latency_ms: Date.now() - started,
              error: String(err),
              context: { provider: 'anthropic', model: params['model'] },
            });
            throw err;
          }
        };

        // Patch streaming too
        if (typeof instance.messages.stream === 'function') {
          const origStream = instance.messages.stream.bind(instance.messages);
          instance.messages.stream = (params: Record<string, unknown>) => {
            const started = Date.now();
            const ctx = origStream(params) as {
              __enter__?: () => unknown;
              on?: (event: string, cb: (...a: unknown[]) => void) => unknown;
              getFinalMessage?: () => Promise<unknown>;
              [Symbol.asyncIterator]?: () => AsyncIterator<unknown>;
            };
            // Wrap with a finalizer that captures the span
            const originalGetFinalMessage = ctx.getFinalMessage?.bind(ctx);
            if (originalGetFinalMessage) {
              ctx.getFinalMessage = async () => {
                const message = await originalGetFinalMessage();
                const msg = message as { content?: unknown; stop_reason?: string; usage?: Record<string, number> };
                const content = toJsonable(msg.content);
                const usage = msg.usage;
                const model = params['model'] as string | undefined;
                appendSpan({
                  type: 'llm_call',
                  provider: 'anthropic',
                  ts: nowIso(),
                  latency_ms: Date.now() - started,
                  input_messages: toJsonable(params['messages'] ?? []),
                  tools: toJsonable(params['tools'] ?? []),
                  model,
                  response_content: content,
                  stop_reason: msg.stop_reason ?? null,
                  usage: toJsonable(usage),
                  cost_usd: computeCostUsd(model, usage),
                  streaming: true,
                });
                return message;
              };
            }
            return ctx;
          };
        }

        return instance;
      },
    });

    _cfg.patchedAnthropic = true;
  } catch {
    // @anthropic-ai/sdk not installed — skip silently
  }
}

// ── OpenAI patch ─────────────────────────────────────────────────────────────

function patchOpenAI(): void {
  if (_cfg.patchedOpenAI) return;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const sdk = require('openai') as { OpenAI: new (...args: unknown[]) => unknown };
    const OriginalOpenAI = sdk.OpenAI;

    sdk.OpenAI = new Proxy(OriginalOpenAI, {
      construct(Target, args) {
        const instance = new Target(...args) as {
          chat: { completions: { create: (...a: unknown[]) => Promise<unknown> } };
        };

        const origCreate = instance.chat.completions.create.bind(instance.chat.completions);
        instance.chat.completions.create = async (params: Record<string, unknown>) => {
          const started = Date.now();
          try {
            const response = await origCreate(params);
            const rj = toJsonable(response) as Record<string, unknown> | null;
            const usage = rj?.['usage'] as Record<string, number> | undefined;
            const model = params['model'] as string | undefined;
            const stopReason = (rj?.['choices'] as Array<Record<string, unknown>> | undefined)?.[0]?.['finish_reason'];
            appendSpan({
              type: 'llm_call',
              provider: 'openai',
              ts: nowIso(),
              latency_ms: Date.now() - started,
              input_messages: toJsonable(params['messages'] ?? []),
              tools: toJsonable(params['tools'] ?? params['functions'] ?? []),
              model,
              response_content: rj,
              stop_reason: stopReason ?? null,
              usage: toJsonable(usage),
              cost_usd: computeCostUsd(model, usage),
            });
            return response;
          } catch (err) {
            appendSpan({
              type: 'error',
              ts: nowIso(),
              latency_ms: Date.now() - started,
              error: String(err),
              context: { provider: 'openai', model: params['model'] },
            });
            throw err;
          }
        };

        return instance;
      },
    });

    _cfg.patchedOpenAI = true;
  } catch {
    // openai not installed — skip silently
  }
}
