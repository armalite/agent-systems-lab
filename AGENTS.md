# AGENTS.md - Operating Rules for Coding & Research Agents

Agent-neutral rules for any agent (Claude, Codex, Copilot, Cursor, other) working in this
repository. Read this file first, then `SPEC.md`, which is authoritative and must not be
edited without the researcher's explicit request.

---

## 1. What this repository is

**Agent Systems Lab is an experimental instrument, not a product and not an agent framework.**

It exists so its owner - an experienced staff-level data/platform engineer moving into AI
systems work - can find poorly understood behaviour in LLM agent systems, turn it into
controlled reproducible experiments, and publish findings that are genuinely useful to the
wider AI community.

Everything built here is subordinate to that. Platform work is justified only when it makes a
current research question cheaper to answer, inspect, or reproduce.

The current frontier direction (a direction, not a decided conclusion) is **evolving agent
systems**: how persistent agents behave when their capabilities, environment, and learned
experience all change over time.

Success is *not* "the repository has lots of features". Success is a trustworthy, reproducible
observation that is non-obvious, survives controls, is distinct from existing work, and creates
a good next question.

---

## 2. Calibration vs. characterisation vs. frontier research

Every experiment must be explicitly classified. Never let one silently become another.

| Class | Purpose | Rule |
|---|---|---|
| **Calibration** | Reproduce a *known* effect to prove the instrument can measure it | Keep deliberately small |
| **Characterisation** | Isolate the mechanism behind an observation | Only when it serves a gated question; never auto-expand into a benchmark grid |
| **Frontier** | Answer a question the literature/practice leaves open | The actual point of this repo; requires a passed novelty gate |

**Tool-space interference is calibration, not the contribution.** Phase 0 exists to validate the
harness against a known effect. That degradation happens when overlapping tools are added is
already established; re-establishing it at scale has no research value here.

**Anti-goal:** do not exhaustively re-test established results just because the harness makes it
easy. Known-already includes: large/confusing tool-spaces degrade performance; semantic overlap
interferes with selection; descriptions and schemas materially affect tool use; stale memory
harms agents; dynamic environments are hard.

---

## 3. The novelty gate (mandatory)

Before implementing **any** research programme beyond calibration, stop and run the gate in
`SPEC.md` §3. It is a research gate, not paperwork.

Record in `research/novelty/RQ-XXX.md`: the exact question; hypothesis if any; why the answer
matters; closest existing work; what this adds; what result is interesting even if the
hypothesis is false. Then a decision: **Proceed / Narrow / Reframe / Stop**.

Rules:

- Search **current** sources at proposal time (arXiv, ACL/EMNLP/NAACL/NeurIPS/ICML/ICLR, lab
  research blogs, benchmark repos, credible systems work). Novelty is time-sensitive.
- **Never** rely solely on model-internal knowledge for a novelty claim.
- The specification appearing to describe a direction is **not** evidence it is novel.
- Do not implement the next phase in `SPEC.md` merely because it is written there. Future phases
  require an explicitly selected, gated question.
- If current published work makes a planned direction redundant, say so plainly.

---

## 4. What must not be implemented prematurely

Do not build until a selected, gated experiment requires it:

- persistent memory **subsystems**, revalidation or invalidation machinery. Milestone 5 built a
  controlled memory *surface* (`agent_lab.memory`) and nothing more: declared material, one
  versioned deterministic selection policy, one versioned model-visible presentation, resolved
  once per run by the runner. Memory content, its selection/presentation policy, and its
  provenance are **model-visible experimental material** under the same evidence, fingerprinting
  and leakage discipline as any other model-visible surface (`SPEC.md` s4.3.1, s4.3.2, s6.14,
  s12). Nothing beyond that surface is authorized: no store, no index, no embeddings, no ranked
  or semantic retrieval, no turn-varying selection, no writing or rewriting during a run;
- self-healing / autonomous repair of capability surfaces;
- adaptive or learned capability-selection layers;
- large benchmark matrices or multi-model sweeps;
- automatic experiment generation;
- multi-agent architecture.

Never introduce (without explicit approval): LangChain, LlamaIndex, CrewAI, AutoGen, or any
general agent-abstraction framework; web apps or dashboards; Kubernetes, cloud infra, containers
as a runtime requirement; Kafka or distributed eventing; Postgres or hosted vector databases;
production auth or tenancy.

Avoid abstractions that obscure exactly what context, tools, messages, and observations were
presented to a model. If a layer makes the agent loop harder to read, it is wrong for this repo.

Empty modules created only to match the target tree in `SPEC.md` §8 are also premature. Create a
module when it has real content.

---

## 5. Research integrity

- **Do not optimize experiments, prompts, evaluators, or architecture toward an expected or
  hoped-for result.** This is the single most important rule in the repository.
