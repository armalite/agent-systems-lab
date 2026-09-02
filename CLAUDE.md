# CLAUDE.md

@AGENTS.md

The rules above are binding. This file adds only Claude Code-specific workflow guidance. It
deliberately does not repeat `SPEC.md` - read that file directly for research substance.

---

## Read order for a new session

1. `AGENTS.md` (imported above) - operating rules and current project state (§10).
2. `SPEC.md` - authoritative spec. Do not edit it unless the researcher explicitly asks.
3. `research/experiment-log.md`, `research/observations.md`, `research/novelty/` - what has
   actually happened. These exist and are seeded; empty sections mean "nothing yet", not
   "undocumented".

`AGENTS.md` §10 is the quickest answer to "what exists yet?". Update it whenever project state
changes, in the same commit as the change.

---

## Environment (WSL2, Ubuntu 20.04)

- System `python3` is **3.10**; the project pins **3.12** (`.python-version`). `uv` manages the
  interpreter and virtualenv - never install into the system Python or `pip install` globally.
- Ruff and Pyright are **project dev dependencies**, not global tools. Always invoke them as
  `uv run ruff` / `uv run pyright` so the locked versions are used.
- Pyright needs a Node runtime. It uses the system `node` (nvm v22 here); on a machine without
  one it downloads a runtime on first run. So `uv run pyright` is not offline-safe on a fresh
  clone - unlike `uv sync` and `uv run pytest`, which are, and which are the M0 acceptance.
- Pyright config lives in `pyrightconfig.json`, not `pyproject.toml`: an unrelated
  `pyrightconfig.json` in the parent directory `/home/armalite/dev` otherwise wins pyright's
  upward root discovery and checks the wrong source tree. Do not move it back.
- Ruff is restricted to Python files. Recent versions also format fenced code blocks in Markdown,
  which would rewrite the snippets in `SPEC.md`. Do not remove that `include` setting.
- There is no `gh` CLI on this machine.
- `ANTHROPIC_BASE_URL` is exported in the shell to the real Anthropic API. `ANTHROPIC_API_KEY` is
  not set, and default work must not need it.
- Repository lives on the ext4 Linux filesystem (not `/mnt/c`), so file I/O is fast; keep it there.
- Docker exists on the machine but is out of scope - do not make it a runtime requirement.

---

## Commands

```bash
uv sync
```

```bash
uv run pytest
```

```bash
uv run ruff check . && uv run ruff format --check .
```

```bash
uv run pyright
```

Milestone 0 acceptance - `uv sync` and `uv run pytest` on a clean clone with no provider
credentials - is met and was verified against a scratch copy of the tracked tree.

---

## Cost discipline

**Never make a paid model API call without explicit per-run approval from the researcher**, and
never as a side effect of tests, lint, a fixture refresh, or a "quick check". Default `pytest`
must stay free and offline. Provider-hitting tests are opt-in via an explicit marker/flag.

When a real run is eventually approved: smoke-test 1-3 tasks first, inspect the traces and the
evaluator output, and only then scale. Say the expected request count out loud before running.

---

## Working style in this repo

- **Stop at milestone boundaries.** Report what changed, what deviated from `SPEC.md`, and what
  the next decision is. Do not roll into the next milestone unprompted.
- **Surface methodology decisions instead of deciding them.** Anything touching evaluator
  semantics, controls, success criteria, trace content, environment identity, or model
  configuration goes to the researcher. Use `AskUserQuestion` for a genuine fork; otherwise state
  the assumption clearly and continue.
- Plan mode is worth using before a milestone that touches the experiment harness or the result
  schema - both are expensive to change once results exist.
- Prefer editing real files over long explanatory prose. Prefer reading `SPEC.md` over
  reconstructing its content from memory - it is long, and details matter.
- Do not spawn subagents unless the researcher asks for one.
- Keep commits scoped to a milestone slice, and update `AGENTS.md` §10 and the research notebook
  files in the same commit as the state change. Commit only when asked.

---

## Traps specific to this project

- Claude is fast at generating breadth; this repo punishes breadth. A large tool-sweep matrix,
  extra conditions, or a speculative memory module are **regressions**, not progress. The M5
  memory surface is deliberately one policy and one presentation; adding a second of either
  "for completeness" is exactly this trap, not a gap to fill (`AGENTS.md` §4).
- Do not "fix" surprising model behaviour before it is recorded in `research/observations.md`.
- Do not create empty modules to match the target tree in `SPEC.md` §8.
- Do not restate the spec into README/AGENTS/CLAUDE. Link to it.
