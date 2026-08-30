# Observations

A first-class research artifact. Record surprising agent behaviour **before** attempting to
explain, fix, or tune it away (`AGENTS.md` s5). Unexplained behaviour is data.

Format (`SPEC.md` s17):

```markdown
## YYYY-MM-DD - Observation O-XXX

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

Observations about the **apparatus** are recorded here too, and are labelled as such. They are
not research findings: an instrument defect found before any model ran tells us about the
instrument, not about agent behaviour.

---

## 2026-08-30 - Observation O-001 (apparatus, not a research result)

**Classification:** Methodological / apparatus. Milestone 1. **No model was involved and no
experiment had been run**, so this is not evidence about agent behaviour and carries no novelty
claim. It is a defect found in the instrument and corrected before first use.

### Observation

The model-visible capability surface of an MCP environment is considerably larger than the tool
names and descriptions an author writes deliberately. While building the synthetic environment,
research-design language was found in two places that are transmitted to the model but are easy
to treat as internal implementation detail:

1. **Pydantic model docstrings are serialized into the MCP `outputSchema`.** Docstrings written
   as internal notes therefore reach the model. Two carried explicit experimental framing - one
   described a record as "A realistic superset of `Customer` - the same core data, never
   contradicting it", language that describes the *experimental design* of the overlap condition
   rather than the API.
2. **Server identity is returned in the MCP initialize result.** The server was initially named
   `agent-lab-synthetic`, which announces to any model that can see it that the environment is
   synthetic laboratory apparatus.

Generated schema *titles* (`"Customer Id"`, `"get_customerArguments"`) are also model-visible and
derive from Python identifiers rather than from anything deliberately authored.

### Conditions

Found by inspecting the full `initialize` and `tools/list` payloads of the synthetic MCP server
directly, rather than by reading the source. Nothing else about the environment changed.

### Unexpected detail

The leakage path was *generation*, not authorship. No one wrote experimental framing into a tool
description; it arrived in the model-visible surface as a by-product of pydantic schema
generation from ordinary Python docstrings, and of the SDK reporting server identity. The
surface an author reviews in code is not the surface the model receives.

### Why it matters

Both leaks are plausible confounds for the effect Phase 0 is meant to measure. Text describing
the relationship between an overlapping tool and a baseline tool could inform the very tool
choice under study, and a model that can infer it is inside an evaluation may not behave as it
would in deployment. Either could have produced a calibration result that looked clean and was
not.

### Candidate explanations

Not applicable - this is a defect in apparatus construction with a known cause, not a behaviour
requiring explanation.

### Resolution

Both were corrected **before any model experiment was run**. Docstrings on exposed models were
rewritten as neutral API prose with rationale moved to comments; the server was renamed to a
neutral, domain-plausible `customer-directory`. Tests now assert that a defined research-design
vocabulary appears nowhere in the tool surface, server identity, or server instructions, and
that internal condition identifiers (`customer_baseline_v1`, `customer_overlap_v1`) are never
exposed over MCP. The model-visible surface is additionally pinned by committed snapshots.

### Follow-up

The generalisation is now a standing rule (`SPEC.md` s6.13, `AGENTS.md` s10): **every string and
schema field that reaches a model is experimental material**, including generated metadata.

Milestones 3 and 4 must re-audit this at the *provider* boundary. A provider adapter re-serializes
the MCP surface into its own tool format, and may add its own titles, wrappers, or descriptions,
so the surface actually sent to the model must be captured in the raw trace and audited there -
verifying it at the MCP boundary alone is not sufficient.