- Negative results are results. A falsified hypothesis from a valid experiment is a success.
- **Unexpected behaviour is data.** Record it in `research/observations.md` *before* attempting to
  fix, explain away, or tune it out.
- Never silently change an experimental control (model, parameters, system instructions, tasks,
  fixtures, evaluator, transport, retry policy). A declared variable change must not alter
  another variable. Changing a control invalidates comparison with prior results - say so.
- Document every methodological compromise where it occurred, and in the experiment log.
- Do not claim stronger reproducibility than the provider actually permits; document
  non-determinism and the absence of immutable model snapshots when relevant.
- Prefer deterministic evaluation. LLM-as-judge is only ever an explicit, named evaluator type -
  never an invisible default - and never when a deterministic answer exists.
- **Never extend task count, repetitions, or provider budget after looking at results** because
  the result is weak, surprising, nearly significant, or otherwise tempting. A post-observation
  extension is a deviation and a new analysis, and must be recorded as one (`SPEC.md` s14.1).
- An underpowered, noisy, or unresolved comparison is not "no effect" - report the achieved
  uncertainty instead. Never compute post-hoc/observed power from the observed effect and present
  it as evidence of sensitivity (`SPEC.md` s14.1).

---

## 6. Engineering rules

- Python 3.12+, `uv` for env and locking, `pytest`, Ruff for lint/format, and static type
  checking. Strongly typed public interfaces where practical.
- **Dependencies are added by the milestone that first uses them, not up front.** `SPEC.md` s7
  names the *preferred* choice for each job when a milestone needs it - `pydantic`, `typer`,
  `rich`, the official MCP Python SDK, provider SDKs used **directly**, `duckdb` + `pyarrow`
  (+ `pandas` where useful), `matplotlib` for simple plots. It is not a list to install now, and
  a package appearing there is not a reason to declare it.
- JSONL for raw traces, Parquet for normalized results. DuckDB must be able to query results
  directly, without application code.
- Preserve separation between: model-provider behaviour, agent/environment behaviour, experiment
  definition, evaluation, tracing, persistence, analysis.
- Do not normalize away provider information that may later prove experimentally relevant.
- Add or update tests for every harness change. Cover config validation, task and tool-space
  loading, environment identity, the evaluator, trace and result serialization, synthetic tool
  behaviour, comparison logic.
- **Default `pytest` must never make a paid model API call.** Provider-hitting tests are opt-in
  and excluded by default. Use a deterministic fake model adapter for integration tests.
- Credentials come from environment variables only. Never write credentials into traces, results,
  logs, or raw provider payloads. `.env` stays gitignored.
- Cost control is a hard requirement: max-tasks caps, configurable repetitions, dry-run/validate,
  run-size preview, explicit model selection, no accidental grids. Smoke-test on 1-3 tasks and
  verify traces before scaling.
- Prefer the simplest transparent implementation that satisfies the current milestone.

---

## 7. Working process

For each milestone:

1. inspect repository state;
2. read the relevant research/spec context;
3. propose only the architecture decisions actually needed;
4. implement the smallest coherent slice;
5. add/update tests;
6. run tests, lint, and type checks;
7. update documentation wherever project state changed;
8. summarize exactly what changed and any deviation from `SPEC.md`;
9. **stop at the milestone boundary.**

Do not build a later milestone early because it looks easy.

**Surface, don't decide:** if a choice could materially affect experimental methodology -
evaluator semantics, what counts as success, controls, trace content, environment identity,
sampling, or model configuration - present it to the researcher instead of choosing silently.

If something in `SPEC.md` looks technically problematic, outdated, unnecessarily complex, or
inconsistent with the research goal, say so rather than implementing it blindly.

**Hard stops** written into the spec: after Phase 0 calibration (§16), which is immediately
followed by Research Gate 1 (§23). At a hard stop, report and wait.

---

## 8. Research notebook discipline

These files are first-class research artifacts, not documentation chores:

- `research/hypotheses.md` - ID, statement, rationale, prediction, falsification condition,
  related experiments.
- `research/observations.md` - surprising behaviour, recorded before it is explained away.
- `research/experiment-log.md` - experiment, commit SHA, result paths, findings, limitations,
  next questions.
- `research/research-backlog.md` - ideas, with no implication that they should be built.
- `research/novelty/` - the evidence and decision from each novelty gate.

Keep them current as part of the work, not afterwards.

---

## 9. Continuity contract

Any agent joining this project must be able to read `SPEC.md`, this file,
`research/experiment-log.md`, `research/observations.md`, and `research/novelty/`, and answer:

1. What is the researcher's long-term goal?
2. What has already been built?
3. What has actually been observed?
4. Which findings are calibration and which are potentially novel?
5. What research question is currently active?
6. What must not be implemented yet?
7. What is the next decision or experiment?

If those answers are not clear from the repository, fixing the documentation is part of the work.

