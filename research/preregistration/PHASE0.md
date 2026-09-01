# Phase 0 Calibration — Pre-Registration

**Status:** frozen design, **not yet executed**. No Phase 0 model result has been observed.
**Binds:** `experiments/phase0_calibration/` · **Spec:** `SPEC.md` v2.5 §16, §14.1
**Written:** 2026-09-01

This document is the binding design record. It is committed **before** any Phase 0 provider call.
The execution records `source_commit_sha` and `source_tree_dirty` in every trace and result row,
so the claim "this design preceded these results" is verifiable rather than asserted. The Phase 0
run must be executed from a **clean committed tree**.

---

## 1. Purpose and status

**Calibration / positive control. Explicitly not a novel research contribution.**

Question: *can this lab reliably detect a change in first-call tool routing when five semantically
overlapping customer tools are added to an otherwise stable five-tool capability surface?*

Per `SPEC.md` §16 calibration succeeds if the experiment is valid and controlled, model/tool
interactions are fully inspectable, the evaluator correctly distinguishes outcomes, the condition
comparison is reproducible, and any outcome can be explained from preserved evidence.
**A null result is an acceptable calibration outcome.** No particular regression magnitude is
required, and none is predicted here.

## 2. Generalization claim

> Within this frozen environment and model configuration, adding five semantically overlapping
> customer tools changes first-call routing accuracy on **a frozen sample of 20 customer-ID
> lookup prompts** by the reported mean paired difference.

**Not claimed:** generalization to agent tasks broadly, to other task types, to other tool
families, to other models, or to non-lookup routing. The 20 direct-exposure tasks share one
routing archetype — `get_customer(customer_id=…)` — varied across record, field, and phrasing
register. That homogeneity is **forced by the paired design**: a task keyed on name or email
would make an overlap-only tool correct and be unanswerable in baseline.

## 3. Strata (declared before results)

| Stratum | n | Content | Role |
|---|---|---|---|
| `direct` | 20 | customer-ID lookups | **Headline.** Directly targeted: overlap adds five competing customer tools |
| `non_target` | 8 | 2 order · 2 invoice · 2 product · 2 employee | **Separate, descriptive.** Expected tool gains no new direct competitor; only the tool list grows |

The `non_target` stratum is **not a true negative control** — its tool environment changes too, so
tool-space growth alone could affect it. It is a coarse spillover indicator, and at n=8 it cannot
resolve small effects. **The two strata are never pooled** (`SPEC.md` §16, v2.5).

## 4. Frozen material

| Artifact | Value |
|---|---|
| Task set | `phase0_calibration_tasks_v1`, 28 tasks |
| **Task-set fingerprint** | `fp1:sha256:bb105a8015d08801366fc4c8f31d49a8c63df2efe0f67bffa961909586ea69ae` |
| **Config fingerprint** | `fp1:sha256:efde09cff4d6a93c7249c2816a54e57db0774a5bdae4b86d3a1787aac39d264c` |
| Metric set | `phase0_single_tool_v1` |
| **Metric fingerprint** | `fp1:sha256:c5d692554380670053ee2e18670eb3df549b81bb6ca8ac1eccd174390a7813ae` |

Fixture content (expanded to 20 customers **before** freezing, per `SPEC.md` §16 v2.5; immutable
for this execution thereafter):

| Fixture | Records | sha256 |
|---|---|---|
| customers.json | 20 | `43c46968bcdece2f16263c047516738cd2e0e3036cdab79e08041fc13d1cc82b` |
| orders.json | 12 | `88a0c6d711df1572e757e1585e053a0894de53e0470ee6d5daf2d1e50e682435` |
| invoices.json | 12 | `a38a7f745909920505c6b4cc00e872bfb84611106b7c9765b831209bd37f924b` |
| products.json | 12 | `f89d05cafbb87b55f345b03998602c3376bef24a077d045380d3a89ac87d0a00` |
| employees.json | 12 | `87ba706e182dda8873a3f9d18753e047cbd8ed02661a24853a92e00f5b7f733e` |

28 distinct fixture records, **zero record reuse**. Reusing a record across tasks would be
pseudo-replication: the same routing decision counted twice.

## 5. Conditions and surfaces

| | `customer_baseline_v1` | `customer_overlap_v1` |
|---|---|---|
| Tools | 5 | 10 |
| environment_fingerprint | `fp1:sha256:0f1a88a9…1796980c` | `fp1:sha256:d80a3f1a…3196e763` |
| model_surface_fingerprint | `fp1:sha256:fa5dc03c…50af6b6c` | `fp1:sha256:7a462242…7f776eab` |
| provider_surface_fingerprint | `fp1:sha256:9ebd86be…1ddb53f2` | `fp1:sha256:369e7734…c8b89ad1` |

