# Agent Systems Lab - Research & Build Specification

**Status:** Active research specification  
**Version:** 2.8  
**Repository:** `agent-systems-lab`

### Version 2.8 roadmap clarification

Version 2.8 preserves the existing research direction, experimental contracts, novelty gate, Phase 0 result, and v2.7 provenance model. It corrects the post-calibration roadmap so the novelty gate follows completion of the calibrated initial instrument rather than being blocked by speculative analysis-ergonomics work.

Earlier versions established:

- every string or schema field that reaches a model is experimental material;
- the complete ordered tool-call sequence is primary evidence and must not be collapsed into a single selected-tool field;
- Phase 0 routing/recovery metrics must be pre-registered before real model results are observed;
- environment/tool-surface fingerprints should represent canonical model-relevant capability definitions rather than incidental wire serialization;
- provider execution that can incur cost requires explicit run-time opt-in even when credentials are configured.

Version 2.2 additionally clarified:

- distinguish the canonical MCP/environment descriptor from the exact surface actually presented to a model;
- preserve and fingerprint model-visible surface separately when it differs from the underlying environment;
- define a substantive tool call for Phase 0 metrics;
- exact argument matching treats unexpected arguments as incorrect for the Phase 0 primary metric;
- `tool_recovery_success` is nullable when no recovery was required;
- remove the redundant/ambiguous normalized `arguments_correct` field;
- deterministic answer evaluation must use a declared task-level matching rule rather than an ad hoc generic substring heuristic;
- distinguish stable logical `run_id` from physical `execution_id`;
- raw trace is authoritative over derived rows and summaries.

Version 2.3 additionally clarifies:

- distinguish a stable provider-facing capability/config surface fingerprint from the exact full provider request sent on each turn;
- preserve the exact full provider request body for every turn, with secrets excluded/redacted;
- preserve provider-native assistant continuation blocks when the provider requires exact round-tripping across tool-use turns;
- provider-specific model controls such as thinking/effort must be explicit experimental controls when available;
- do not use `temperature: 0` as a generic determinism control for models that do not support it;
- real-provider smoke validation is a harness check, not Phase 0 research.

Version 2.4 additionally clarifies:

- quantitative experiments must pre-register the unit of analysis/generalization, treatment of repeated runs, aggregation rule, fixed stopping/sample budget, and the smallest effect considered practically meaningful;
- repeated runs of the same task are within-task replicates, not additional independent task observations when the claim generalizes across tasks;
- A/A or equivalent repeatability checks may characterize apparatus/model stochasticity, but raw repeatability spread is not a universal threshold below which a real A/B effect cannot exist;
- formal power/minimum-detectable-effect calculations should be used when defensible variability information exists, but precision must not be invented when it does not;
- secondary metrics are descriptive/diagnostic unless independently pre-registered to carry a claim; post-observation promotion requires a new metric definition set/version and a clearly new analysis;
- if persistent memory later reaches the model, its content, retrieval/presentation policy, provenance, and exact retrieved material become model-visible experimental material and must be declared, fingerprinted, persisted, and auditable;
- naturally acquired/learned memory must be distinguished from synthetic, hand-authored, or transformed control material rather than treating one provenance type as universally required;
- memory retention/invalidation/revalidation policies are experimental conditions when compared, and their operational cost must be observable as an outcome;
- these memory constraints do not authorize a memory implementation or bypass the mandatory novelty gate.

Version 2.5 additionally clarifies:

- execution order is experimental design: when provider/model state or time drift could confound conditions, run ordering/counterbalancing must be pre-registered, deterministic or reproducibly seeded, and persisted as evidence;
- when a manipulation directly targets only part of a task set, the affected and non-target/spillover strata must be declared before results are observed and must not be silently pooled into one headline effect;
- fixture/task material may be expanded or corrected before the experiment is frozen, but once the pre-registration binds the task/fixture set, it becomes immutable for that execution except through a new explicitly versioned design;
- operational-failure handling may invalidate an entire execution rather than replacing individual cells; the chosen unit of invalidation/replacement must be pre-registered and incomplete and replacement executions must remain distinct;
- provider-request ceilings must not be lower than the maximum valid execution path allowed by the experiment's own run/step limits;
- request-count limits bound request count, not spend; expected/planning cost and theoretical token exposure must be described separately where paid execution is material.

Version 2.6 additionally clarifies:

- the reusable Agent Systems Lab apparatus and an external research workspace are distinct provenance domains and must never be conflated because of process working directory;
- `source_commit_sha` / `source_tree_dirty` refer specifically to the Agent Systems Lab apparatus source tree that executed the experiment;
- external experiment/workspace provenance is captured separately as `workspace_commit_sha` / `workspace_tree_dirty`, resolved from the Git worktree containing the experiment definition when one exists;
- apparatus Git/dependency provenance must be resolved from the actual apparatus/package source location, not from caller CWD;
- both apparatus and workspace provenance enter authoritative raw execution evidence before being derived into normalized results;
- external experiment/task content remains bound by the existing experiment/config/task fingerprinting discipline; additional experimental materials must be fingerprinted when a concrete study makes them model-visible or behaviourally relevant;
- apparatus code remains single-sourced in `agent-systems-lab`; external/private research workspaces contain study material and results, not duplicated runtime/harness code;
- any proposed implementation that changes the semantic meaning, provenance, or evidentiary authority of persisted experiment artifacts requires a SPEC contract update before implementation.

Version 2.7 additionally clarifies:

- persisted `trace_path` is an **execution-root-relative path** to the authoritative raw trace, not an absolute filesystem path;
- the physical execution/results root itself may live anywhere, including an external/private research workspace, but machine-specific absolute paths are not part of normalized experiment evidence;
- historical result rows keep the path semantics of the schema version under which they were originally produced and are not rewritten or migrated.

Version 2.8 additionally clarifies:

- Milestones 0-4 establish and calibrate the initial research instrument;
- **Research Gate 1 occurs immediately after Milestone 4 / successful Phase 0 calibration**;
- further analysis ergonomics are a deferred research-enablement backlog, not a prerequisite for novelty review or frontier-question selection;
- there is intentionally **no pre-written Milestone 5** after calibration;
- the novelty review, calibration evidence, and selected research question determine what Milestone 5 should be;
- a future Milestone 5 may be a small apparatus capability, a pilot, or a frontier experiment, depending on what the selected question actually requires;
- no memory capability, generic analysis layer, or other future platform feature is authorized merely because it appears useful in advance.


---

## 0. Researcher Intent and Continuation Brief

This section exists so that any AI coding/research agent can pick up this project without needing the original conversation that created it.

### What the researcher is actually trying to do

The goal is **not** to build another agent demo, MCP wrapper, generic agent framework, benchmark clone, or portfolio toy.

The researcher wants to become an active contributor to frontier AI systems work by:

- finding unexplained or poorly understood behaviour in modern LLM agent systems;
- turning those observations into controlled, reproducible experiments;
- identifying results that may be genuinely useful to the broader AI community;
- publishing useful findings, datasets, evals, tooling, or architectural ideas when warranted;
- building expertise at the intersection of AI behaviour and real software systems.

The researcher is an experienced staff-level data/platform engineer who increasingly works on AI systems, including MCP, agent/tool integration, evaluation, protocol behaviour, and client internals. The comparative advantage being pursued is **AI systems research**, especially questions involving tools, memory, evolving environments, evaluation, compatibility, feedback loops, and reliability - not competing with frontier labs on foundation-model pretraining.

Compute and budget are finite. Prefer research questions that can be investigated with controlled API experiments, open models where appropriate, local infrastructure, and strong experimental design rather than large-scale model training.

### What success looks like

Success is not:

> "The repository has lots of features."

Success is:

> "The lab produced a trustworthy, reproducible observation that tells us something non-obvious about agent systems, survives appropriate controls, appears meaningfully distinct from existing work, and creates a useful next research question."

The long-term aspiration is to reach research that is genuinely worth sharing with the AI community.

### Core working philosophy

**Build a microscope, not a product.**

The repository is an experimental instrument. Platform work exists only to make valid experiments easier to run, inspect, reproduce, and extend.

