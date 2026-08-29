Agent Systems Lab - Build Specification

1. Purpose

Build a long-lived, reproducible research laboratory for experimentally studying LLM agent systems rather than a one-off agent application.

The initial research programmes are:

Tool-space interference and capability regression - determine when adding tools to an agent's available capability set causes previously successful tasks to fail, identify the mechanisms that cause the regression, and eventually test automatic diagnosis and repair.

Persistent agent memory - determine what an agent should remember, retrieve, update, invalidate and forget across sessions, and measure when memory improves or harms agent performance.

The project must be designed so that new research programmes can be added later without rewriting the core harness.

The guiding principle is: build an experimental instrument, not an agent framework.

2. Core Research Questions

2.1 Tool-space interference

Initial questions:

Does task success decrease as additional irrelevant tools are added?

Does semantic overlap between tools cause more regression than raw tool count?

How do tool names, descriptions, schemas, examples and ordering affect selection accuracy?

Are interference effects model-specific?

Can interfering tool pairs or clusters be identified automatically?

Can an automated process modify the capability representation and recover lost performance without overfitting the evaluation set?

Important property to investigate:

Capability addition may be non-monotonic: adding a new capability can reduce the effective capability of the complete system.

2.2 Persistent memory

Initial questions:

Which kinds of information are worth preserving between sessions?

Is structured memory more useful than transcript summaries or full-history replay?

How should episodic, semantic and procedural memories be represented?

How accurately can relevant memories be retrieved?

When does stale memory degrade performance?

How should procedural memories be invalidated when tools or environments change?

2.3 Intersection of tools and memory

Later experiments should examine whether learned procedural memories improve future tool selection and what happens when the tool environment subsequently changes.

This creates a particularly important systems question:

How should an agent invalidate learned procedural knowledge when its capability environment changes?

3. Scope

In scope for the initial implementation

Python research harness.

Direct model-provider integrations.

Real MCP client/server interactions.

Synthetic deterministic MCP tools.

Deterministic task datasets with known expected outcomes.

Experiment configuration and execution.

Detailed trace capture.

Automated scoring.

Repeated runs and controlled comparisons.

Parquet result storage and DuckDB analysis.

CLI for running experiments.

Basic plots and tabular summaries.

Provider/model abstraction sufficient to compare multiple models later.

Initial tool-interference experiment suite.

Foundation for a future memory experiment suite.

Explicitly out of scope initially

Do not build any of the following unless a later experiment requires it:

General-purpose production agent framework.

Web application or dashboard.

Kubernetes deployment.

Cloud infrastructure.

Kafka or distributed eventing.

Postgres.

Vector database service.

LangChain.

LlamaIndex.

CrewAI.

AutoGen.

Large orchestration frameworks.

Multi-agent architecture.

Automatic self-healing of tool definitions in the first milestone.

Production-grade auth or tenancy.

Avoid abstractions that make it difficult to determine exactly what context, tools and messages were presented to a model.

4. Technical Principles

The implementation must prioritize:

Reproducibility - every result must be attributable to a model, experiment config, task definition, tool-space definition and run configuration.

Observability - preserve raw interactions, not only final scores.

Controlled experimentation - changing a variable should not silently change other variables.

Transparency - direct SDK and MCP use is preferred over hidden framework behaviour.

Provider neutrality - provider-specific code must not leak throughout the research harness.

Extensibility - new experiments should mostly require datasets/configs, not core rewrites.

Cheap iteration - small local experiments should be possible before spending on frontier-model sweeps.

Research integrity - do not optimize implementation around producing a desired experimental outcome.

5. Preferred Technology Stack

Use:

Python 3.12+

uv for dependency/environment management

pytest

pydantic

typer

rich

official MCP Python SDK

provider SDKs directly (Anthropic/OpenAI initially; additional providers later)

duckdb

pyarrow

pandas only where useful for analysis

matplotlib for simple plots

structured JSON/JSONL for raw traces

Parquet for normalized experiment results

Use static typing throughout sensible public interfaces.

