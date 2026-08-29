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

- persistent memory subsystems, memory provenance, revalidation or invalidation machinery;
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

**Hard stops** written into the spec: after Phase 0 calibration (§16), and at Research Gate 1
after Milestone 5 (§23). At a hard stop, report and wait.

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

**Current milestone:** Milestone 0 - repository foundation. **Complete.**

**Implemented:** `uv`-managed Python 3.12 project (`pyproject.toml`, `uv.lock`); `agent_lab`
package exposing `__version__` and a `--version`-only Typer CLI; ruff, pyright (strict, via
`pyrightconfig.json`), and pytest configured; `paid` pytest marker deselected by default with
tests guarding that gate; `.env.example`; `results/` gitignored; README; research notebook files;
`AGENTS.md`; `CLAUDE.md`. Runtime dependency: `typer` only.

**Not yet implemented:** synthetic MCP environment and fixtures (M1); experiment harness, task and
tool-space loaders, model adapter interface, fake deterministic adapter, trace recorder,
deterministic evaluator, normalized result schema, Parquet persistence (M2); real provider adapter
(M3); Phase 0 calibration dataset and experiment (M4); DuckDB analysis ergonomics (M5).
**Nothing in this repository can call a model.**

**Active research question:** none. Phase 0 is calibration only, and no novelty gate has been run.

**Observations recorded:** none - no agent runs have been executed.

**Standing decisions carried forward** (agreed with the researcher, not yet implemented):

- Dependencies are added by the milestone that first uses them, never because they appear in the
  preferred stack in `SPEC.md` s7.
- The trace and result design must preserve the **full ordered tool-call sequence**; summary
  fields such as a single selected tool are derived from it, never substituted for it.
- `tool_selection_correct` and the primary/secondary routing and recovery metrics must be
  **pre-registered in `research/experiment-log.md` before any Phase 0 result is observed.**
- Real MCP stays in the execution path for actual experiments; unit tests may exercise the
  underlying deterministic behaviour directly. Tracing must distinguish MCP/transport failures
  from model tool-selection behaviour.
- Paid provider execution requires an explicit per-run opt-in. Configured credentials must never
  be sufficient to start a billable run.
