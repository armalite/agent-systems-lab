# Synthetic MCP Environment

Deterministic, fixture-backed experimental apparatus. Not an experiment, and not a general
tool server: its only purpose is to be a *controlled* capability environment that can be varied
along one declared axis at a time.

## Layering

| Layer | Module | Rule |
|---|---|---|
| Fixtures | `fixtures/*.json` | Fixed literals, checked in. No generation at run time. |
| Records | `models.py` | Typed records and result envelopes. |
| Data | `data.py` | Loading, indexing, integrity checks. **No `mcp` import.** |
| Tools | `tools.py` | Pure deterministic lookups. **No `mcp` import.** |
| Surface | `toolspaces.py` | The model-visible capability surface per condition. |
| Protocol | `server.py` | Thin MCP adapter. No business logic. |

The `tools.py` / `server.py` seam is load-bearing. It lets the environment's determinism be
proven without a transport, and it is what will later let a trace attribute a failure to the
model rather than to MCP.

`SPEC.md` §8 places this inside the installed package rather than a top-level `servers/`
directory, precisely so the deterministic logic stays directly importable and testable without
MCP transport while `server.py` remains a thin real-protocol adapter.

## Determinism

Every tool is a pure function of its arguments over immutable fixture data: no clock, no
randomness, no network, no mutable state. Identical arguments always produce identical results.

- Multi-result operations are ordered by identifier. `search_customers` performs case-insensitive
  substring matching and applies **no relevance ranking** - ranking would introduce a hidden
  variable into an environment that must be fully controlled.
- A miss returns a structured `found: false` result, never an exception, so a legitimate
  "not found" stays distinguishable from a transport or protocol failure.

## Fixture design

Twelve records for each of customers, orders, invoices, products, and employees, with referential
integrity enforced at load time (`_check_integrity`).

**Values are deliberately not derivable from their identifiers.** `C102` does not map to
`customer102@example.test`; email formats vary between records so no single rule reconstructs
one. If an answer could be inferred from the key alone, a task built on this data would measure
guessing rather than tool use. All data is synthetic, uses `example.test` addresses, and
describes no real person.

Customer names and email addresses are unique, which is what makes `find_customer` and
`lookup_customer` deterministic single-result lookups. The integrity check enforces this.

## Tool-spaces

| Tool-space | Tools |
|---|---|
| `customer_baseline_v1` | `get_customer`, `get_order`, `get_invoice`, `get_product`, `get_employee` |
| `customer_overlap_v1` | the baseline five, plus `find_customer`, `search_customers`, `get_customer_details`, `lookup_customer`, `customer_information` |

Selection happens **server-side at launch**, so the real `tools/list` response differs between
conditions. The model observes the manipulated variable through the protocol itself rather than
through harness-side filtering.

## Intended semantic overlap

Recorded here, before any model experiment is run, as required by `SPEC.md` §10.

| Tool | Overlaps | Nature of the overlap |
|---|---|---|
| `get_customer_details` | `get_customer` | Same argument; returns a strict superset of the same stored record. |
| `customer_information` | `get_customer` | Near-pure alias: same argument, same data, different name and phrasing. |
| `find_customer` | `get_customer` | Same intent, different key: full name instead of customer ID. |
| `lookup_customer` | `get_customer` | Same intent, different key: email instead of customer ID. |
| `search_customers` | `get_customer` | Same intent, unstructured query, returns zero or more results. |

Two design rules constrain these, and both matter for the validity of anything measured later:

1. **The overlapping tools are genuinely functional and internally consistent with the baseline
   tools.** They read the same stored records, so choosing an overlapping tool never returns
   data that contradicts `get_customer`. They were *not* made to return wrong or partial data
   in order to manufacture task failure. A wrong tool choice therefore does not automatically
   produce a wrong answer - which is what allows tool-selection accuracy and answer correctness
   to be measured independently, as `SPEC.md` §9.3 requires.

2. **Descriptions are neutral API prose, fixed before any run.** They are controlled
   experimental material, defined in exactly one place (`toolspaces.py`) and pinned by a
   snapshot test so an accidental edit shows up as a reviewable diff rather than a silent change
   to a control.

`ToolDefinition.overlap_note` carries this intent in code. It is internal experimental metadata
and is **never exposed over MCP** - the model cannot see how the environment was designed. The
same rule applies to docstrings on `models.py` records, which *are* serialized into the MCP
output schema: they stay neutral API prose, and rationale lives in comments.

One asymmetry is inherent rather than engineered: `find_customer` and `lookup_customer` key on
name and email, so using them for a customer-ID task requires an argument the caller does not
have. That is a genuine failure mode of overlapping APIs, not a trap built into the fixture.

## Running

```bash
python -m agent_lab.synthetic.server --tool-space customer_overlap_v1
```

Nothing may be written to stdout: under stdio, stdout carries the protocol.
