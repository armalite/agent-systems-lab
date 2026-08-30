"""Deterministic synthetic environment used as controlled experimental apparatus.

Layering is deliberate and load-bearing (see `README.md` in this package):

- `models` / `data` / `tools` are pure Python over checked-in fixtures and **must not import
  `mcp`**. They are directly testable without any transport.
- `toolspaces` declares the model-visible capability surface for each named condition.
- `server` is a thin MCP protocol adapter containing no business logic.

That seam is what later lets a trace attribute a failure to the model rather than to the
transport, and it is why the environment's own determinism can be proven independently.

`SPEC.md` s8 places this inside the installed package rather than a top-level `servers/`
directory, precisely so the deterministic logic stays directly importable and testable without
MCP transport while `server.py` remains a thin real-protocol adapter.
"""