Known phenomena may be reproduced briefly to validate the instrument, but **reproduction is not the end goal**.

### Critical anti-goal

Do not spend significant time exhaustively re-testing already-established results merely because the harness makes those experiments easy.

For example, prior work already establishes that:

- large or confusing tool-spaces can degrade agent performance;
- semantically overlapping tools can interfere with selection;
- tool descriptions and schemas can materially affect tool use;
- stale or incorrect memory can harm agents;
- dynamic environments remain difficult for current agents.

A small reproduction of a known effect is useful as **calibration**. A large reproduction programme is not justified unless it supports a new unanswered question.

### Current frontier direction

The current strongest research direction is **evolving agent systems**:

> How do persistent agents behave when their capabilities, tools, environment, and learned experience all change over time?

Especially interesting is the interaction between:

1. **capability evolution** - tools are added, removed, renamed, versioned, or change semantics;
2. **persistent agent memory** - the agent stores procedural or experiential knowledge derived from earlier versions of that capability environment;
3. **feedback effects** - old experience may help adaptation, become stale, amplify errors, or reinforce new failures;
4. **compatibility mechanisms** - provenance, versioning, dependency tracking, selective revalidation, dynamic capability exposure, or other mechanisms may mitigate those failures.

A representative research question is:

> **Does persistent procedural memory amplify or mitigate capability regression when an LLM agent's tool environment evolves?**

A representative mitigation question is:

> **Can capability-aware memory provenance and selective revalidation reduce regressions after capability changes?**

These are candidate directions, not pre-decided conclusions. They must pass the novelty process in Section 3 before substantial implementation.

---

## 1. Purpose

Build a long-lived, reproducible laboratory for experimentally studying **evolving LLM agent systems**.

The system should make it cheap to:

1. define a hypothesis;
2. construct controlled agent environments;
3. vary one or more explicit experimental factors;
4. run the same tasks across conditions and models;
5. preserve the complete agent/tool interaction trace;
6. score outcomes deterministically where possible;
7. compare conditions;
8. inspect individual regressions and unexpected behaviours;
9. record observations;
10. decide the next experiment from evidence rather than from a feature roadmap.

The lab must support research programmes involving tools, MCP, memory, context, model behaviour, evaluation, evolving environments, and other agent-system components without requiring the core harness to be rewritten.

The guiding principle remains:

> **Build an experimental instrument, not an agent framework.**

---

## 2. Research Model

The project should distinguish three kinds of work.

### 2.1 Calibration work

Small experiments reproducing a known effect to establish that the harness is capable of measuring it.

Example:

> A baseline tool-space performs better than the same tool-space after strongly overlapping tools are introduced.

Calibration work should be deliberately small.

### 2.2 Characterisation work

Experiments that isolate mechanisms behind an observation.

Example:

> If a regression appears, is it caused primarily by naming similarity, description similarity, schema overlap, ordering, context length, model-specific routing behaviour, or something else?

Characterisation is useful when it supports a genuinely interesting unanswered question. It must not expand automatically into a large benchmark grid.

### 2.3 Frontier research work

The primary purpose of this repository.

A frontier experiment should attempt to answer a question that:

- appears incompletely answered by current literature or practice;
- has a clearly stated hypothesis or exploratory objective;
- can generate falsifiable or at least discriminating evidence;
- has plausible value beyond this repository;
- is controlled enough that a surprising result can be trusted;
- can be communicated to other researchers or practitioners.

---

## 3. Mandatory Novelty Gate

Before implementing any substantial research programme beyond calibration, stop and perform a novelty check.

This is a **research gate**, not an optional documentation task.

### 3.1 Required inputs

Document:

- the exact research question;
- the proposed hypothesis, if hypothesis-driven;
- why the answer would matter;
- what existing work appears closest;
- what the proposed experiment adds that existing work does not;
- what result would be interesting even if the original hypothesis is false.

### 3.2 Current-literature check

Because AI research moves quickly, the novelty check must use current sources at the time the experiment is proposed.

Search at minimum where appropriate:

- arXiv;
- ACL / EMNLP / NAACL / NeurIPS / ICML / ICLR proceedings;
- model-lab research/engineering publications;
- relevant benchmark repositories;
- recent systems or agent research;
- reputable implementation work if the question is primarily systems-oriented.

Do not rely solely on the knowledge encoded in an AI model.

### 3.3 Novelty decision

Record one of:

- **Proceed** - meaningful unanswered angle remains.
- **Narrow** - the broad question is known, but a specific interaction/mechanism remains interesting.
- **Reframe** - another formulation is more novel/useful.
- **Stop** - the planned experiment largely duplicates existing work without a compelling reason.

Store novelty reviews under:

```text
research/novelty/
```

Suggested file:

```text
research/novelty/RQ-001.md
```

### 3.4 Implementation rule

Coding agents must **not automatically implement the next research phase merely because it appears in this specification**.

After calibration, future experiment implementation requires an explicitly selected research question that has passed this gate.

---

## 4. Initial Research Programmes

These are research directions, not a backlog that must all be implemented.

### 4.1 Phase 0 - Tool-space interference calibration

Purpose:

> Verify that the lab can reproduce a known non-monotonic capability effect and correctly trace individual regressions.

This is calibration only.

Do not turn this phase into an exhaustive study of tool count, naming, descriptions, ordering, models, or schemas unless a later novelty-gated question requires those dimensions.

### 4.2 Capability evolution

Study what happens to established agent behaviour when the capability environment changes over time.

Example transitions:

```text
Environment V1
    |
    | add / remove / rename / modify tool
    v
Environment V2
    |
    | modify schema / response / semantics
    v
Environment V3
```

Questions may include:

- Which existing behaviours regress after capability changes?
- Can regressions be predicted before deployment?
- Are regressions localized or systemic?
- Do models differ in how they tolerate capability evolution?
- What information is needed to identify causal capability relationships?

### 4.3 Persistent memory in changing environments

Study the interaction between learned experience and environmental change.

Example:

1. an agent repeatedly uses a capability environment;
2. it stores procedural knowledge such as "for task pattern X, use Tool B";
3. that memory improves later performance;
4. the tool environment changes;
5. the previously useful memory becomes incomplete, misleading, or wrong;
6. measure whether memory helps adaptation or amplifies regression.

Key question:

> **When does remembered experience become technical debt for an agent?**

#### 4.3.1 Design constraints for any future memory experiment

This subsection is **not authorization to build a memory subsystem or to select memory as the next research question**. It records methodological constraints now so that implementation convenience cannot silently determine a later experiment. Any substantial memory work still requires an explicitly selected question that passes the novelty gate in Section 3.

If persistent memory later becomes experimental material:

**Memory is a model-visible surface.**

Retrieved memory that enters a model request can change behaviour just as tool names, descriptions, schemas, system instructions, or provider serialization can. Future memory-enabled experiments must therefore preserve enough evidence to distinguish:

- a canonical representation/descriptor of the memory material available to the experiment;
- a deterministic `fp1` fingerprint for the relevant canonical memory surface;
- the exact memory entries actually retrieved for each run/turn, in their presented order;
- the exact placement/presentation of those entries in the model/provider request;
- the provenance required to reproduce or explain how those entries were produced.

The exact persisted provider request remains the final model-visible evidence. Existing leakage rules continue to apply: audit the recorded request, not merely the code that constructed it. Old tool names, schemas, versions, environment identifiers, condition labels, or other capability-change information contained in memory are direct potential confounds and must be inspectable.

**Retrieval and presentation policy are experimental factors.**

What is retrieved, how many entries are retrieved, ranking/order, filtering, truncation, recency rules, and where/how memory is inserted into the request can independently create, amplify, suppress, or erase an observed effect. These choices must not remain invisible defaults inside harness code.

A memory-enabled experiment must declare the relevant retrieval/presentation policy in its experimental configuration and preserve a deterministic fingerprint of that policy or of the canonical memory configuration that contains it. The exact implementation shape should be chosen only when a novelty-gated experiment requires it.

**Memory provenance must be explicit.**