A lightweight formatter/linter/type-checking setup is desirable, e.g. Ruff plus Pyright or equivalent.

6. Repository Structure

Target structure:

agent-systems-lab/
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
|       |-- memory/                 # foundation only initially
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
|   |-- tool_interference/
|   |   |-- configs/
|   |   |-- datasets/
|   |   |-- toolspaces/
|   |   `-- analysis/
|   |
|   `-- memory/
|       |-- configs/
|       |-- datasets/
|       `-- analysis/
|
|-- results/                        # gitignored except small fixtures/examples
|-- research/
|   |-- hypotheses.md
|   |-- observations.md
|   |-- experiment-log.md
|   `-- research-backlog.md
|
|-- tests/
|-- .env.example
|-- .gitignore
|-- pyproject.toml
|-- README.md
`-- AGENTS.md

The exact module names may change if there is a strong technical reason, but preserve the separation of concerns.

7. Core Domain Model

7.1 Model adapter

Define a provider-neutral model interface.

Conceptually:

class ModelAdapter(Protocol):
    async def run(self, request: AgentRequest) -> AgentResponse:
        ...

The request must allow:

system instructions

user/task input

available tools

conversation state

temperature / provider-supported generation controls

metadata required for tracing

The response must expose:

final model output

tool calls

tool arguments

tool results/observations

usage/token information where available

latency

provider request identifiers where available

raw provider response or a serializable representation

Do not normalize away provider-specific information that might later prove experimentally relevant. Store normalized fields plus provider-specific raw metadata.

7.2 Task definition

Each deterministic task should include at minimum:

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

The evaluator must be able to score tool selection separately from final answer correctness.

7.3 Tool-space definition

Tool sets must be declarative and versioned.

Example:

id: customer_baseline_v1
tools:
  - get_customer
  - get_order
  - get_invoice
  - get_product
  - get_employee

And an interference variant:

id: customer_overlap_v1
extends: customer_baseline_v1
tools:
  - find_customer
  - search_customers
  - get_customer_details
  - lookup_customer
  - customer_information

Where practical, experiment variants should alter metadata/config rather than duplicating source code.

7.4 Experiment definition

Experiments should be declarative.

Example:

id: tool_interference_001
research_question: "Do semantically overlapping tools reduce tool-selection accuracy?"

model:
  provider: anthropic
  name: <configured-model>

task_set: customer_baseline_tasks_v1

tool_spaces:
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

Experiment configuration must be included in saved results.

8. Synthetic MCP Server

Build a deterministic MCP server specifically for controlled research.

Initial baseline tools:

get_customer(customer_id)

get_order(order_id)

get_invoice(invoice_id)

get_product(product_id)

get_employee(employee_id)

Use a fixed in-memory or fixture-backed dataset checked into the repo.

No external API/network dependencies should be required for the synthetic server.

The baseline tools should have clear, distinct semantics.

Initial overlapping tools

Add controlled variants such as:

find_customer(name) - search by customer name

search_customers(query) - broad fuzzy customer search

get_customer_details(customer_id) - extended profile after ID is known

lookup_customer(email) - lookup by email address

customer_information(customer_id) - deliberately similar to get_customer

The exact semantic overlap should be documented so experiments can distinguish intentionally similar tools from unrelated distractors.

Later, allow tool metadata to be varied without changing tool execution behaviour:

name

description

parameter names

schema shape

examples if supported by the client/harness

description length

ordering

9. First Task Dataset

Create 20-30 deterministic baseline tasks spanning the five baseline tools.

Characteristics:

approximately balanced across tools

unambiguous expected tool

deterministic tool result

deterministic factual final answer

simple enough that errors primarily reflect tool interaction rather than domain reasoning

Examples:

"What is the email address of customer C102?"

"What is the status of order O204?"

"What amount is due on invoice I301?"

"What category is product P502?"

"Which office is employee E104 assigned to?"

Do not make the initial tasks intellectually difficult.

The experiment is measuring capability selection, not general knowledge.

10. Trace Model

Raw trace preservation is mandatory.

Every run should produce a trace containing ordered events such as:

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

Each event should include:

timestamp

run ID

experiment ID

task ID

model/provider

sequence number

event-specific payload

Do not depend only on console logs.

Persist machine-readable raw traces to disk, ideally JSONL per run or per experiment batch.

Sensitive API credentials must never appear in traces.

11. Normalized Result Schema

At minimum save:

run_id
experiment_id
experiment_version
timestamp
provider
model
model_parameters
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

Store normalized batch results in Parquet.

DuckDB queries should be able to compare experiment conditions without requiring application code.

12. Evaluation

The initial evaluator should be deterministic wherever possible.

Score separately:

tool selection

argument correctness

tool result handling

final answer correctness

overall task success

Avoid LLM-as-judge for the initial dataset because deterministic answers are available.

Where textual comparison is required, prefer structured extraction or canonicalized exact comparisons.

Later research can add semantic/LLM evaluation as a separate evaluator type.

13. CLI

Provide an ergonomic CLI.

Desired commands:

agent-lab list experiments
agent-lab validate experiments/tool_interference/configs/tool_interference_001.yaml
agent-lab run experiments/tool_interference/configs/tool_interference_001.yaml
agent-lab summarize <experiment-id-or-result-path>

Nice-to-have later:

agent-lab compare baseline overlap
agent-lab inspect <run-id>

The CLI should display concise progress but must not be the source of truth for results.

14. Experiment 001 - Baseline vs Semantic Overlap

This is the first milestone and should be implemented before generalized research features.

Hypothesis

Adding semantically overlapping tools will reduce tool-selection accuracy on tasks that previously succeed with a smaller, distinct tool-space.

Conditions

Condition A: Baseline

Five distinct tools.

Condition B: Semantic overlap

The same five tools plus five customer-related tools with overlapping names/descriptions/semantics.

Controlled variables

Keep constant:

model

model parameters

system instruction

tasks

synthetic data

evaluator

transport

retry policy

Only the tool-space should change in the first comparison.

Execution

Initially:

20-30 tasks

one model

temperature 0 if supported

one run per condition while debugging

then at least 3 repetitions for a useful result

Required output

Produce:

overall success by condition

tool-selection accuracy by condition

per-task regression list

raw traces for regressed tasks

simple chart comparing baseline and overlap

Example summary:

Condition                 Success   Tool Selection
-------------------------------------------------
baseline                   93.3%        96.7%
semantic_overlap           76.7%        80.0%

Regressed tasks: 6
Improved tasks: 1
Unchanged tasks: 23

Do not implement automatic repair yet.

15. Subsequent Tool-Interference Experiments

After Experiment 001 works reliably, make it possible to systematically vary one dimension at a time.

Candidate dimensions:

Tool quantity

5

10

20

50

100

Semantic similarity

unrelated

weakly related

strongly related

near duplicate

Description quality

precise

normal

ambiguous

misleading

Naming similarity

Examples:

get_customer

customer_get

retrieve_customer

search_customer

lookup_customer

Description length

short

medium

long

extremely verbose

Ordering

expected tool first

expected tool middle

expected tool last

randomized

Provider/model

Compare multiple models only after the experiment is stable on one provider.

16. Future Tool-Space Diagnosis and Repair

Do not implement during the first milestone, but design the harness so this can be added later.

Long-term loop:

existing tool-space
        |
        + new tool
        v
run regression suite
        v
detect degraded tasks
        v
identify likely interfering tools/clusters
        v
propose metadata/schema/routing changes
        v
rerun development evals
        v
run held-out evals
        v
accept or reject proposed change

Possible repair actions:

improve descriptions

rename tools

alter parameter terminology

change schemas

remove redundant tools

group tools

alter visibility/routing

modify context supplied to the model

Any automatic repair system must use a held-out evaluation set to reduce eval overfitting.

17. Memory Research Foundation

The initial build only needs interfaces/types and directory structure for memory research, not a complete memory system.

Later create experimental conditions such as:

Condition 0 - No memory

Session 2 receives no information from Session 1.

Condition 1 - Full transcript

Replay complete history.

Condition 2 - Summary memory

Generate a compact summary after Session 1 and provide it to Session 2.

Condition 3 - Episodic retrieval

Store discrete experiences and retrieve relevant entries for Session 2.

Condition 4 - Structured memory

Example conceptual representation:

semantic:
  customer_output_preference: CSV

procedural:
  customer_lookup_requires: account_id

episodic:
  - event: endpoint_a_failed
    timestamp: ...

confidence:
  customer_lookup_requires: 0.91

Candidate metrics:

downstream task success

token usage

retrieval precision

retrieval recall where measurable

stale-memory usage

incorrect-memory usage

latency

18. Tool-Memory Interaction Experiments

Later create a scenario such as:

Agent uses Tool A incorrectly.

Agent learns that Tool B is correct for a task pattern.

This procedural memory improves later performance.

The MCP environment changes and Tool B's semantics are modified or Tool C supersedes it.

Measure whether retained procedural memory now causes regression.

Potential research themes:

memory invalidation

capability-version awareness

environment fingerprints

confidence decay

contradiction detection

memory provenance

automatic forgetting

19. Research Notebook Discipline

Create and maintain these files manually or semi-automatically.

research/hypotheses.md

Track hypotheses before experiments are run.

Each hypothesis should contain:

ID

statement

rationale

predicted result

falsification condition

related experiments

research/observations.md

This is a critical research artifact.

Record unexpected behaviour, even when it appears small.

Suggested format:

## 2026-08-29 - Observation O-001

### Observation
Adding `lookup_customer_by_email` caused selection accuracy for
ID-based `get_customer` tasks to fall from 96% to 81%.

### Unexpected detail
Removing examples from the new tool restored accuracy to 93%.

### Candidate hypothesis
Examples may dominate semantic routing more strongly than tool descriptions.

### Follow-up
Create an experiment holding name/schema constant while varying examples only.

research/experiment-log.md

Record completed experiments, links/paths to results, major findings and follow-ups.

research/research-backlog.md

Store ideas without implementing them immediately.

20. Reproducibility Requirements

Every experiment result must be reconstructable as far as external model APIs permit.

Persist:

experiment config

exact task dataset version

exact tool-space version

provider/model identifier returned/used

model parameters

source Git commit SHA

execution timestamp

dependency lockfile

raw traces

normalized results

If a provider does not expose deterministic seeds or immutable model snapshots, document that limitation rather than pretending results are perfectly reproducible.

21. Cost Controls

The harness should support cheap development.

Required safeguards:

configurable maximum tasks per run

configurable repetitions

dry-run/config validation

optional estimated/request-count summary before a sweep

provider/model selected by config/environment

no accidental default to very large experiment grids

Development workflow:

run 1-3 tasks

verify trace/evaluator correctness

run complete small condition

inspect results

only then increase repetitions/models

Frontier-model sweeps should be intentional validation steps, not the default debugging path.

22. Testing Requirements

Unit tests should cover at least:

config parsing/validation

task loading

tool-space loading

deterministic evaluator

trace serialization

result serialization

synthetic tool behaviour

experiment comparison logic

Provide integration tests that can run without paid model APIs by using a deterministic fake model adapter.

Paid-provider tests must be explicitly marked and excluded from the default test suite.

No test suite should make billable API calls unexpectedly.

23. Environment and Secrets

Use environment variables for provider credentials.

Provide .env.example, for example:

ANTHROPIC_API_KEY=
OPENAI_API_KEY=

.env and credentials must be gitignored.

Never persist credentials in raw provider responses or traces.

24. Documentation Requirements

README

Explain:

what Agent Systems Lab is

current research programmes

installation

configuration

how to start synthetic MCP server if required separately

how to run Experiment 001

where results and traces are stored

how to add a new task

how to add a new tool-space variant

how to add a new model adapter

AGENTS.md

Create instructions for coding agents working in the repository.

At minimum tell them:

preserve experimental transparency

do not add agent frameworks without explicit approval

do not silently alter experimental controls

preserve raw traces

prefer deterministic evaluation

add tests for harness changes

never make paid API calls from tests by default

do not optimize experiments to produce the expected hypothesis

document methodological compromises

25. Implementation Milestones

Milestone 0 - Repository foundation

Deliver:

Python project

dependencies

directory structure

lint/type/test setup

README skeleton

AGENTS.md

.env.example

Acceptance:

uv sync
uv run pytest

works on a clean clone without provider credentials.

Milestone 1 - Deterministic synthetic MCP environment

Deliver:

synthetic data fixtures

five baseline MCP tools

five overlapping customer tools

tests for tool behaviour

Acceptance:

Every tool returns deterministic fixture data and can be invoked through the MCP client layer.

Milestone 2 - Core experiment harness

Deliver:

task loader

tool-space loader

experiment config

model adapter interface

trace recorder

deterministic evaluator

normalized result model

Parquet persistence

Acceptance:

A fake model adapter can execute a complete experiment with no external APIs.

Milestone 3 - First real provider

Deliver one production provider adapter, preferably Anthropic first if Claude is the initial experimental subject.

Acceptance:

A 1-3 task smoke experiment can execute against a configured provider and save complete traces/results.

Milestone 4 - Experiment 001

Deliver:

20-30 baseline tasks

baseline tool-space

semantic-overlap tool-space

experiment config

comparison summary

simple chart

Acceptance:

A single command runs the experiment and produces inspectable results comparing the two conditions.

Milestone 5 - Analysis ergonomics

Deliver:

DuckDB result querying

run inspection

regression-task extraction

condition comparison

Acceptance:

The researcher can quickly answer: "Which tasks succeeded in baseline but failed after the new tools were introduced?"

Milestone 6 - Second provider

Only after Milestones 0-5 are stable.

Add another provider adapter and run the same experiment unchanged.

Milestone 7 - Memory experiment foundation

Only after the initial tool-space lab is trustworthy.

Implement persistent memory interfaces and the first no-memory/full-history/summary comparison.

26. Coding-Agent Execution Instructions

If an autonomous coding agent is implementing this specification, it should work in milestone order.

For each milestone:

inspect current repository state

propose only necessary architecture decisions

implement the smallest coherent slice

add/adjust tests

run tests/lint/type checks

update relevant docs

summarize exactly what changed

identify any deviation from this spec and why

Do not build future milestones early merely because they appear straightforward.

Do not add speculative abstractions without a demonstrated current need.

When the specification leaves a minor implementation detail open, choose the simplest transparent implementation and document the decision.

If a decision could materially alter experimental methodology, do not silently choose. Record it clearly for researcher review.

27. Definition of Done for the Initial Project

The initial project is considered successfully established when:

A clean clone can install and test locally.

A deterministic synthetic MCP server exposes baseline and overlapping tools.

20-30 deterministic tasks exist with known expected tool calls and answers.

At least one real model provider can execute the task set using the MCP tools.

Every run preserves detailed raw traces.

Results are persisted in normalized Parquet format.

DuckDB can compare conditions.

Experiment 001 compares baseline vs semantic-overlap tool-spaces.

The output identifies individual regressed tasks, not just aggregate accuracy.

Research observation/hypothesis files exist and are ready for ongoing use.

The system is simple enough that the researcher can understand the complete agent loop without relying on a general agent framework.

At that point, stop adding platform features and inspect the experimental results.

The next work should be determined by observed behaviour, not by the original architecture backlog.

28. First Research Success Criterion

The first meaningful success is not "the platform is feature complete."

It is something like:

Baseline tool-space:       28/30 successful
Overlapping tool-space:    22/30 successful

Six previously successful tasks regressed.
Their complete traces are available for inspection.

At that point the research question becomes:

Why did those six regress?

That question, and the experiments it produces, should drive the evolution of the repository.