---

## 10. Project state

*Keep this section accurate. It is the fastest answer to "what exists?" for a new agent.*

**Current milestone:** Milestone 5 - Controlled Procedural-Memory Surface. **Complete.** The
**mandatory stop** after M5 (`SPEC.md` s23) is now in force: the researcher must inspect the
apparatus for leakage/contamination, then design, pilot and pre-register a frontier experiment
before any claim-bearing run. No such experiment exists in this repository.

**Implemented:** M0-M3 as before (project and tooling; deterministic synthetic MCP environment;
the harness with runner-owned agent loop, tracing, deterministic derivation, versioned metrics and
Parquet; the Anthropic one-turn adapter with paid gate, request budget, exact per-turn provider
requests and three-way surface fingerprinting). *M4* adds the expanded customer fixtures (20), the
frozen 28-task Phase 0 set, the deterministic counterbalanced execution schedule, trace-derived
source provenance, `agent_lab.analysis.phase0`, and the committed
`research/preregistration/PHASE0.md`. *M5* adds `agent_lab.memory` - declared memory material,
one versioned deterministic selection policy, one versioned model-visible presentation, and their
three separate fingerprints - plus the `MEMORY_SURFACE_RESOLVED` trace event, four normalized
memory columns, and trace/result schema `1.4.0`.

**Phase 0 outcome:** executed at commit `55030e4b` from a clean tree. Physical execution
`20260901T113003Z` is the valid one (280/280 runs, 560 requests, ~$4.28); `20260901T103826Z` is
retained as an operationally invalid apparatus execution and is never combined with it. Headline
(direct-exposure stratum, n=20): baseline 1.0000, overlap 0.8000, mean paired difference -0.2000,
95% task-cluster bootstrap [-0.4000, -0.0500], 4 regressed / 16 unchanged / 0 improved, task
success 100% in both conditions. Non-target stratum (n=8): 1.0000 vs 1.0000, reported separately
and never pooled. `SPEC.md` s16 criteria satisfied.

**This is calibration, not a contribution.** It reproduces a known effect to validate the
instrument. Do not describe it as a research finding.

**Research Gate 1: complete.** Its outcome was `NARROW / PROCEED`. The novelty review, the
selected question, the hypothesis, the closest-work analysis, and the claim boundary are held
**outside this repository** until deliberate disclosure. Do not attempt to reconstruct,
reverse-engineer, infer, or restate them here, and do not encode them into apparatus code,
experiments, fixtures, tests, or documentation. What the gate authorized in public is M5 and
nothing else. Passing a gate never authorizes a claim-bearing experiment.

**Memory scope discipline.** `agent_lab.memory` is a controlled experimental *surface*, not a
memory subsystem. Still explicitly unauthorized (`SPEC.md` s4.3.2): vector storage, embeddings,
semantic or ranked retrieval, recency scoring, turn-varying retrieval, autonomous memory writing
or rewriting, self-healing, revalidation algorithms, compatibility probes, a memory service, and a
generic skill-management platform. Additional selection policies and presentation modes are
**future experimental variables**, not ergonomic gaps - add one only when a pre-registered
experiment requires it, and never by editing an existing versioned definition in place.

**Active research question:** none is defined in this repository, and M5 is apparatus, not a
finding. No experiment shipped here declares memory; `tests/test_memory_surface.py` enforces
that.

**Observations recorded:** O-001 to O-004 (model-visible leakage and real-provider behaviour) and
O-005, O-006 (CLI disclosure before validity was known; operational cost of whole-execution
invalidation). All are apparatus findings; none is a research result.

**Standing decisions carried forward.** `SPEC.md` v2.1 absorbed most of these; the spec is the
canonical statement and the section references below are the place to check the detail.

- Dependencies are added by the milestone that first uses them, never because they appear in the
  preferred stack in `SPEC.md` s7.
- The trace and result design must preserve the **complete ordered tool-call sequence**
  (`SPEC.md` s12, s13). Derived fields such as `first_tool_correct`, `expected_tool_used`, and
  `tool_recovery_success` come from that trace; a run is never collapsed to one selected tool.
- **Quantitative design must be pre-registered before the real comparison is observed**
  (`SPEC.md` s14.1, s16): analysis/generalization unit, treatment of repeated runs, aggregation
  rule, exact task/repetition/provider-request budget, stopping and invalid-execution rule,
  practical-effect threshold, and uncertainty approach - alongside the primary and secondary
  metrics themselves.
- When a claim generalizes across tasks, repetitions of one task are **within-task replicates**.
  Never count them as additional independent task observations (`SPEC.md` s14.1, s16).
- **Execution order is experimental design.** Where time, provider state, or a mutable model alias
  could drift, pre-register a deterministic or reproducibly seeded run order that interleaves the
  conditions, and persist the realized schedule as evidence. Never run one condition to completion
  and then the other, and never change the schedule after seeing results (`SPEC.md` s14.1, v2.5).