Overlap adds `find_customer`, `search_customers`, `get_customer_details`, `lookup_customer`,
`customer_information`. **The tool-space is the only intended manipulated variable.** Held
constant: model, model parameters, system instructions, tasks, fixture data, evaluator and metric
definitions, MCP transport, retry policy, provider-adapter behaviour, and all other model-visible
content.

No research-design language reaches the model: leakage at the persisted provider request is
audited by existing tests, and internal condition identifiers never appear there.

## 6. Metrics

**Primary (claim-bearing):** `first_call_routing_correct` — the first substantive tool call is the
expected tool **and** carries exactly the expected identifying arguments after canonicalisation.
Substantive includes calls to absent tools and calls with invalid arguments.

**Secondary (diagnostic only):** `first_tool_correct`, `first_tool_arguments_correct`,
`expected_tool_used`, `expected_tool_used_correctly`, `tool_recovery_success` (null when no
recovery was required), `incorrect_tool_call_count`, `unnecessary_tool_call_count`,
`tool_call_count`, `task_success`.

Secondary metrics **do not carry the claim**. Promoting one after results are observed requires a
new metric definition set/version and must be labelled a new analysis.

Answer evaluation uses `contains_facts` (25 tasks) and `typed_scalar` (3). **`exact_match` is
deliberately unused**: M3 showed a conversational model answers in prose, so it would reject
correct answers and inject matcher artifacts into `task_success`.

## 7. Unit of generalization and aggregation

**The task is the unit of generalization. Repetitions are within-task replicates.**

1. Per run: primary metric is 0/1.
2. Per task per condition: rate = correct runs ÷ valid runs, over 5 repetitions.
3. Per task: paired difference `d = rate_overlap − rate_baseline`.
4. Headline: **mean paired difference across the 20 `direct` tasks**, with all 20 shown.

Repeated runs of one task are **never** counted as additional independent task observations.

## 8. Design parameters

| | |
|---|---|
| Tasks | 28 (20 direct + 8 non_target) |
| Conditions | 2 |
| **Repetitions** | **5** |
| **Runs** | **280** |
| Expected provider requests | ~600 |
| **Provider-request ceiling** | **1120** |

The ceiling is `28 × 2 × 5 × 4` — every trajectory valid under the experiment's own `max_steps: 4`
must be permitted (`SPEC.md` §14.1, v2.5). **It bounds request count, not spend**; see §14 for why
dollar exposure is not bounded by it.

## 9. Execution order

Execution order is experimental design. Running all baseline observations before all overlap
observations would confound condition with time, provider state, and a mutable model alias.

**Deterministic pair-adjacent counterbalanced schedule.** For repetition `r` and frozen task index
`i`: `(baseline, overlap)` when `(i + r) % 2 == 0`, otherwise `(overlap, baseline)`. The two
conditions of a task/repetition run **adjacently**; within-pair order alternates so neither
condition is systematically first.

**No RNG and therefore no seed** — the schedule is a pure function of the frozen task order and
repetition count, reconstructible without persisting randomness. The realized schedule is
persisted anyway: in full in `manifest.json`, and as `schedule_index` in each run's `RUN_STARTED`
event, derived into the normalized row. The schedule is not changed after observing results.

## 10. Practical-effect threshold

**0.10 absolute mean paired difference** in first-call routing rate is the smallest effect
considered practically meaningful for this calibration.

Chosen because it is ten times the 0.01 quantisation floor (one flipped repetition on one of 20
tasks moves the mean by 1/(5×20)), so it cannot be an artifact of granularity, and because a
ten-percentage-point routing change is the scale at which tool-design advice would change.

It is **not** an MDE, **not** a power estimate, **not** a significance threshold, and **not** a
requirement for Phase 0 to succeed. It is an instrument-sensitivity statement.

**No defensible prospective power/MDE calculation is possible**: no variability estimate for
per-task routing rates exists under either condition, and precision will not be invented
(`SPEC.md` §14.1). **Post-hoc/observed power will not be computed or reported.**

## 11. Uncertainty and reporting

**Paired/cluster bootstrap over tasks** — 10,000 resamples, **seed `20260901`**, resampling
*tasks* so each task's repetitions stay clustered. Percentile 95% interval on the mean paired
difference. The seed exists for reproducibility and carries no inferential meaning.

**Descriptive robustness:** counts of tasks regressed / unchanged / improved, plus the full
per-task difference table and one comparison chart.

**No permutation or significance test is pre-registered.** A p-value would only invite defining
calibration success by significance, which `SPEC.md` §16 rejects.

The `non_target` stratum receives the same per-task computation, reported **separately and
descriptively**, never pooled into the headline.

