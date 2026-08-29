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

## Phase 0 pre-registration (required before Milestone 4 runs)

Before any Phase 0 calibration run is executed, and **before its results are observed**, record
here: the primary and secondary routing/recovery metric definitions, the exact meaning of
`tool_selection_correct` under multi-call runs, and the condition-comparison method. Defining
these after seeing results would make the calibration unfalsifiable.

*Not yet written - Milestone 4 is not in scope.*