Do not impose a universal rule that all experimental memory must be trace-derived. Each memory set/entry must instead declare its origin, for example:

- trace-derived learned experience;
- synthetic controlled material;
- hand-authored controlled material;
- transformed/derived memory.

For an experiment intended to represent **naturally acquired agent experience**, the memory must be reproducibly derived from persisted traces of prior real runs, and the derivation itself must be reproducible from recorded evidence.

Synthetic or hand-authored memory is permitted when scientifically useful as controlled experimental material, but it must be labelled as such and must never be presented as naturally acquired experience.

**Provenance should make dependency/blast-radius questions answerable.**

When a future memory representation is designed, entries should retain the relevant provenance available at creation/derivation time, including where applicable:

- source run/trace identifiers;
- environment version;
- tool-space identifier;
- relevant environment, model-surface, and provider-surface fingerprints;
- relevant tool/schema/capability identity or version;
- derivation/transformation identity where memory was not copied directly from a trace.

Do not freeze a detailed memory schema now. The exact fields belong to the novelty-gated experiment that needs them.

**Memory policies are experimental conditions when compared.**

Policies such as retain-all, wipe-all, recency-based retention, provenance-scoped invalidation, and provenance-scoped revalidation can themselves change behaviour. If compared, they must be expressible as declarative experiment conditions with the rest of the harness held constant as far as the hypothesis permits.

Measure policy cost as well as behavioural outcome. Relevant cost may include additional provider requests, tool calls, input/output tokens, latency, or other reproducible resource usage.

### 4.4 Provenance-aware memory

Investigate whether memories should carry dependencies on the environment that produced them.

Conceptually:

```yaml
memory_id: M-104
type: procedural
content: "For customer-ID lookups, use get_customer."
confidence: 0.91

provenance:
  capability: get_customer
  capability_version: 1.4.0
  schema_hash: "..."
  toolspace_hash: "..."
  source_runs:
    - R-2201
    - R-2204
```

When capabilities change:

```text
capability changed
      |
      v
find dependent memories
      |
      v
mark suspect / reduce confidence / revalidate
      |
      v
retain, revise, or invalidate
```

This is analogous to lineage/dependency tracking in data and software systems, applied to machine experience.

Candidate questions:

- Does provenance reduce stale-memory failures?
- What level of dependency granularity is useful?
- Should memory confidence decay when its originating environment changes?
- Can only affected memories be revalidated rather than rebuilding all memory?
- What happens when a memory depends on interactions among multiple tools?

### 4.5 Agent capability compatibility testing

Explore whether capability changes can be treated as a compatibility problem analogous to software/API regression.

Long-term conceptual flow:

```text
proposed capability change
          |
          v
identify likely impacted behaviours
          |
          v
generate or select targeted regression evals
          |
          v
compare before / after environments
          |
          v
localize regressions
          |
          v
evaluate mitigation candidates
          |
          v
held-out validation
          |
          v
compatibility report
```

Potential mitigation classes include:

- description changes;
- naming changes;
- schema changes;
- capability grouping;
- selective visibility;
- routing policies;
- context changes;
- version-aware memory invalidation.

Do not implement a self-healing system until experiments justify it.

### 4.6 Adaptive capability surfaces

A later possible direction is to test whether the optimal capability surface depends on:

```text
model x task x current state x memory x environment
```

Instead of exposing the same complete tool-space to every model:

```text
full capability ecosystem
          |
          v
capability selection / compilation layer
          |
          v
temporary task/model-specific capability surface
          |
          v
model
```

Questions may include:

- Do different models need different tool representations?
- Is selecting a task-relevant subset better than exposing everything?
- Should persistent memory affect which tools are shown?
- Can a learned policy construct capability surfaces without hiding necessary tools?
- Does dynamic capability selection reduce interference while preserving discovery?

Again, novelty must be checked immediately before pursuing this work.

---

## 5. Scope of the Initial Build

### In scope

- Python research harness.
- Direct model-provider integrations.
- Real MCP client/server interactions.
- Synthetic deterministic MCP tools.
- Deterministic task datasets with known expected outcomes.
- Declarative experiment configuration.
- Detailed trace capture.
- Automated deterministic scoring where possible.
- Repeated runs and controlled comparisons.
- Parquet result storage and DuckDB analysis.
- CLI for running experiments.
- Small analysis outputs and plots.
- Provider/model abstraction sufficient to compare models later.
- Research notebook files.
- Phase 0 calibration experiment.
- Architecture that can later support multi-session/evolving-environment experiments.

### Explicitly out of scope initially

Do not build unless a selected experiment requires it:

- general-purpose production agent framework;
- web application or dashboard;
- Kubernetes deployment;
- cloud infrastructure;
- Kafka or distributed eventing;
- Postgres;
- hosted vector database;
- LangChain;
- LlamaIndex;
- CrewAI;
- AutoGen;
- large orchestration frameworks;
- multi-agent architecture;
- autonomous self-healing;
- production auth or tenancy;
- exhaustive benchmark grids;
- speculative memory architecture;
- automatic experiment generation before the core lab is trustworthy.

Avoid abstractions that make it difficult to determine exactly what context, tools, messages, memory, and observations were presented to a model.

---

## 6. Technical Principles

Prioritize:

1. **Reproducibility** - every result must be attributable to model, configuration, tasks, tool-space/environment, source version, and execution metadata.
2. **Observability** - preserve raw interactions, not only scores.
3. **Controlled experimentation** - a declared variable change must not silently alter another variable.
4. **Transparency** - direct provider SDK and MCP use is preferred over hidden framework behaviour.
5. **Provider neutrality** - provider-specific implementation must remain visible but isolated.
6. **Extensibility** - new experiments should primarily add datasets/configuration/environment variants rather than rewrite the harness.
7. **Cheap iteration** - debug locally and cheaply before expensive sweeps.
8. **Research integrity** - do not optimize implementations to produce the hoped-for result.
9. **Negative results matter** - a falsified hypothesis is still useful if the experiment is valid.
10. **Unexpected behaviour is data** - do not automatically "fix" unexplained model behaviour before recording it.
11. **Minimal platform bias** - build only infrastructure needed to answer current research questions.
12. **Novelty awareness** - continuously distinguish calibration, replication, engineering work, and genuinely new research.
13. **Model-visible surface discipline** - any content that reaches the model is part of the experiment. This includes tool names, descriptions, input/output schemas, generated schema titles, enum labels, server instructions, examples, annotations, and provider-specific tool serialization. Experimental intent or condition labels must never leak into that surface unless they are themselves the variable being tested.
14. **Memory-surface discipline** - if future work places persistent memory into a model request, memory content, selection/retrieval, ordering, truncation, provenance, and presentation are experimental material rather than hidden storage utilities. Preserve the exact retrieved material and provider-facing request evidence, and do not build a memory subsystem before a novelty-gated question requires it.
15. **SPEC-first evidence contracts** - if a proposed implementation changes the semantic meaning of a persisted field, execution provenance, evidence authority/derivation, or the definition of an experimental/model-visible surface, update this specification before implementing the change. Pure refactoring or ergonomics that preserve those contracts do not require a SPEC revision.

---

## 7. Preferred Technology Stack

Use unless a current experiment gives a strong reason otherwise:

- Python 3.12+
- `uv`
- `pytest`
- `pydantic`
- `typer`
- `rich`
- official MCP Python SDK
- provider SDKs directly
- `duckdb`
- `pyarrow`
- `pandas` where useful
- `matplotlib` for simple research plots
- JSON/JSONL for raw traces
- Parquet for normalized results
- Ruff
- Pyright or equivalent static type checking

Prefer strongly typed public interfaces where practical.

Do not introduce a heavy agent framework as the harness itself.

---

## 8. Target Repository Structure