- **Never pool a directly manipulated stratum with a non-target/spillover stratum.** When a
  manipulation targets only part of a task set, declare both strata before results are observed
  and report the headline on the targeted stratum only (`SPEC.md` s14.1, s16, v2.5).
- Secondary metrics are diagnostic unless pre-registered as claim-bearing. Promoting one after
  results are observed requires a **new metric definition set/version** and must be labelled a
  new analysis, never presented as pre-registered (`SPEC.md` s14.1).
- Operationally invalid runs may be replaced or excluded **only** under the pre-registered rule,
  keeping distinct execution evidence. If retained repetitions end up unbalanced, the analysis
  must account for that rather than silently assuming an equal-weight balanced design
  (`SPEC.md` s14.1).
- Real MCP stays in the execution path for actual experiments; unit tests may exercise the
  underlying deterministic behaviour directly. Traces must distinguish model behaviour, MCP
  transport behaviour, deterministic tool execution, and evaluator decisions (`SPEC.md` s12).
- Paid provider execution requires an explicit **run-time** opt-in (`SPEC.md` s19, Milestone 3).
  Configured credentials must never by themselves authorize a billable run.
- Overlapping calibration tools are genuinely functional and internally consistent with the
  baseline tools. They must never be made to return wrong or partial data in order to
  manufacture task failure.
- **Model-visible surface discipline** (`SPEC.md` s6.13, s9.4): every string and schema field
  that reaches the model is experimental material - tool names, descriptions, input and output
  schemas, pydantic-generated schema titles, docstrings on result models, enum labels,
  annotations, server identity, server instructions, and **anything the harness synthesises
  that ends up in the message history** - including tool-call ids echoed back in the conversation
  (Observation O-002). Research-design vocabulary (`baseline`, `overlap`, `calibration`,
  `experiment`, condition identifiers, and the fact of being apparatus at all) must never appear
  there. Audit the **recorded request**, not the code that builds it - at the MCP boundary and
  again at the provider boundary, since an adapter re-serializes everything and may add material
  of its own. Guarded by `tests/test_mcp_server.py`, `tests/test_model_visible_audit.py`, and
  `tests/test_provider_execution_offline.py`.
- **Apparatus and workspace are separate provenance domains** (`SPEC.md` s12.1, s18.1).
  `source_*` describes the Agent Systems Lab tree that executed the study, resolved from the
  installed package; `workspace_*` describes the worktree holding the experiment definition, or is
  explicitly null. **Neither is ever inferred from the process working directory**, and apparatus
  code stays single-sourced here - an external workspace holds study material and results, never
  duplicated runtime.
- **SPEC-first evidence contracts** (`SPEC.md` principle 15). If a change would alter the semantic
  meaning of a persisted field, execution provenance, evidence authority, or the definition of an
  experimental/model-visible surface, update `SPEC.md` **before** implementing it. Pure refactoring
  that preserves those contracts does not need a spec revision.
- **Provider controls are experimental controls.** Declare thinking mode, effort, max tokens and
  model identity explicitly rather than inheriting provider defaults, and record them. Never send
  `temperature` to current Claude models - it is unsupported and rejected. Variance is controlled
  by repetitions (`SPEC.md` s18, v2.3).
- **Memory is declared input, resolved by the runner, never assembled in an adapter**
  (`SPEC.md` s4.3.2, s9.6). It enters as a separate leading user-role message and is never merged
  into `system_instructions`, so the capability `model_surface_fingerprint` stays independent of
  per-run memory. Selection is per run and invariant across turns. Hidden provenance - source
  traces, derivation identity, capability dependencies, learned-under fingerprints, lifecycle
  state - is harness evidence and must never reach a provider request. The descriptor fingerprint
  covers the whole declared corpus; the policy fingerprint covers the versioned definition plus
  its parameters, never the selection outcome; the surface fingerprint covers only what the model
  sees. **No memory configured** (null fields, no event) and **configured-but-empty** (real
  descriptor/policy fingerprints, canonical empty-surface fingerprint, count `0`, no model-visible
  message) are distinct recorded states and must not be collapsed.
- **The leading-user memory message has not yet been exercised against a real provider.** M5 is
  covered offline only. Two consecutive user-role messages are valid in the recorded request body
  but have not been sent to the Anthropic API from this apparatus. Smoke-test one memory-enabled
  task before any pre-registered memory run, and treat a provider-side rejection as an apparatus
  finding to record, not a reason to quietly change the placement contract.
- **Evidence authority is raw trace > normalized result row > aggregate summary** (`SPEC.md`
  s18). If a derived row disagrees with a valid trace, the trace wins and the derivation is the
  bug. Derived fields must be reproducible from the trace alone.
