# Agent Systems Lab

An experimental instrument for studying **evolving LLM agent systems** - what happens to a
persistent agent when its capabilities, environment, and learned experience change over time.

**This is a research laboratory, not an agent framework and not a product.** Its output is
evidence: controlled, reproducible, inspectable observations about agent behaviour. Platform work
exists only to make valid experiments easier to run, inspect, reproduce, and extend.

- `SPEC.md` - authoritative research and build specification.
- `AGENTS.md` - operating rules for any coding/research agent working here.
- `CLAUDE.md` - Claude Code-specific workflow guidance.

## Why it exists

To find poorly understood behaviour in modern LLM agent systems, turn it into controlled
experiments, and publish results that are useful to the wider AI community. Success is one
trustworthy, non-obvious, reproducible observation - not a large feature set.

## Current status

**Milestone 1 complete: deterministic synthetic MCP environment.** Nothing in this repository
can call a model yet.

| Milestone | State |
|---|---|
| M0 - repository foundation | ✅ complete |
| M1 - deterministic synthetic MCP environment | ✅ complete |
| M2 - core experiment harness | not started |
| M3 - first real provider adapter | not started |
| M4 - Phase 0 calibration experiment | not started |
| M5 - analysis ergonomics (DuckDB) | not started |
| Research Gate 1 - select first frontier question | blocked on M0-M5 |

**Active research question:** none. Phase 0 is *calibration only* - a positive control proving
the instrument can detect a known effect. It is explicitly not the intended contribution.

## Installation

Requires [`uv`](https://docs.astral.sh/uv/). Python 3.12+ is fetched by `uv` if needed.

```bash
uv sync
```

No provider credentials are required, and none are used.

## Development

```bash
uv run pytest
```

```bash
uv run ruff check . && uv run ruff format --check .
```

```bash
uv run pyright
```

Pyright requires a Node runtime; it uses the system `node` if present and otherwise downloads one
on first run, so it is the one development command that is not offline-safe on a fresh clone.

Default `pytest` never makes a paid model-provider API call. Provider-hitting tests are marked
`paid` and are deselected unless explicitly requested with `-m paid`.

## Running experiments

Not yet implemented - there is no harness and no model integration. The CLI currently exposes
only:

```bash
uv run agent-lab --version
```

Experiment commands arrive with the milestones that implement the machinery behind them.

## The synthetic environment

A deterministic, fixture-backed MCP server is the controlled apparatus for the Phase 0
calibration. It exposes two named tool-spaces, selected server-side at launch, so the real
`tools/list` surface differs between conditions:

| Tool-space | Tools |
|---|---|
| `customer_baseline_v1` | `get_customer`, `get_order`, `get_invoice`, `get_product`, `get_employee` |
| `customer_overlap_v1` | those five, plus `find_customer`, `search_customers`, `get_customer_details`, `lookup_customer`, `customer_information` |

```bash
uv run python -m agent_lab.synthetic.server --tool-space customer_overlap_v1
```

See [`src/agent_lab/synthetic/README.md`](src/agent_lab/synthetic/README.md) for the fixture
design, determinism guarantees, and the documented intent behind the overlapping tools.

## Results and traces

Not yet implemented. When they exist: raw JSONL traces and normalized Parquet results are written
under `results/`, which is gitignored - experiment output is a reproducible artifact, not source.

## Defining tasks and environments

Not yet implemented (Milestones 1-2). Tasks, tool-spaces, and experiments will be declarative
files rather than code, so new experiments mostly add data rather than rewriting the harness.

## Research gates

Work here is classified as **calibration** (reproduce a known effect to validate the instrument),
**characterisation** (isolate a mechanism), or **frontier research** (the actual purpose).

Any research programme beyond calibration must first pass the novelty gate in `SPEC.md` s3, with
its review recorded under `research/novelty/`. A direction appearing in `SPEC.md` is not evidence
that it is novel, and is not authorisation to implement it.

The research notebook - `research/hypotheses.md`, `research/observations.md`,
`research/experiment-log.md`, `research/research-backlog.md`, `research/novelty/` - is a
first-class research artifact, not documentation overhead.

## License

Apache-2.0. See `LICENSE`.