```text
agent-systems-lab/
|
|-- SPEC.md
|-- AGENTS.md
|-- CLAUDE.md
|
|-- src/
|   `-- agent_lab/
|       |-- models/
|       |   |-- base.py
|       |   |-- anthropic.py
|       |   `-- openai.py
|       |
|       |-- mcp/
|       |   `-- client.py
|       |
|       |-- synthetic/
|       |   |-- fixtures/
|       |   |-- models.py
|       |   |-- data.py
|       |   |-- tools.py
|       |   |-- toolspaces.py
|       |   `-- server.py
|       |
|       |-- evals/
|       |   |-- base.py
|       |   |-- deterministic.py
|       |   `-- metrics.py
|       |
|       |-- experiments/
|       |   |-- config.py
|       |   |-- runner.py
|       |   `-- result.py
|       |
|       |-- environments/
|       |   |-- base.py
|       |   `-- versioning.py
|       |
|       |-- tracing/
|       |   |-- events.py
|       |   `-- recorder.py
|       |
|       |-- storage/
|       |   |-- parquet.py
|       |   `-- duckdb.py
|       |
|       |-- analysis/
|       |   `-- summaries.py
|       |
|       |-- memory/                 # create only after a novelty-gated memory question requires it
|       |
|       `-- cli.py
|
|-- experiments/
|   |-- calibration/
|   |   `-- tool_interference/
|   |
|   `-- research/
|       `-- <research-question-id>/
|
|-- results/                        # gitignored except fixtures/examples
|
|-- research/
|   |-- hypotheses.md
|   |-- observations.md
|   |-- experiment-log.md
|   |-- research-backlog.md
|   `-- novelty/
|
|-- tests/
|-- .env.example
|-- .gitignore
|-- pyproject.toml
`-- README.md
```

The exact module names may change for a strong technical reason. Preserve separation between:

- model-provider behaviour;
- agent/environment behaviour;
- experiment definition;
- evaluation;
- tracing;
- persistence;
- analysis.

Do not create empty abstractions merely to match this tree.

The synthetic environment intentionally lives inside the installed `agent_lab` package rather than a top-level `servers/` directory. This keeps deterministic fixture/data/tool logic directly importable and testable without MCP transport while allowing `synthetic/server.py` to remain a thin real-protocol adapter.

---

## 9. Core Domain Model

### 9.1 Model adapter

Define a provider-neutral interface conceptually similar to:

```python
class ModelAdapter(Protocol):
    async def run(self, request: AgentRequest) -> AgentResponse:
        ...
```

Request support should include:

- system instructions;
- task/user input;
- available tools;
- conversation state;
- optional memory/context;
- provider-supported generation controls;
- trace metadata.

Response support should include:

- final model output;
- tool calls;
- tool arguments;
- tool observations/results;
- usage information where available;
- latency;
- provider request identifiers;
- raw provider metadata or a serializable representation;
- opaque provider-native assistant content/continuation blocks when the provider requires them to be echoed back unchanged on later tool-use turns.

The runner must remain provider-neutral and must not interpret opaque provider-native continuation blocks. The owning adapter may preserve and replay them as required by the provider protocol.

Do not normalize away information that may later prove experimentally relevant.

### 9.2 Environment identity

Experiments involving evolving systems need an explicit environment identity.

Conceptually:

```yaml
environment:
  id: customer_env
  version: 1.0.0
  tool_space: customer_baseline_v1
  fingerprint: "..."
```

Persist a deterministic canonical **EnvironmentDescriptor** for the semantic MCP/environment state observed by the harness. It may include stable server identity/instructions, declared environment version, capability metadata, and the canonical tool surface. Exclude incidental wire details such as JSON-RPC request IDs, timing, cursor values, and raw envelope serialization.

Also persist a distinct deterministic **model-surface representation/fingerprint** for the content actually presented to the model adapter. This is the scientifically relevant object when asking whether a model-visible surface changed.

Do not assume that metadata visible to the MCP client is automatically visible to the model. For example, MCP `serverInfo` may be observed by the harness but must not be included in the model-surface fingerprint unless the harness/adapter actually presents it to the model.

At minimum, when exposed to the model, the model-surface representation should incorporate:

- tool names;
- model-visible descriptions;
- input schemas;
- output schemas;
- annotations/titles/enums or other generated schema metadata;
- server instructions/identity only if they are actually included in the model request;
- system instructions or other capability-related context supplied by the harness when relevant.

Canonicalization should use deterministic ordering and stable serialization. Do not hash raw MCP wire bytes merely because they are available.

The raw trace must preserve the actual adapter request.

In Milestone 3, when a real provider adapter may re-serialize or transform tools again, preserve two separate provider-boundary objects:

1. a deterministic **provider-surface representation/fingerprint** for the stable provider-facing capability/config material used for controlled comparison (for example model id, system instructions, rendered tools, tool choice, thinking/effort and other declared generation controls); and
2. the **exact full provider request body for every turn**, including the conversation/messages actually sent.

Do not call the stable surface fingerprint a fingerprint of the exact request if per-turn messages are excluded. If an exact-request hash is useful, compute it separately over the persisted full request after deterministic secret redaction.

The full provider request is evidence; the provider-surface fingerprint is a comparison aid.

Do not overdesign environment versioning before Milestone 2. Establish only enough structure that later experiments can distinguish V1 from V2 without ambiguity.

### 9.3 Task definition

Each deterministic task should include at minimum:

```yaml
id: customer_email_001
prompt: "What is the email address of customer C102?"

expected:
  tool: get_customer
  arguments:
    customer_id: C102
  answer:
    email: alice@example.test

metadata:
  domain: customer
  difficulty: baseline

answer_evaluation:
  strategy: contains_facts
```

Tool-selection correctness and final-answer correctness must be independently measurable.

Final-answer evaluation must be deterministic and declared with the task/task-set before results are observed. Do not use one permissive generic substring rule for every answer type. The initial harness may support a deliberately small set of deterministic strategies such as normalized exact match, required-fact containment, or typed scalar comparison. The chosen strategy and expected facts are part of the frozen task definition.

### 9.4 Tool-space definition

Tool sets must be declarative and versioned.

Example:

```yaml
id: customer_baseline_v1
tools:
  - get_customer
  - get_order
  - get_invoice
  - get_product
  - get_employee
```

Calibration overlap condition:

```yaml
id: customer_overlap_v1
extends: customer_baseline_v1

tools:
  - find_customer
  - search_customers
  - get_customer_details
  - lookup_customer
  - customer_information
```

The canonical tool-space definition must capture the model-relevant semantic surface, including tool names, descriptions, schemas, and any other fields actually exposed to the model. Generated schema metadata such as titles or docstring-derived descriptions is not "just implementation detail" if the model can see it.

Condition names, experiment labels, calibration terminology, overlap rationale, and other research-design language must remain internal unless explicitly being studied. Do not leak terms such as `baseline`, `overlap`, `calibration`, or `experiment` into model-visible tool metadata.

Snapshot tests may protect the canonical semantic surface, but should avoid coupling to irrelevant SDK serialization or protocol-envelope details.

### 9.5 Experiment definition

Experiments should be declarative.

Example:

```yaml
id: calibration_tool_interference_001

classification: calibration

research_question:
  "Can this harness reproduce degradation after semantically overlapping tools are introduced?"

model:
  provider: anthropic
  name: <configured-model>

task_set: customer_baseline_tasks_v1

conditions:
  - customer_baseline_v1
  - customer_overlap_v1

repetitions: 3

controls:
  randomize_tool_order: false
  # Provider-specific generation controls belong in the resolved model config.
  # Do not assume temperature is supported by every model.

metrics:
  - task_success
  - tool_selection_accuracy
  - argument_accuracy
  - tool_call_count
  - input_tokens
  - output_tokens
  - latency_ms
```

Saved results must include the complete resolved experiment configuration.

---

## 10. Synthetic MCP Environment

Build a deterministic MCP server specifically for controlled experimentation.

### Baseline tools

- `get_customer(customer_id)`
- `get_order(order_id)`
- `get_invoice(invoice_id)`
- `get_product(product_id)`
- `get_employee(employee_id)`

Use fixed fixture-backed data checked into the repository.

No external API/network dependency should be required for synthetic tools.

### Calibration overlap tools

Use controlled additional tools such as:

- `find_customer(name)`
- `search_customers(query)`
- `get_customer_details(customer_id)`
- `lookup_customer(email)`
- `customer_information(customer_id)`

