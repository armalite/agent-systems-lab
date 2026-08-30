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

## 2026-08-30 - Observation O-004 (apparatus, not a research result)

**Classification:** Methodological / apparatus. Milestone 3, first live provider execution
(3 tasks, `claude-opus-5`, harness check). **Not a research result**: three tasks against a
scripted-simple environment say nothing about agent behaviour, and this was an instrument check.

### Observation

Two behaviours of the real provider differed from the offline doubles used to build the adapter:

1. **A text preamble accompanies the tool call.** In two of three tasks the first assistant turn
   returned `["text", "tool_use"]` - a short preamble ("I'll look that up for you.") in the same
   turn as the tool call. The offline doubles had only ever produced `["tool_use"]` or
   `["thinking", "tool_use"]`, so this shape was untested.
2. **Adaptive thinking produced zero thinking tokens.** With `thinking: {type: adaptive}` and
   `effort: high` declared, `output_tokens_details.thinking_tokens` was `0` on all six turns and
   no thinking block was returned. The model judged these single-lookup tasks not to warrant it.

The provider also returned a richer `usage` object than the doubles: `cache_creation`,
`inference_geo`, `output_tokens_details`, `server_tool_use`, and `service_tier` alongside the
token counts.

### Conditions

First live run of `smoke_anthropic_001`, immediately after a prior execution of the identical
config (same config fingerprint) was rejected for insufficient account credit.

### Unexpected detail

The preamble case is the interesting one. It was handled correctly by accident of good design
rather than by explicit intent: the runner ends a run only on a turn with **no** tool calls, so
the preamble was preserved as model output, replayed verbatim, and never mistaken for the final
answer. Had the runner instead treated "any text" as an answer, two of three tasks would have
been scored against "I'll look that up for you." and the smoke test would have failed for a
reason that had nothing to do with routing.

The thinking result is a reminder that a *declared* control is not an *exercised* one. Thinking
mode is recorded in the provider surface and its fingerprint, but the verbatim thinking-block
replay path - the reason `provider_blocks` exists at all - was **not** exercised live, only
offline. That gap should not be described as validated.

### Resolution

Added a regression test pinning the `["text", "tool_use"]` turn shape: the preamble is captured
and replayed, and it never becomes the final answer. No production code changed - the behaviour
was already correct; only the evidence for it was missing.

The richer `usage` object needed no change: it is preserved verbatim in the trace, which is what
"do not normalize away provider-specific information" is for.

### Follow-up

Before any experiment where thinking is a manipulated or relied-upon variable, verify thinking
blocks are actually returned for those tasks - on trivial lookups they are not. If Phase 0 tasks
stay this simple, the thinking control will be declared and recorded but effectively inert, and
that must be stated rather than assumed.

---

## 2026-08-30 - Observation O-003 (apparatus, not a research result)

**Classification:** Methodological / apparatus. Milestone 3. **No model was involved**; found
while building the provider adapter offline. Not a research result.

### Observation

The canonical model surface and the provider-facing surface are **not** semantically equivalent,
and the difference is not cosmetic. An Anthropic tool definition carries exactly `name`,
`description`, and `input_schema`. Our canonical `ModelSurface` also carries `title`,
`output_schema`, and `annotations` for every tool - and the output schemas are the largest part
of the MCP surface, since they describe the full result envelope.

So a model reached through the Anthropic Messages API sees a **materially narrower** capability
surface than the same environment presents over MCP. Nothing warns you about this: the tools
render successfully, the request is valid, and the loss is silent.

### Conditions

Found by comparing the canonical surface against the rendered Anthropic request body, offline,
with no API call.

### Unexpected detail

Milestones 1 and 2 established the habit of asking "what does the model see?" at the MCP
boundary. The answer changes again at the provider boundary, and in this case it changes by
*subtraction* performed by the provider's schema rather than by anything the harness authored.
O-001 was generated content leaking in; O-002 was a harness identifier leaking in; O-003 is
declared content silently dropping out. All three are the same lesson from different directions:
**the surface you can read in your own source is never the surface the model receives.**

### Why it matters

Two consequences for Phase 0. First, a fingerprint over the canonical model surface would not
detect a change confined to the provider transformation, so the two must be fingerprinted
separately - which `SPEC.md` v2.3 now requires. Second, if a later experiment manipulates output
schemas, that manipulation would be **invisible** to a Claude subject reached this way, and any
null result would be an artifact of the transport rather than a finding about the model.

### Resolution

Three surfaces are now persisted and fingerprinted independently - environment descriptor,
canonical model surface, provider surface - plus the exact full provider request body for every
turn as evidence. The `PROVIDER_SURFACE_PREPARED` trace event records the dropped fields
explicitly (`title`, `output_schema`, `annotations`) so the loss is visible in the evidence
rather than only in the code. A test asserts the model-surface and provider-surface fingerprints
differ.

### Follow-up

Before any experiment that treats output schemas or tool annotations as a manipulated variable,
confirm the variable actually survives to the model on the provider being used. For the Anthropic
Messages API today, it does not.

---

## 2026-08-30 - Observation O-002 (apparatus, not a research result)

**Classification:** Methodological / apparatus. Milestone 2. **No model was involved and no
experiment had been run.** A second instance of the O-001 failure mode, found at a different
boundary.

### Observation

Building the harness surfaced a third channel through which experimental design reaches the
model: **tool-call identifiers echoed back in the conversation**. The scripted adapter initially
minted call ids of the form `{task_id}-{tool_space_id}-{turn}-{index}`. Those ids are returned
to the model inside the assistant turn and the following tool result, so every request after the
first tool call contained the string `customer_overlap_v1` or `customer_baseline_v1` - the
condition label, i.e. the manipulated variable, named directly in model-visible context.

It was caught by an audit that reads the **persisted trace** rather than the source: the check
that no condition identifier appears in a `MODEL_REQUEST` payload.

### Conditions

Found while extending the O-001 leakage audit from the MCP boundary to the adapter boundary.
Nothing else changed.

### Unexpected detail

O-001's leaks came from schema generation and server identity - metadata. This one came from an
**identifier the harness itself invented**, and it entered model-visible context by being echoed
back through conversation history rather than by being declared anywhere. Both the tool
definitions and the system prompt were clean; the leak lived in the transcript.

The generalisation is sharper than O-001's: it is not only *authored* and *generated* content
that must be audited, but anything the harness synthesises that ends up in the message history.
Real provider APIs echo tool-use ids the same way, so this is not an artifact of the fake
adapter.

### Why it matters

The leaked string is the condition label. A model able to read it could in principle condition
its behaviour on which experimental arm it is in - the most direct confound available for the
Phase 0 comparison.

### Resolution

Call ids are now opaque and position-derived (`call_{turn}_{index}`): unique within a run,
deterministic, and carrying no task or condition information. The task/condition-qualified string
is retained as `provider_request_id`, which is recorded as provider metadata and never enters the
conversation. A test asserts that no condition identifier appears in any `MODEL_REQUEST` payload
- system instructions, rendered tools, or messages.

### Follow-up

Milestone 3 must repeat this audit against the real provider-facing request, since an adapter may
introduce identifiers, wrappers, or cache keys of its own. The standing rule is now: **audit the
recorded request, not the code that builds it.**

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
