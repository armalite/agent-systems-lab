# Experiment Log

Chronological record of experiments and of the milestones that built the instrument. Each entry
records the commit, result paths, findings, limitations, and the next question.

---

## 2026-08-30 - Milestone 0: repository foundation

- **Type:** Instrument build (not an experiment).
- **Commit:** uncommitted working tree at time of writing (branch `main`, parent `7a7c4bb`).
- **Delivered:** Python 3.12 project via `uv`; `agent_lab` package with a `--version`-only CLI;
  ruff, pyright, and pytest configured; `paid` pytest marker deselected by default; `.env.example`;
  `results/` gitignored; README skeleton; research notebook files; `AGENTS.md` and `CLAUDE.md`.
- **Dependencies:** runtime `typer` only. `pydantic`, `rich`, `mcp`, `duckdb`, `pyarrow`,
  `pandas`, `matplotlib`, and provider SDKs are deliberately deferred to the milestone that
  first uses them.
- **Result paths:** none - no runs executed.
- **Findings:** none - no runs. Acceptance verified: `uv sync` and `uv run pytest` (6 passed,
  1 deselected) succeed on a scratch clean copy of the tracked tree with `ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, and `ANTHROPIC_BASE_URL` unset. `ruff check`, `ruff format --check`, and
  `pyright` (strict) are clean.
- **Pre-commit review:** the `paid`-marker gate is now verified in all three states - on by
  default, explicitly opted into, and removed (the tripwire fails). Packaging is checked against
  the installed distribution rather than the source tree. An empty `results/` directory was
  removed as premature scaffolding; its ignore rule remains.
- **Environment notes:** `uv` upgraded 0.4.16 -> 0.12.7 via its own install mechanism (`pip
  --user`) before the lockfile was generated. Pyright config had to move to `pyrightconfig.json`
  because a `pyrightconfig.json` in the parent directory captured pyright's root discovery. Ruff
  was restricted to Python files so that it cannot reformat code blocks inside `SPEC.md`.
- **Limitations:** no MCP environment, no harness, no adapter, no tasks, no evaluator, no
  tracing, no result schema. Nothing in the repository can call a model.
- **Next:** Milestone 1 (deterministic synthetic MCP environment), on researcher approval.

---

## 2026-08-30 - Milestone 1: deterministic synthetic MCP environment

- **Type:** Instrument build (not an experiment). No model was involved.
- **Commit:** uncommitted working tree at time of writing (branch `main`, parent `12f7fd9`).
- **Delivered:** `agent_lab.synthetic` (JSON fixtures, typed records, pure deterministic tool
  implementations, two declarative tool-spaces, thin stdio `MCPServer` adapter) and
  `agent_lab.mcp.client` (stdio client helper, canonical tool-surface projection). Overlap design
  and rationale recorded in `src/agent_lab/synthetic/README.md` **before** any model experiment.
- **Dependencies added:** `mcp>=2.1.1`, `pydantic>=2.13.5`.
- **Result paths:** none - no runs executed.
- **Verification:** all 10 tools invoked directly (no transport) and over a real MCP stdio
  subprocess; both `tools/list` surfaces confirmed independently (5 vs 10 tools, baseline a
  strict subset); three separate server subprocesses produced byte-identical results whose
  SHA-256 also equals the direct, non-MCP path. 79 tests pass; ruff and pyright (strict) clean.
- **Methodological notes:** two model-visible leakage paths were found and closed before any
  model experiment - pydantic docstrings serialized into the MCP output schema, and the server
  identity returned in the initialize result. Recorded in full as Observation O-001 (apparatus,
  not a research result). The model-visible surface is pinned by committed snapshots so an
  accidental edit to a control shows up as a reviewable diff, and tests assert that no
  research-design vocabulary or internal condition identifier reaches the model.
- **Limitations:** no harness, no tasks, no evaluator, no tracing, no persistence, no model
  adapter. `search_customers` uses substring matching with no relevance ranking, by design.
- **Next:** Milestone 2 (core experiment harness), on researcher approval.

---

## 2026-08-30 - Milestone 2: core experiment harness

- **Type:** Instrument build (not an experiment). No model was involved; no external API was
  contacted.
- **Commit:** uncommitted working tree at time of writing (branch `main`, parent `186f666`).
- **Delivered:** canonical `EnvironmentDescriptor` and `ModelSurface` with separate `fp1:sha256`
  fingerprints; task loading with declared answer strategies; experiment config with a config
  fingerprint covering referenced content; single-turn model adapter protocol; deterministic
  scripted fake adapter; runner owning the agent loop and emitting ordered JSONL traces;
  versioned metric definition sets; result derivation from traces alone; Parquet persistence
  with an explicit Arrow schema; `agent-lab validate` / `run`; the `experiments/harness_check/`
  self-check (8 tasks x 2 conditions x 2 repetitions = 32 runs).
- **Dependencies added:** `pyarrow`, `pyyaml` (runtime); `duckdb`, `types-PyYAML` (dev only).
- **Result paths:** `results/harness_check_001/<execution_id>/`. These are instrument self-checks
  and are **not** research evidence.
- **Verification:** 177 tests pass; ruff and pyright (strict) clean. Every normalized row was
  re-derived from its persisted trace and asserted equal to what was written. Two executions
  produced identical canonical traces and identical rows outside volatile fields. The
  model-surface fingerprint was shown not to move when `serverInfo` or server instructions
  change, while the environment fingerprint does.
- **Methodological findings:** Observation **O-002** - the scripted adapter initially embedded
  the tool-space id in tool-call ids, which are echoed back into the conversation, placing the
  condition label directly in model-visible context. Call ids are now opaque. This is the same
  failure mode as O-001 at a third boundary; the standing rule is now to audit the *recorded
  request*, not the code that builds it.
- **Limitations:** no provider adapter, no paid path, no Phase 0 dataset, no pre-registration
  record, no comparison or plotting, no analysis tooling. The scripted adapter is a calibration
  weight and says nothing about agent behaviour. Token usage is null rather than zero because the
  fake reports none.
- **Next:** Milestone 3 (first real provider adapter, with run-time paid opt-in), on researcher
  approval.

---

## 2026-08-30 - Milestone 3: first real provider (offline)

- **Type:** Instrument build (not an experiment). **No provider API call has been made.**
- **Commit:** uncommitted working tree at time of writing (branch `main`, parent `da30924`).
- **Delivered:** `agent_lab.models.anthropic` (one model turn, no loop); `agent_lab.models.provider`
  (paid gate, request budget, deterministic secret redaction); `provider` trace layer with
  `PROVIDER_SURFACE_PREPARED` and `PROVIDER_ERROR`; stable `provider_surface_fingerprint` plus the
  exact full provider request body persisted for every turn with its own hash; provider fields in
  the result schema; `--allow-paid`; `clean harness-check`; `experiments/smoke_anthropic/`
  (3 tasks, 1 condition, 1 repetition, classification `harness_check`).
- **Schema versions:** trace 1.0.0 -> 1.1.0, result 1.0.0 -> 1.1.0. M2 and M3 rows must not be
  compared as equivalent.
- **Dependencies added:** `anthropic>=1.2.0`.
- **Verification (all offline):** 237 tests pass; ruff and pyright (strict) clean. The full
  harness ran end to end against a fake Anthropic client through the real runner, real MCP
  environment, and real tracing - results re-derived from persisted traces and matched. Six
  persisted provider requests were audited for leakage: zero hits across design vocabulary,
  condition identifiers, run/execution ids, filesystem paths, server identity, and credential
  shapes. Environment, model-surface, and provider-surface fingerprints are all distinct.
- **Methodological finding:** Observation **O-003** - the Anthropic tool schema has no
  output-schema field, so a model reached through the Messages API sees a materially narrower
  capability surface than the same environment presents over MCP. Recorded explicitly in the
  trace rather than left implicit.
- **Controls:** `claude-opus-5`, `thinking: {type: adaptive}`, `effort: high`, `max_tokens: 4096`,
  SDK retries 0. `temperature` is deliberately absent - unsupported on current Claude models and
  rejected by the API. Variance is controlled by repetitions, not sampling parameters.
- **Limitations:** model identity is a mutable alias, not an immutable snapshot; recorded as
  `model_snapshot_available: false` alongside the served model the provider reports. No live
  evidence exists yet.
- **Next:** Milestone 4 planning, on researcher approval. Phase 0 still requires a
  pre-registration record before execution.

---

## 2026-08-30 - Milestone 3: live provider smoke validation

- **Type:** Harness check against a real provider. **Not calibration and not Phase 0.**
- **Experiment:** `smoke_anthropic_001`, unmodified - config fingerprint
  `fp1:sha256:a7e06081...`, identical to the approved offline definition.
- **Attempt 1** (`20260830T060816Z`): all 3 runs rejected with HTTP 400
  `invalid_request_error` - insufficient account credit. No inference, **$0.00 billed**. Every
  run recorded a distinct `PROVIDER_ERROR`, aborted with `stop_reason: provider_error`, did not
  retry, and still produced a complete trace and a re-derivable result row. First real test of
  the zero-retry provider-error path; it held. Evidence retained.
- **Attempt 2** (`20260830T061819Z`), after credits were added: **3/3 first-call routing correct,
  3/3 task success.** 6 provider requests (budget 10), 5,607 input and 347 output tokens, 0 cache
  tokens. **Actual cost ~$0.037.**
- **Model:** requested `claude-opus-5`; `response.model` returned `claude-opus-5`. An alias, not
  an immutable snapshot - recorded as `model_snapshot_available: false`.
- **Controls:** `thinking: {type: adaptive}`, `effort: high`, `max_tokens: 4096`, SDK retries 0,
  no `temperature`.
- **Verification:** 6 live provider requests audited for leakage - zero hits across design
  vocabulary, condition identifiers, run/execution ids, paths, server identity, and credential
  shapes. The live OAuth access token was byte-searched across every artifact and is absent. All
  3 result rows re-derived from the raw traces match the persisted Parquet exactly. Environment,
  model-surface, and provider-surface fingerprints all distinct and identical to their offline
  values.
- **Findings:** Observation **O-004** - a text preamble accompanies the tool call in most turns
  (handled correctly; regression test added), and adaptive thinking produced zero thinking tokens
  on these trivial lookups, so the verbatim thinking-replay path remains exercised only offline.
- **Limitations:** three tasks, one condition, one repetition, one model. Says nothing about
  agent behaviour and is not evidence for any research claim.

---

## 2026-09-01 - Milestone 4: Phase 0 calibration (COMPLETE)

- **Type:** Calibration / positive control. **Not a novel research contribution** and not the
  intended frontier question (`SPEC.md` s16).
- **Bound by:** [`research/preregistration/PHASE0.md`](preregistration/PHASE0.md), committed
  before any Phase 0 provider call.
- **Source commit:** `55030e4b6a3d06d093c17bcaa16bb32f5efb6e04`, `source_tree_dirty: false`.

### Physical executions

Two physical executions exist and must remain clearly distinct. They are never combined.

**`20260901T103826Z` - OPERATIONALLY INVALID.** Three Anthropic HTTP 529 `overloaded_error`
responses and one request timeout produced four provider-invalid runs of 280 (schedule positions
53, 54, 64, 69; both conditions; four distinct tasks). Under the pre-registered whole-execution
rule this invalidated the entire execution. **No headline analysis was produced from it** - the
analysis gate refused, and no `phase0_analysis.json` or chart exists in that directory. The
execution and all 280 traces are retained as apparatus evidence. ~$4.21 spent. See O-006.

**`20260901T113003Z` - OPERATIONALLY COMPLETE.** Zero provider failures.

- 280/280 valid runs (28 tasks x 2 conditions x 5 repetitions)
- 560 provider requests (ceiling 1120)
- 674,987 input + 36,340 output tokens, 0 cache
- **~$4.28 estimated API cost**
- All frozen fingerprints (config, task set, metric set, and all six environment / model-surface /
  provider-surface values), the realized counterbalanced schedule, and clean-tree provenance
  matched the pre-registration exactly.

### Pre-registered headline result - direct-exposure stratum (n=20)

| | |
|---|---|
| Baseline mean routing rate | **1.0000** |
| Overlap mean routing rate | **0.8000** |
| **Mean paired difference** | **-0.2000** |
| 95% task-cluster bootstrap interval | **[-0.4000, -0.0500]** |
| Pre-registered practical-effect threshold | 0.10 |
| Tasks regressed / unchanged / improved | **4 / 16 / 0** |

Final task success remained **100% in both direct conditions**: routing degraded while answer
correctness did not.

### Non-target / spillover stratum (n=8) - reported separately

Baseline **1.0000**, overlap **1.0000**, mean paired difference **+0.0000**, 0 regressed. This
stratum is **never pooled** into the direct-exposure headline, and at n=8 it is a coarse
spillover indicator only, not a true negative control.

### Descriptive patterns observed after results (NOT pre-registered claims)

Exploratory and descriptive only. No additional hypothesis test, sweep, or metric was run on
these, and none carries a claim.

- All four regressed tasks queried the customer `status` field.
- Four of the five frozen `status` tasks regressed.
- All 20 regressed runs selected `get_customer_details` as the first tool.
- All 20 retained the correct `customer_id`; argument correctness was 100/100 in both conditions.
- No `email`, `city`, or `name` task regressed.
- Every task-condition cell was either 0/5 or 5/5, so **no within-task variation was observed in
  this calibration**. This is a Phase 0 empirical characteristic, not an apparatus observation.
- The one non-regressing `status` task used the imperative prompt register. **n=1 provides no
  basis for inference** and no conclusion is drawn from it.

### Calibration outcome

**`SPEC.md` s16 criteria satisfied.** The experiment was valid and controlled; model/tool
interactions were fully inspectable; the evaluator correctly distinguished routing failure from
answer correctness; the comparison was reproducible; and the outcome is explicable from preserved
evidence as a single named tool substitution on a single field.

**Phase 0 and Milestone 4 completed successfully.**

- **Findings:** Observations **O-005** and **O-006**, both apparatus findings from the invalid
  first execution. Neither is a research result.
- **Limitations:** one routing archetype, one model, one environment version, one system prompt,
  synthetic fixtures; `claude-opus-5` is a mutable alias, not an immutable snapshot; the
  non-target stratum at n=8 cannot resolve small spillover.
- **Next:** **MANDATORY STOP** (`SPEC.md` s16). Do not sweep tool count, naming, descriptions,
  schemas, ordering, or models. The novelty gate (`SPEC.md` s3) must be invoked before selecting
  the first frontier research question. Phase 0 is not the contribution.

---

## Phase 0 pre-registration

**Written and frozen: [`research/preregistration/PHASE0.md`](preregistration/PHASE0.md).**

That document is the binding design record - strata, task set, fingerprints, metrics, unit of
generalization, aggregation, execution schedule, practical-effect threshold, uncertainty method,
operational-validity rule, model controls, and budget. It is committed **before** any Phase 0
provider call, and every trace and result row records `source_commit_sha` / `source_tree_dirty`,
so precedence is verifiable rather than asserted.

**Phase 0 has not been executed.** No Phase 0 model result has been observed. Results will be
recorded here and in `research/observations.md` after execution, never in the pre-registration.