Their intended semantic overlap must be documented.

The purpose is not to prove tool interference is novel. The purpose is to establish that the laboratory can detect a known effect and preserve enough evidence to inspect it.

---

## 11. Calibration Task Dataset

Create approximately 20-30 deterministic tasks spanning the baseline tools.

Requirements:

- approximately balanced across baseline tools;
- unambiguous expected tool;
- deterministic tool result;
- deterministic final answer;
- intentionally simple domain reasoning.

Examples:

- "What is the email address of customer C102?"
- "What is the status of order O204?"
- "What amount is due on invoice I301?"
- "What category is product P502?"
- "Which office is employee E104 assigned to?"

The task difficulty must not obscure the capability-selection behaviour being measured.

---

## 12. Trace Model

Raw trace preservation is mandatory.

Every run should preserve ordered events such as:

```text
RUN_STARTED
MODEL_REQUEST
MODEL_RESPONSE
TOOL_CALL_REQUESTED
TOOL_CALL_EXECUTED
TOOL_RESULT_RETURNED
MODEL_REQUEST
MODEL_RESPONSE
RUN_COMPLETED
EVALUATION_COMPLETED
```

Each event should include:

- timestamp;
- run ID;
- experiment ID;
- task ID;
- environment ID/version;
- model/provider;
- sequence number;
- event payload.

The trace is the source of truth for tool behaviour. Preserve the **complete ordered tool-call sequence**, including every call attempt, arguments, results, errors, retries, and subsequent recovery. Do not reduce a run to one singular `selected_tool` value at ingestion time.

Use a stable logical `run_id` to identify the experiment/condition/task/repetition combination, and a distinct `execution_id` to identify a physical invocation of the experiment so reruns do not overwrite evidence.

For Phase 0 single-tool metrics, a **substantive tool call** is any invocation emitted by the model, including an unknown/hallucinated tool name or a call with invalid arguments. Harness-initiated transport retries of an identical call are not additional substantive model calls. Calls that are impossible to attribute to model output must be represented separately rather than silently counted or discarded.

Where possible, traces should distinguish:

- model request/response behaviour;
- MCP transport/protocol behaviour;
- deterministic underlying tool execution;
- evaluator decisions.

The raw provider-facing request should preserve the exact tool representation, system content, messages/conversation, model controls, and other model-visible context actually sent to the provider, subject to credential/sensitive-data redaction.

Provider-native continuation content that must be replayed verbatim (for example thinking/redacted-thinking blocks on providers that require this) should be preserved losslessly in the trace and round-tripped by the provider adapter without interpretation by the runner.

For future memory research, the trace design should also be capable of recording:

- memory candidates;
- memory writes;
- retrieval queries;
- exact retrieved memories in presented order;
- retrieval/presentation policy identity or fingerprint;
- memory provenance and derivation identity;
- model-visible memory placement/presentation where not already reconstructible from the exact provider request;
- memory invalidation/revalidation events;
- incremental provider/tool/token/latency cost attributable to a memory policy where relevant.

The exact persisted provider request remains authoritative for what memory the model actually saw.

Do not implement the full memory subsystem initially.

### 12.1 Apparatus and external-workspace provenance

A physical execution may be defined by study material outside the Agent Systems Lab repository. In that case, preserve two independent provenance domains:

- **apparatus provenance** - the exact Agent Systems Lab source tree/runtime that executed the study;
- **workspace provenance** - the Git worktree containing the experiment definition and unreleased/public study material, when such a worktree exists.

The existing fields:

```text
source_commit_sha
source_tree_dirty
```

refer **only** to apparatus provenance. Their meaning must not depend on process working directory.

When an experiment definition is contained in an external Git worktree, also record:

```text
workspace_commit_sha
workspace_tree_dirty
```

If the experiment definition is not contained in a Git worktree, workspace provenance must be explicitly unavailable/null rather than inferred from the caller's current directory or confused with apparatus provenance.

Apparatus Git state and dependency-lock provenance must be resolved relative to the actual Agent Systems Lab source/package repository. Workspace Git state must be resolved relative to the repository containing the experiment definition.

Both provenance layers must first be written into authoritative raw execution evidence (for example `RUN_STARTED`) and execution-level manifest metadata. Normalized result fields must be derived from the raw trace rather than injected independently downstream.

Do not persist absolute developer-machine paths unless they are required to explain or reproduce the experiment and cannot be represented by stable repository-relative identity.

For raw-trace references specifically, persist `trace_path` **relative to the physical execution/results root**. The execution root may itself be selected externally (for example inside a private research workspace), but normalized result evidence must not encode the researcher's absolute home-directory path merely because the output root is external.

External workspaces do not authorize duplication of apparatus code. Generic runner, MCP, provider, tracing, evaluation, storage, fingerprinting, and synthetic-environment implementation remains single-sourced in `agent-systems-lab`.

Credentials must never appear in traces.

---

## 13. Normalized Result Schema

At minimum:

```text
run_id
execution_id
experiment_id
experiment_classification
timestamp
source_commit_sha
source_tree_dirty
workspace_commit_sha
workspace_tree_dirty

provider
model
model_parameters

environment_id
environment_version
environment_fingerprint
model_surface_fingerprint

task_id
task_set

tool_space_id
tool_count
tool_names

expected_tool

tool_call_sequence
first_tool
first_tool_arguments
first_tool_correct
first_tool_arguments_correct

expected_tool_used
expected_tool_used_correctly
incorrect_tool_call_count
unnecessary_tool_call_count
tool_recovery_success

expected_arguments

expected_answer
actual_answer
task_success

tool_call_count
input_tokens
output_tokens
latency_ms

repetition
random_seed_if_applicable
trace_path
```

The normalized schema may contain derived convenience fields, but the ordered raw trace remains authoritative. Fields such as `first_tool_correct`, `expected_tool_used`, and `tool_recovery_success` must be derived from pre-registered metric definitions rather than ad hoc interpretation after results are observed.

`source_*` and `workspace_*` provenance fields are also derived evidence. They must be reconstructible from raw execution events. Adding the workspace provenance fields changes the trace/result evidence schemas and therefore requires an explicit schema-version bump rather than silently extending historical schema versions. For the implementation current at v2.7, the intended transition remains trace schema `1.2.0 -> 1.3.0` and result schema `1.2.0 -> 1.3.0`.

`trace_path` identifies the authoritative raw trace **relative to the physical execution/results root**. It must not become an absolute developer-machine path when `--results-root` points outside the apparatus repository. Consumers resolve it against the execution root recorded/known by the execution context rather than treating it as a globally absolute location.

Store normalized batch results in Parquet.

DuckDB must be usable directly against results without requiring application code.

---

## 14. Evaluation

### 14.1 Quantitative design and interpretation

Keep statistical design proportionate to the size and purpose of the lab. The objective is not to impose one universal frequentist framework; it is to prevent stochastic model behaviour, repeated measures, flexible stopping, or weak power from being mistaken for a scientific conclusion.

Before observing the real experimental comparison, pre-register:

- the **unit of analysis/generalization** appropriate to the claim;
- how repeated runs of the same task are treated;
- the aggregation rule used to produce task-level and condition-level metrics;
- any pre-declared strata/subgroups required because the manipulation targets only part of the task set;
- the execution-order/counterbalancing rule when time/provider drift could confound conditions;
- the planned task count, repetition count, and provider/request budget;
- the stopping/replacement rule for invalid executions, including whether invalidity applies to individual runs/cells or to the entire execution;
- the smallest effect on the primary metric considered **practically meaningful**;
- the intended uncertainty/reporting method.

**Repeated runs are not automatically independent task observations.**

Repetitions of the same task within a condition may be useful within-task replicates for estimating model stochasticity. When a claim is intended to generalize across tasks, those repetitions must remain nested within task rather than being silently counted as additional independent task samples.

Do not impose a universal analysis unit on every future experiment. Run-level, task-level, paired-task, condition-level, or other analysis may be appropriate depending on the hypothesis; the choice and aggregation rule must be declared before results are observed and must not drift during analysis.

