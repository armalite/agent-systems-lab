# Agent Systems Lab - Research & Build Specification

**Status:** Active research specification  
**Version:** 2.0  
**Repository:** `agent-systems-lab`

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
|       |   |-- client.py
|       |   `-- types.py
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
|       |-- memory/                 # no speculative implementation initially
|       |   `-- types.py
|       |
|       `-- cli.py
|
|-- servers/
|   `-- synthetic_tools/
|       |-- server.py
|       |-- data.py
|       `-- tools.py
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
- raw provider metadata or a serializable representation.

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

A fingerprint may eventually incorporate:

- tool names;
- descriptions;
- schemas;
- tool versions;
- response contracts;
- other experimentally relevant capability metadata.

Do not overdesign environment versioning during Milestone 0. Establish only enough structure that later experiments can distinguish V1 from V2 without ambiguity.

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
```

Tool-selection correctness and final-answer correctness must be independently measurable.

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
  temperature: 0
  randomize_tool_order: false

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

For future memory research, the trace design should also be capable of recording:

- memory candidates;
- memory writes;
- retrieval queries;
- retrieved memories;
- memory provenance;
- memory invalidation/revalidation events.

Do not implement the full memory subsystem initially.

Credentials must never appear in traces.

---

## 13. Normalized Result Schema

At minimum:

```text
run_id
experiment_id
experiment_classification
timestamp
source_commit_sha

provider
model
model_parameters

environment_id
environment_version
environment_fingerprint

task_id
task_set

tool_space_id
tool_count
tool_names

expected_tool
selected_tool
tool_selection_correct

expected_arguments
actual_arguments
arguments_correct

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

Store normalized batch results in Parquet.

DuckDB must be usable directly against results without requiring application code.

---

## 14. Evaluation

Initial evaluation should be deterministic wherever possible.

Score separately:

1. tool selection;
2. argument correctness;
3. tool-result handling;
4. final-answer correctness;
5. overall task success.

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
- evaluator;
- MCP transport;
- retry policy.

The tool-space is the intended manipulated variable.

### Initial execution

While debugging:

- 1-3 tasks;
- one model;
- one run.

Once the harness is trustworthy:

- approximately 20-30 tasks;
- one model;
- at least 3 repetitions if affordable/useful.

### Required outputs

- success by condition;
- tool-selection accuracy by condition;
- per-task regression list;
- raw traces for regressions;
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
- source Git SHA;
- execution timestamp;
- dependency lockfile;
- raw traces;
- normalized results.

If a provider cannot provide deterministic seeds or immutable model snapshots, document the limitation.

Do not imply stronger reproducibility than the external API permits.

---

## 19. Cost Controls

Required safeguards:

- configurable max tasks per run;
- configurable repetitions;
- dry-run/config validation;
- optional run-size/request-count preview;
- explicit provider/model selection;
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

These milestones establish the **research instrument**. They are not a commitment to a fixed research roadmap.

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

- task loader;
- tool-space/environment loader;
- experiment config;
- model adapter interface;
- fake deterministic model adapter;
- trace recorder;
- deterministic evaluator;
- normalized result model;
- Parquet persistence.

Acceptance:

A fake adapter can execute a complete experiment without external APIs.

### Milestone 3 - First real provider

Implement one real provider adapter.

If Claude is the initial experimental subject, Anthropic is a reasonable first choice.

Acceptance:

A 1-3 task smoke experiment can run against the configured provider and persist complete evidence.

### Milestone 4 - Phase 0 calibration

Deliver:

- 20-30 simple deterministic tasks;
- baseline condition;
- semantic-overlap condition;
- experiment config;
- comparison summary;
- regression extraction;
- simple plot.

Acceptance:

The researcher can inspect both aggregate results and every individual regressed task.

### Milestone 5 - Analysis ergonomics

Deliver only what is necessary to make research iteration efficient:

- DuckDB querying;
- run inspection;
- regression extraction;
- condition comparison.

Acceptance:

The researcher can quickly answer questions such as:

> "Which tasks succeeded before the capability change and failed after it?"

### Research Gate 1 - Select first frontier question

After Milestones 0-5:

**Do not continue automatically.**

1. summarize calibration results;
2. record observations;
3. inspect unexpected behaviour;
4. perform current-literature novelty search;
5. select a frontier research question;
6. write its novelty review and hypothesis/exploratory objective;
7. only then define the next implementation milestone.

There is intentionally **no pre-written Milestone 6**.

The evidence determines Milestone 6.

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

> **Stop building the platform. Start selecting research questions.**

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