## 12. Operational validity — whole-execution rule

Valid model outcomes (`answered`, `no_answer`, `max_steps`) are **valid observations and are never
replaced**, however inconvenient.

If **any** run fails for a provider reason (authentication, billing, rate limit, outage,
connection, transport — recorded as `provider_error_kind` with `stop_reason: provider_error`):

1. the **entire physical execution** is marked operationally incomplete;
2. that execution and all traces are retained as apparatus evidence;
3. none of its runs is combined with a later execution for the headline;
4. **nothing reruns automatically**;
5. a replacement execution requires the operational cause resolved, **fresh researcher
   authorization for paid execution**, the exact same frozen experiment, and a new `execution_id`;
6. repeated operational failure goes to researcher review.

The analysis script **refuses** to produce a headline from an operationally incomplete execution
rather than silently dropping failed rows. This preserves a complete balanced 5/5 design and
avoids mixing unequal repetition counts.

## 13. Model and controls

`claude-opus-5` · `thinking: {type: adaptive}` · `output_config: {effort: high}` ·
`max_tokens: 4096` · **no `temperature`** (unsupported on current Claude models and rejected by
the API) · SDK retries **0** · `max_steps: 4` · real stdio MCP · `--allow-paid` required per
invocation.

**Limitation:** `claude-opus-5` is a **mutable alias, not an immutable model snapshot**. Every row
records `model_snapshot_available: false` alongside the `response.model` the provider returned.
Reproducibility is claimed no more strongly than the API permits.

**Noted from Observation O-004:** adaptive thinking returned zero thinking tokens on trivial
lookups in M3. The thinking control is declared and recorded but may be effectively inert for
tasks of this shape. This is stated rather than assumed.

## 14. Cost

| | |
|---|---|
| **Expected spend** | **~$5**, from M3 empirical token usage (~600 requests) |
| **Conservative planning spend** | **~$6.50** per normal execution |
| **Researcher planning allowance** | **~$13**, if one separately approved replacement execution is required |
| **High-trajectory estimate** | **~$10–11** for an execution where every run uses all four turns, *assuming response and token sizes stay in the M3-like range* |
| **Hard request-count ceiling** | **1120 requests** |
| **True worst-case dollar exposure** | **Not bounded by request count.** See below. |

**The request ceiling is not a spend ceiling.** `max_provider_requests: 1120` bounds how many
provider calls may be made; it says nothing about how many tokens each call carries. Two things
make dollar exposure variable:

- **Input** grows with conversation length, so later turns cost more than earlier ones.
- **Output** is capped per response only by `max_tokens: 4096`. The M3-derived planning figures
  assume ~60–150 output tokens per response, which is what a concise lookup answer actually
  produced. A pathological or degenerate response could use far more, up to that cap.

The `~$10–11` figure above is therefore a **high-trajectory planning estimate, not a maximum**:
it holds only while token sizes resemble M3's. Arithmetically, output alone could reach
`1120 × 4096 ≈ 4.6M` tokens — roughly an order of magnitude more output volume than the
high-trajectory estimate assumes — and input volume has no comparable fixed bound.

**No single precise theoretical dollar maximum is quoted here**, because none can be derived
honestly from the declared controls: request count is bounded, token volume per request is not
bounded tightly enough to yield a meaningful figure. The operative protections are the request
ceiling, the per-invocation `--allow-paid` authorization, and the researcher reviewing actual
usage from the persisted evidence after the run.

## 15. A/A omission

No A/A arm. The 5 within-condition repetitions already characterise model stochasticity at the
task level, so an A/A arm would largely re-measure it at additional cost, a third condition, and
code changes. Its unique contribution — detecting label-induced differences between nominally
identical arms — is obtained for free: the leakage audit proves condition identifiers never reach
the provider, and an alias tool-space's model-surface and provider-surface fingerprints would
provably equal baseline's.

## 16. Limitations

- One routing archetype; the claim is about customer-ID lookup prompts, not agent tasks generally.
- One model, one provider, one environment version, one system prompt.
- `non_target` at n=8 is a coarse spillover indicator only.
- Model identity is a mutable alias.
- Adaptive thinking may be inert at this task difficulty.
- Synthetic fixtures; no external validity claim about real customer systems.

## 17. Mandatory stop

After Phase 0: **STOP.** Do not build a matrix of tool-count, naming, description, schema,
ordering, or multi-model experiments. Record the result, inspect the traces, record observations,
and **invoke the novelty gate** (`SPEC.md` §3) before selecting the first frontier research
question. Phase 0 is not the contribution.

---

*No results appear in this document. Results belong in `research/experiment-log.md` and
`research/observations.md` after execution.*