**Execution order can be a confound.**

When condition is correlated with execution time, provider state, mutable model aliases, transient infrastructure state, cache state, or other plausible drift, the order of runs becomes part of the experiment.

Use a pre-registered ordering strategy that reduces avoidable confounding, such as deterministic counterbalancing/interleaving for paired conditions. Persist enough schedule information to reconstruct the exact order actually executed. If randomization is used, persist the seed and realized schedule. Do not silently change the schedule after observing results.

**Practical importance and statistical detectability are distinct.**

Declare the smallest effect that would be meaningful for the research question before examining the experimental comparison.

Where prior or pilot variability permits a defensible power or minimum-detectable-effect calculation, record the estimate and its assumptions before the confirmatory comparison. Where it does not, do not invent statistical precision. Use the fixed design, report uncertainty appropriate to the analysis unit, and distinguish among:

- an observed effect below the pre-registered practical threshold;
- evidence precise enough to be consistent with little/no practically meaningful effect;
- an experiment whose uncertainty is too large to resolve meaningful from negligible effects.

An underpowered or noisy result must not automatically be described as "no effect."

Do not compute or report post-hoc/"observed power" from the same observed effect as if it were new evidence about sensitivity. If a defensible prospective power or minimum-detectable-effect estimate was not available before the comparison, report the achieved uncertainty/resolution directly instead.

**A/A or equivalent repeatability checks are apparatus measurements.**

An A/A control or equivalent repeatability analysis may be pre-registered when useful for characterising model stochasticity, validating that nominally identical conditions remain identical at the model-visible boundary, or estimating instrument repeatability.

If used:

- the nominal arms must have identical model-visible/provider-visible experimental surfaces unless the label itself is the variable under test;
- their canonical surface fingerprints should therefore match;
- logical condition labels must not leak into model-visible content;
- the observed A/A variability is apparatus/repeatability evidence, not a research result;
- raw A/A spread must **not** be treated as a universal hard threshold below which a real A/B effect cannot exist;
- any use of the repeatability estimate in later inference must be declared rather than hidden in analysis code.

**Secondary metrics are diagnostic unless pre-registered otherwise.**

The primary metric carries the headline claim for an experiment unless another claim-bearing metric was independently pre-registered.

Secondary metrics may explain mechanisms, recoveries, failure modes, or unexpected behaviour. After results are observed, a secondary metric must not be silently promoted into the primary story. If a later analysis promotes one to claim-bearing status, create a new metric definition set/version and label the analysis as new rather than retroactively pre-registered.

**Stopping rules must be fixed before the experimental comparison.**

Do not extend task count, repetitions, or provider-request budget merely because a result is weak, surprising, nearly significant, or otherwise tempting.

Operationally invalid executions (for example authentication/billing failures or provider outages that produce no model observation) may be replaced or excluded only according to a declared failure/replacement rule, must retain distinct execution evidence, and must not be confused with inconvenient but valid model outcomes.

The rule may operate at the individual-run/cell level **or invalidate the entire physical execution**. A whole-execution strategy is acceptable when it better preserves a balanced frozen design. In that case, incomplete and replacement executions must remain separate, must never be silently combined for the headline analysis, and any paid rerun requires fresh authorization.

If invalid runs are instead retained/excluded at finer granularity, the declared rule must state how unequal valid repetition counts are handled. Dropping runs can produce unequal precision across tasks/conditions and therefore changes the appropriate aggregation or uncertainty treatment. Do not silently apply an analysis that assumes a balanced design when the retained evidence is unbalanced.

A provider/request ceiling must be large enough to permit every valid trajectory allowed by the experiment's own `max_steps` or equivalent limits. Request-count budgets constrain call count, not token spend; where cost matters, distinguish expected/planning spend from theoretical maximum token exposure rather than calling request count a hard dollar ceiling.

If an experiment is intentionally sequential/adaptive, its stopping rule and any required inferential correction must be pre-registered. If a fixed design is extended after looking at results, record the deviation explicitly and do not present the enlarged analysis as if the original stopping rule were preserved.

### 14.2 Metric semantics

Initial evaluation should be deterministic wherever possible.

Score separately:

1. initial routing/tool selection;
2. initial argument correctness;
3. eventual use of the expected capability;
4. recovery after an initially incorrect or unnecessary call;
5. tool-result handling;
6. final-answer correctness;
7. overall task success.

For Phase 0 and later experiments, the primary and secondary metrics must be **pre-registered before real model results are observed**.

For the simple Phase 0 calibration tasks, the default primary routing metric should be:

> The first substantive tool call is the expected tool and contains exactly the expected identifying argument(s).

For this metric, argument key/value comparison is order-insensitive but exact after schema-valid canonicalization: missing expected arguments, incorrect values, invalid values, or unexpected extra arguments make the argument component incorrect.

Secondary metrics should distinguish at minimum:

- whether the expected tool was eventually used;
- whether it was eventually used with correct arguments;
- whether the agent recovered after an initially incorrect call;
- final task success;
- number of incorrect or unnecessary tool calls.

`tool_recovery_success` is **null / not applicable** when the first substantive call already satisfies the primary routing metric. It is `true` or `false` only when recovery was actually required.

Final `task_success` remains independent of tool-use correctness and must use the task's pre-declared deterministic answer-evaluation strategy.

A different primary definition may be used when a future task genuinely requires multi-tool planning, but it must be declared before observing results for that experiment.

Avoid LLM-as-judge when a deterministic answer is available.

Later experiments may introduce semantic or LLM evaluation, but it must be an explicit evaluator type rather than an invisible default.

---

## 15. CLI

Desired commands:

```bash
agent-lab list experiments
agent-lab validate <experiment-config>
agent-lab run <experiment-config>
agent-lab summarize <experiment-id-or-result-path>
```

Later, if useful:

```bash
agent-lab compare <condition-a> <condition-b>
agent-lab inspect <run-id>
```

The CLI may provide progress/status, but persisted traces/results are the source of truth.

---

## 16. Phase 0 Calibration Experiment

### Research classification

**Calibration / positive control. Not intended as a novel research contribution.**

### Question

Can the lab reliably detect task regression when semantically overlapping capabilities are added to an otherwise stable tool-space?

### Condition A

Five distinct baseline tools.

### Condition B

The same five baseline tools plus five intentionally overlapping customer tools.

### Controls

Keep constant:

- model;
- model parameters;
- system instructions;
- tasks;
- fixture data;
- evaluator and pre-registered metric definitions;
- MCP transport;
- retry policy;
- provider-adapter behaviour;
- all model-visible content other than the intended tool-space change.

The tool-space is the intended manipulated variable.

Before the first real Phase 0 run:

1. record the exact baseline and overlap canonical environment descriptors and model-visible surfaces;
2. record their environment and model-surface fingerprints;
3. verify that no research-design language leaks into the model-visible surface;
4. pre-register the primary routing metric and secondary recovery/task-success metrics;
5. freeze the exact fixture/task set and evaluator definitions for that calibration run;
6. pre-register the analysis unit/generalization target, repeated-run aggregation rule, uncertainty/reporting method, and any direct-exposure versus non-target/spillover strata;
7. pre-register the deterministic/reproducibly seeded execution-order strategy and persist the realized schedule;
8. freeze the exact task count, repetition count, provider/request budget, and stopping/replacement rule, including whether operational failure invalidates individual runs or the whole execution;
9. declare the smallest primary-metric difference considered practically meaningful; for Phase 0 treat any defensible detectability/MDE estimate primarily as an **instrument-sensitivity statement** (what this calibration design can reliably resolve), not as a requirement that calibration must produce a particular regression size;
10. if an A/A or equivalent repeatability check is used, pre-register it as apparatus calibration and keep it distinct from the baseline-vs-overlap research comparison.

Fixture/task data may be expanded or corrected while Phase 0 is still being designed. Once the pre-registration is committed and its task/fixture fingerprints are frozen, do not modify that material for the bound execution. A changed task or fixture set constitutes a new explicitly versioned design, not a continuation of the frozen one.

### Phase 0 analysis unit

