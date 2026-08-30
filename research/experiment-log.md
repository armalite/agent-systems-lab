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

## Phase 0 pre-registration (required before Milestone 4 runs)

Before any Phase 0 calibration run is executed, and **before its results are observed**, record
here: the primary and secondary routing/recovery metric definitions, the exact meaning of
`tool_selection_correct` under multi-call runs, and the condition-comparison method. Defining
these after seeing results would make the calibration unfalsifiable.

*Not yet written - Milestone 4 is not in scope.*