For the headline Phase 0 baseline-vs-overlap comparison, the **task is the unit of generalization** and repetitions are within-task replicates used to characterise stochasticity.

For the primary routing metric:

1. compute the within-condition primary-metric rate for each frozen task across its repetitions;
2. compare baseline and overlap as paired task-level values;
3. summarize condition-level accuracy from those task-level values;
4. retain all run-level rows and traces as evidence, but do not treat repeated runs of one task as additional independent task samples for claim-bearing interpretation.

This choice is specific to Phase 0's frozen paired task set. Future novelty-gated experiments may choose a different unit when their hypothesis requires it, but must pre-register that choice.

If the Phase 0 manipulation directly targets only a subset of expected tools/tasks, pre-register that **direct-exposure stratum** separately from any **non-target/spillover stratum**. The headline calibration effect should be computed on the stratum the manipulation directly targets unless the pre-registration gives a principled reason to pool. Non-target tasks may be reported separately to reveal broader tool-space/context spillover, but must not be silently mixed into the primary targeted effect.

### Initial execution

While debugging:

- 1-3 tasks;
- one model;
- one run.

Once the harness is trustworthy, the planning range is:

- approximately 20-30 tasks;
- one model;
- at least 3 repetitions where budget permits.

The actual Phase 0 pre-registration must replace those planning ranges with an **exact** frozen task count, repetition count, and provider/request budget before observing baseline-vs-overlap results.

### Required outputs

- primary first-call routing accuracy by condition;
- eventual expected-tool-use / recovery accuracy by condition;
- final task success by condition;
- incorrect/unnecessary tool-call counts;
- per-task routing regressions;
- per-task task-success regressions;
- raw traces for regressions and representative recoveries;
- simple comparison chart;
- notes on any unexpected behaviour.

### Calibration success criterion

A successful calibration does **not** require a specific regression percentage.

Calibration succeeds if:

1. the experiment is valid and controlled;
2. model/tool interactions are fully inspectable;
3. the evaluator correctly distinguishes outcomes;
4. condition comparison is reproducible enough to reason about;
5. any regression or non-regression can be explained from preserved evidence.

If a clear known interference effect appears, that is sufficient to validate the instrument.

### Mandatory stop

After Phase 0:

> **STOP.**

Do not automatically build a large matrix of tool-count, naming, description, schema, ordering, or multi-model experiments.

Record the result, inspect the traces, and invoke the novelty gate before selecting the first real research question.

---

## 17. Research Notebook Discipline

### `research/hypotheses.md`

For each hypothesis record:

- ID;
- statement;
- rationale;
- prediction;
- falsification condition;
- related experiment IDs.

### `research/observations.md`

This is a first-class research artifact.

Record surprising behaviour before trying to eliminate it.

Suggested format:

```markdown
## 2026-XX-XX - Observation O-001

### Observation
Describe the behaviour precisely.

### Conditions
What changed and what remained constant?

### Unexpected detail
What made the result surprising?

### Candidate explanations
List alternatives rather than prematurely selecting one.

### Follow-up
What smallest experiment would discriminate among explanations?
```

### `research/experiment-log.md`

Record:

- experiment;
- commit;
- result paths;
- major findings;
- limitations;
- next questions.

### `research/research-backlog.md`

Store ideas without implying that they should be implemented.

### `research/novelty/`

Store the evidence and decision from each novelty gate.

---

## 18. Reproducibility Requirements

Persist:

- resolved experiment config;
- exact task dataset/version;
- exact capability/environment version;
- provider/model identifier;
- model parameters;
- apparatus source Git SHA and dirty-tree state;
- external research-workspace Git SHA and dirty-tree state when applicable;
- execution timestamp;
- apparatus dependency lockfile/hash;
- raw traces;
- normalized results.

If a provider cannot provide deterministic seeds or immutable model snapshots, document the limitation.

Record the exact provider-supported generation controls used for every run. Do not assume a universal `temperature` control exists. For models where temperature is unsupported or deprecated, omit it and rely on repeated runs plus explicit recording of the controls the provider actually supports (for example thinking mode and effort).

Do not imply stronger reproducibility than the external API permits.

### 18.1 External research workspaces

Agent Systems Lab may execute an experiment whose definition, preregistration, study-specific materials, analysis, and results live in another repository. This is a supported research organization pattern, not a second copy of the apparatus.

The intended separation is:

```text
agent-systems-lab
    reusable apparatus/runtime

external research workspace
    literature/novelty notes
    hypotheses
    preregistration
    experiment definitions/tasks/materials
    private/raw results
    study-specific analysis
    paper/publication material
```

The apparatus repository may continue to evolve independently. Each real study must pin the exact apparatus commit actually used for that study, and the execution evidence must record it.

External experiment/config paths and external result roots must not weaken the existing fingerprinting, provider-request preservation, trace authority, paid-run gates, or clean/dirty provenance discipline.

Changing the physical result root must not change the semantic identity of a trace reference. `trace_path` remains execution-root-relative whether results are written inside the apparatus repository or into an external research workspace.

The experiment's Git workspace is not itself the apparatus. Running the same apparatus from a different CWD must not change apparatus provenance.

When study-specific files beyond the resolved experiment/task definitions become model-visible or behaviourally relevant (for example future memory entries, few-shot examples, retrieval corpora, or other `materials/`), the study must define and persist an appropriate canonical fingerprint/binding for that material before the claim-bearing run. Do not pre-build a generic material registry before a concrete novelty-gated experiment requires one.

Evidence authority is:

> **raw trace > normalized result row > aggregate summary**

Normalized rows and summaries are derived conveniences. If they disagree with a valid raw trace, the trace wins and the derivation bug must be fixed.

---

## 19. Cost Controls

Required safeguards:

- configurable max tasks per run;
- configurable repetitions;
- dry-run/config validation;
- optional run-size/request-count preview;
- explicit provider/model selection;
- **explicit paid-run opt-in at execution time** before any provider call that can incur cost;
- credentials being present must not by themselves authorize paid execution;
- no accidental large experiment grids;
- paid integration tests excluded by default.

Workflow:

```text
1-3 task smoke test
        |
        v
verify traces and evaluator
        |
        v
small full condition
        |
        v
inspect evidence
        |
        v
only then scale
```

Frontier models are validation instruments, not the default development loop.

---

## 20. Testing Requirements

Unit tests should cover at least:

- configuration validation;
- task loading;
- tool-space loading;
- environment identity/version handling;
- deterministic evaluator;
- trace serialization;
- result serialization;
- synthetic tool behaviour;
- comparison logic.

Provide integration tests using a deterministic fake model adapter.

Default test execution must never make paid model API calls.

---

## 21. Environment and Secrets

Provider credentials must use environment variables.

Example:

```text
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

Provide `.env.example`.

Gitignore `.env` and all credential-bearing material.

Never store credentials in traces or raw provider payloads.

---

## 22. Documentation and Agent Continuity

### README

Explain:

- what Agent Systems Lab is;
- why it exists;
- current research status;
- installation;
- test commands;
- how to run the current experiment;
- result/trace locations;
- how to define tasks and environments;
- how research gates work.

### AGENTS.md

Create a concise, agent-neutral instruction file for any coding agent working in this repository.

It should include at minimum:

- read `SPEC.md` before major work;
- preserve experimental transparency;
- distinguish calibration from frontier research;
- do not implement a new research programme without a selected novelty-gated question;
- do not add heavy agent frameworks without explicit approval;
- do not silently change experimental controls;
- preserve raw traces and negative results;
- prefer deterministic evaluation;
- add tests for harness changes;
- never make paid API calls in default tests;
- do not optimize experiments to confirm hypotheses;
- document methodological compromises;
- treat unexplained behaviour as potential research data;
- keep platform work subordinate to research questions.

### CLAUDE.md

If Claude Code is used, create a root-level `CLAUDE.md` that imports:

```text
@AGENTS.md
```

Add only Claude Code-specific workflow guidance that is genuinely useful.

Do not duplicate the full specification.

### Continuity expectation for any AI agent

An agent joining the project should be able to read:

```text
SPEC.md
AGENTS.md
research/experiment-log.md
research/observations.md
research/novelty/
```

and answer:

1. What is the researcher's long-term goal?
2. What has already been built?
3. What has actually been observed?
4. Which findings are calibration versus potentially novel?
5. What research question is currently active?
6. What must not be implemented yet?
7. What is the next decision or experiment?

If these files do not make those answers clear, update the documentation.

---

## 23. Implementation Milestones

Milestones 0-4 establish and calibrate the **initial research instrument**. They are not a commitment to a fixed frontier-research roadmap.

After Milestone 4, stop and pass through Research Gate 1 before defining another implementation milestone.

### Milestone 0 - Repository foundation

Deliver:

- Python project;
- dependencies;
- minimal directory structure;
- lint/type/test setup;
- README skeleton;
- `AGENTS.md`;
- `CLAUDE.md` if Claude Code is in use;
- `.env.example`.

Acceptance:

```bash
uv sync
uv run pytest
```

works on a clean clone without provider credentials.

### Milestone 1 - Deterministic synthetic MCP environment

Deliver:

- synthetic fixture data;
- five baseline MCP tools;
- five overlapping calibration tools;
- tests for deterministic tool behaviour.

Acceptance:

Every tool can be invoked through the real MCP client layer and returns deterministic fixture data.

### Milestone 2 - Core experiment harness

Deliver:

- task loader with declared deterministic answer-evaluation strategy;
- tool-space/environment loader;
- canonical EnvironmentDescriptor + environment fingerprint;
- canonical model-visible surface representation + model-surface fingerprint;
- stable logical run identity plus physical execution identity;
- experiment config;
- model adapter interface;
- fake deterministic model adapter;
- trace recorder preserving the complete ordered tool-call sequence;
- deterministic evaluator with explicit metric definitions;
- normalized result model derived from the raw trace;
- Parquet persistence.

Acceptance:

A fake adapter can execute a complete experiment without external APIs, and:

- the raw trace preserves every ordered tool call rather than a singular selection;
- derived routing/recovery fields can be reproduced from that trace;
- the environment descriptor/fingerprint is stable for unchanged semantic MCP/environment state;
- the model-surface fingerprint is stable when the actual adapter-visible capability surface is unchanged and changes when that surface changes;
- MCP-client-visible metadata that is not passed to the model does not falsely change the model-surface fingerprint;
- model-visible capability metadata can be inspected without exposing internal research-design annotations;
- result rows are reproducibly derived from raw traces;
- repeated physical executions can share a logical `run_id` without overwriting one another.

### Milestone 3 - First real provider

Implement one real provider adapter.

If Claude is the initial experimental subject, Anthropic is a reasonable first choice.

The real-provider smoke experiment is classified as a **harness check**, not calibration/frontier research.

Acceptance:

A 1-3 task smoke experiment can run against the configured provider and persist complete evidence.

Provider execution that can incur cost must require explicit run-time opt-in. Merely configuring API credentials is insufficient authorization to make paid calls.

The implementation must preserve separately:

- canonical MCP/environment descriptor;
- canonical model-visible surface;
- stable provider-facing capability/config surface and fingerprint;
- exact full provider request body for every turn;
- raw/provider-native response material required to reconstruct or continue the interaction.

The adapter must preserve any provider-native assistant blocks that the provider requires to be replayed unchanged on subsequent tool-use turns.

Provider-specific model controls used by the smoke run must be explicit and recorded. Do not send unsupported generic controls merely because they appeared in an earlier example configuration.

Credentials and secrets must never enter traces/results.

### Milestone 4 - Phase 0 calibration

Before execution, deliver a pre-registration record containing:

- frozen task set;
- exact baseline and overlap canonical environment descriptors plus model-visible surfaces/fingerprints;
- primary routing metric definition;
- secondary recovery/task-success metric definitions;
- evaluator rules;
- planned repetitions and comparison method;
- known limitations.

Then deliver:

- 20-30 simple deterministic tasks;
- baseline condition;
- semantic-overlap condition;
- experiment config;
- comparison summary;
- routing-regression and task-success-regression extraction;
- simple plot.

Acceptance:

The researcher can inspect both aggregate results and every individual regressed/recovered task, and can verify that metric definitions and model-visible surfaces were fixed before observing the real model results.

### Research Gate 1 - Select first frontier question

Immediately after Milestone 4 / successful Phase 0 calibration:

**Do not continue automatically into another implementation milestone.**

1. summarize calibration results;
2. record observations;
3. inspect unexpected behaviour;
4. perform a current-literature novelty search;
5. select, narrow, reframe, or stop the candidate frontier direction based on that review;
6. write the novelty review and the resulting hypothesis or exploratory objective;
7. identify the smallest additional apparatus capability, if any, required to test that question;
8. only then define Milestone 5.

There is intentionally **no pre-written Milestone 5**.

The evidence and current literature determine Milestone 5.

A valid Milestone 5 might be:

- a small generic apparatus extension required by the selected question;
- a controlled pilot that validates a newly required experimental surface;
- the first frontier experiment itself if the existing apparatus is already sufficient.

Do not assign a milestone number to infrastructure merely because it is convenient to build.

### Deferred research-enablement backlog - not a gate

Further analysis ergonomics may be useful, including:

- richer DuckDB querying;
- run inspection;
- regression extraction;
- condition comparison;
- study-specific comparison/reporting helpers.

These are **not** prerequisites for Research Gate 1.

Implement or promote them into a milestone only when an active research question makes the need concrete. Prefer the smallest ergonomics that reduce real research friction over a generic analysis platform designed in advance.

Existing analysis capabilities remain valid and may continue to be used; this change only removes speculative ergonomics work as a blocker to research-question selection.

---

## 24. Coding-Agent Execution Instructions

If an autonomous coding agent implements this specification:

For each implementation milestone:

1. inspect repository state;
2. read relevant research/documentation context;
3. propose only necessary architecture decisions;
4. implement the smallest coherent slice;
5. add or update tests;
6. run test/lint/type checks;
7. update documentation where state changed;
8. summarize exactly what changed;
9. identify deviations from this specification;
10. stop at the milestone boundary.

Do not build future milestones early because they appear easy.

Do not introduce speculative abstractions.

If a decision may materially alter experimental methodology, surface it for researcher review instead of silently choosing.

If current published work appears to make a planned research direction redundant, say so.

Do not treat the specification as evidence that a research hypothesis is novel. Novelty is time-sensitive and must be rechecked.

---

## 25. Definition of Done for the Initial Instrument

Milestones 0-4 define the build/calibration sequence for the initial instrument. Additional analysis ergonomics are not a prerequisite for entering Research Gate 1.

The lab is established when:

1. a clean clone installs and tests locally;
2. deterministic synthetic MCP capabilities exist;
3. deterministic calibration tasks exist;
4. one real model can execute those tasks through the MCP environment;
5. every run preserves detailed raw traces;
6. results are stored in normalized Parquet;
7. DuckDB can compare conditions;
8. Phase 0 baseline-vs-overlap calibration can run from a declared config;
9. individual regressions can be extracted and inspected;
10. research observation/hypothesis/novelty files exist;
11. an external coding/research agent can understand the project state from repo documentation;
12. the researcher can understand the complete agent loop without relying on a general agent framework.

At this point:

> **Stop building the platform. Enter Research Gate 1 and start selecting research questions.**

---

## 26. First Instrument Success Criterion

A valid first outcome might look like:

```text
Phase 0 calibration

Baseline tool-space:      28/30 successful
Overlap tool-space:       23/30 successful

Regressed tasks: 5
Improved tasks: 0
Unchanged tasks: 25

Complete traces: available
```

Or it might show little/no regression.

Either result is acceptable if the experiment is controlled and trustworthy.

The purpose is to establish:

> **This lab can manipulate an agent environment, observe model behaviour, preserve evidence, and compare conditions reliably.**

The next question is not automatically:

> "Which tool variable should we sweep next?"

It is:

> **"Given what we observed and what the current research landscape already knows, what is the most valuable unanswered question we can test next?"**

That question should drive the evolution of `agent-systems-lab`.
