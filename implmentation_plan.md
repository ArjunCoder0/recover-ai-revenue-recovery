# RECOVER — Implementation Blueprint (Source of Truth for the AI Coding IDE)

---

## SECTION A — Project understanding

**What we are building:** a local, single-process Python application that demonstrates a *policy-bounded learning controller* for failed-payment recovery. It ingests simulated failed payments, classifies each failure, computes the set of actions a deterministic policy engine permits, lets a Thompson-Sampling bandit choose the highest-expected-value permitted action, executes it inside a bounded event-driven workflow against a simulated world, observes the outcome, updates the bandit, writes an append-only audit entry with a full rationale, and presents everything in a Streamlit revenue-operations console alongside a naive-baseline benchmark and a multi-seed confidence check.

**What we are not building:** an LLM agent, a real payment integration, a distributed system, or a general ML platform.

**The claim being demonstrated to the judge:** *"Recovery decisions can be adaptive AND provably safe at the same time, and every decision can be explained and audited."* The numbers are simulation evidence; the architecture is the product.

**Hard invariants (must hold in code, tests, UI, README):**
1. The learning layer can only choose from actions the policy layer allowed.
2. The decision path (`policy.py`, `decide.py`) never reads `hidden_recovery_prob` or `case.responsiveness`.
3. The LLM (if any) only rewrites an already-approved message and never influences which action is taken.
4. The application runs completely without any API key or network access.
5. Same seed → identical results.
6. Every executed or terminal decision produces exactly one audit entry.
7. The workflow terminates for every case (proof in Section I).

---

## SECTION B — Requirements extracted from the research/report

From the competitive analysis and the one-day plan, the following requirements were carried forward and are binding:

| # | Requirement | Source in research | Where satisfied |
|---|---|---|---|
| B1 | Track 3 is the least saturated in open source; no AI-native recovery product exists; differentiate on *bounded workflow + measurement*, not ML novelty | Research §3, §7 | Whole design |
| B2 | Decline-code-aware taxonomy (soft / transient / action-required / hard) modeled on issuer decline reasons and Hyperswitch/Kill Bill retry logic | Research 3.1, 3.2 | Section F |
| B3 | Network reattempt rule: hard declines never retried; UPI Autopay pre-debit notification constraint (India-specific white space W2) | Research W1, W2 | Section G rules R1, R4 |
| B4 | Deterministic policy engine with table-driven unit tests | Research §7 MVP | Section G, R |
| B5 | Learning via bandit, not LLM; explicit per-decision rationale | Research §7, §10 | Section H |
| B6 | Bounded, resumable-style workflow (max attempts, cool-downs, contact caps, quiet hours, window, escalation) | Research §7 | Section I |
| B7 | Baseline vs policy comparison with ₹ recovered, fees, contacts, violations; multi-seed confidence (honest "mean ± SD") | Research §7 standout features | Section K |
| B8 | Human-in-the-loop for high-value cases | Research §7 | Section M |
| B9 | LLM outreach optional, guardrailed, template fallback; "kill the key" degradation story | Research §7 | Section L |
| B10 | No-key default mode ranked "MUCH higher" by the user's own rubric | Research §0, §10 brutal truth 2 | Section S, T |
| B11 | Honest disclosure that outcomes are simulated; simulator parameterized, seeded, separate | Research §10 truth 4 | Section J, AD |
| B12 | Reviewer will "change an input and watch the output change" → merchant controls must actually change results | Research §4 item 10 | Section N.8 |
| B13 | Decision-visibility UI pattern (routing/guardrail visualization) from openai-cs-agents-demo | Research T5 notes | Section N.3, N.4 |

---

## SECTION C — Core product concept

**One sentence:** Recover turns each failed payment into a diagnosed case, fences the legal actions with deterministic rules, lets a bandit pick the most valuable legal action, executes it inside a bounded workflow, learns from the result, and proves the economics against a naive retry schedule.

**Layered principle:**

```
LAYER A  SAFETY      policy.py     "Which actions are allowed?"      deterministic, tested, merchant-configurable
LAYER B  INTELLIGENCE decide.py    "Which allowed action is best?"   probabilistic, learns online, explainable
LAYER C  EXECUTION   engine.py     "Do it, in order, bounded"        event queue, scheduling, audit
LAYER D  WORLD       simulator.py  "What actually happens?"          hidden ground truth, seeded
LAYER E  EVIDENCE    metrics.py    "Was it worth it?"                baseline, by-class, multi-seed
LAYER F  VOICE       outreach.py   "How do we word the message?"     template first, LLM optional + guardrails
LAYER G  CONSOLE     app.py        "Show me and let me act"          Streamlit, 8 sections
```

Layer B may *see* Layer A's rejections (for explainability) but may only *select* from Layer A's approvals. Layer B and A never see Layer D's internals.

---

## SECTION D — Architecture

### D.1 Module dependency graph (acyclic — enforce this)

```
simulator.py   ← (stdlib only)
policy.py      ← simulator.day_of_month        (for salary-day scheduling rule)
decide.py      ← policy
engine.py      ← simulator, policy, decide
metrics.py     ← simulator, engine
outreach.py    ← (stdlib; google.generativeai imported lazily inside try)
app.py         ← all of the above + streamlit, pandas
tests/*        ← recover.*
```

`policy.py` must NOT import `decide` or `engine`. `simulator.py` must NOT import anything from `recover`.

### D.2 File responsibilities

| File | Responsibility | Must NOT contain |
|---|---|---|
| `recover/simulator.py` | `Case` dataclass, failure-code taxonomy table (`CODES`), `generate`, `day_of_month`, `hidden_recovery_prob` | any decision logic, any policy constants |
| `recover/policy.py` | action arms, costs, delays, default controls, `validate_controls`, `allowed_actions`, `is_quiet`, `defer_quiet`, `salary_delay`, `check_violations` | randomness, bandit, LLM |
| `recover/decide.py` | `Bandit` (Beta-Thompson), `PRIORS`, `decide`, `explain_rationale` | scheduling, outcome simulation, `hidden_recovery_prob`, `responsiveness` |
| `recover/engine.py` | `run` (event loop), `execute_human_action` (HITL), re-exports `salary_delay`, `defer_quiet` | UI code, metrics |
| `recover/metrics.py` | `summarize`, `by_class`, `confidence` | UI code |
| `recover/outreach.py` | `TEMPLATES`, `draft`, `validate_rewrite`, `_llm_rewrite` | decision logic |
| `app.py` | Streamlit console: state, navigation, 8 sections, CSS | business rules (must call into `recover.*`) |
| `tests/` | pytest suites per module + boundary test | — |

### D.3 Runtime model

Single Python process. All state lives in memory (`st.session_state`) for the session. No database. No threads. No network unless the user explicitly enables LLM rewrite and a key exists.

### D.4 Time model

Simulation time is an **integer hour** counted from `t = 0` = day 1, 00:00. Hour-of-day = `hour % 24`. Day-of-month = `(hour // 24) % 28 + 1` (28-day month for simplicity). Failures occur in `[0, 120)` (first 5 days). All scheduling arithmetic is integer.

---

## SECTION E — Data model

### E.1 `Case` (dataclass in `simulator.py`)

| Field | Type | Set by | Visible to decision layer? | Meaning |
|---|---|---|---|---|
| `id` | `int` | generate | yes | Unique index 0..n-1 |
| `method` | `str` | generate | yes | `"card"` \| `"upi_autopay"` \| `"netbanking"` |
| `amount` | `float` | generate | yes | Amount at risk in ₹, 2 decimals |
| `error_code` | `str` | generate | yes | One of 10 codes (Section F) |
| `failed_at` | `int` | generate | yes | Simulation hour of the original failure |
| `salary_day` | `int` (1..28) | generate | **yes, as an observable estimate** — see E.2 | Customer's expected income day |
| `responsiveness` | `float` (0..1) | generate | **NO — hidden** | Customer's latent propensity to react to messages/links |
| `state` | `str` | engine | yes | `OPEN` \| `RECOVERED` \| `EXHAUSTED` \| `ESCALATED` |
| `retries` | `int` | engine | yes | Retry attempts executed so far |
| `messages` | `int` | engine | yes | Customer contacts executed so far (reminders + links) |
| `last_retry_at` | `int` | engine | yes | Hour of last executed retry; sentinel `-999` = never |
| `recovered_at` | `int` | engine | yes | Hour of recovery; `-1` if not recovered |
| `cost` | `float` | engine | yes | Cumulative action cost in ₹ |
| `history` | `list[dict]` | engine | yes | Ordered audit entries for this case (same schema as global audit) |

Derived property: `failure_class -> str` = `CODES[error_code]`.

### E.2 Decision on the hidden-variable boundary (binding)

The spec calls both `salary_day` and `responsiveness` "hidden simulation variables" but also requires a `RETRY_SALARY_DAY` action that must be scheduled *somehow*. Resolution:

- `responsiveness` is **strictly hidden**: only `hidden_recovery_prob` reads it. A boundary test greps `policy.py` and `decide.py` and `engine.py` for the token `responsiveness` and `hidden_recovery_prob` (engine may reference `hidden_recovery_prob` only inside the execution step; policy/decide may not reference either).
- `salary_day` is treated as a **merchant-observable estimate** (in production: inferred from prior successful debit dates or provided by the customer). Its *effect on recovery* remains hidden inside `hidden_recovery_prob`. The scheduler may read `case.salary_day` to compute the salary-day retry time. Document this in README ("Observable vs hidden").
- `hidden_recovery_prob` is called in exactly two places: `engine.run` (execution step) and `engine.execute_human_action`.

### E.3 Controls (dict, defaults in `policy.py`)

```
DEFAULT_CONTROLS = {
  "max_retries": 4,            # int 0..8
  "min_retry_gap_h": 2,        # int ≥ 1 (fixed in UI, shown)
  "contact_cap": 2,            # int 0..5
  "quiet_hours": (21, 9),      # (start_hour, end_hour), wrap-around allowed; fixed in UI, shown
  "recovery_window_days": 30,  # int 3..45
  "escalate_above": 2500,      # float ≥ 0
  "pre_debit_notice_h": 24,    # int ≥ 0 (fixed in UI, shown)
}
```

### E.4 Audit entry (dict) — single schema used for global audit and `case.history`

```
{
  "seq": int,                  # global monotonically increasing per run
  "kind": "action" | "terminal" | "human",
  "policy": "smart" | "naive",
  "decided_at": int,           # hour the decision was made
  "executed_at": int | None,   # hour the action executed (None for terminal)
  "case_id": int,
  "arm": str,                  # ARMS member
  "failure_class": str,
  "method": str,
  "amount": float,
  "success": bool | None,      # None for terminal
  "violation": int,            # len(violation_reasons)
  "violation_reasons": list[str],
  "deferred": bool,            # quiet-hour deferral applied
  "rationale": dict            # Section H.5 schema (naive: {"chosen":..., "note":"fixed schedule"})
}
```

### E.5 Rationale (dict) — Section H.5.

---

## SECTION F — Failure taxonomy

`CODES: dict[str, str]` in `simulator.py` (ordering is significant for weighted sampling):

| Error code | Class | Why this class exists / what it means for recovery |
|---|---|---|
| `INSUFFICIENT_FUNDS` | SOFT | Instrument valid, money absent now. Timing is everything (salary day). Blind immediate retry wastes fees. |
| `DO_NOT_HONOR` | SOFT | Generic issuer refusal; often temporary. Retry later or offer an alternate method. |
| `ISSUER_UNAVAILABLE` | TRANSIENT | Bank/system outage. Short-delay retry has high success once systems recover. |
| `UPI_TIMEOUT` | TRANSIENT | PSP/NPCI timeout. Same as above; UPI-Autopay-specific. |
| `EXPIRED_CARD` | ACTION_REQUIRED | Same instrument will keep failing; customer must update card or pay via another method. |
| `MANDATE_PAUSED` | ACTION_REQUIRED | Customer paused UPI Autopay mandate; presentment fails until they resume or pay manually. |
| `AUTH_TIMEOUT` | ACTION_REQUIRED | Customer didn't complete authentication (OTP/3DS/UPI PIN). Needs the customer, not a retry. |
| `MANDATE_REVOKED` | HARD | Customer revoked the mandate. Re-presentment is not permitted; only alternate-payment link or stop. |
| `CARD_LOST_STOLEN` | HARD | Network says do not reattempt. Retrying is a rule violation. |
| `RISK_DECLINE` | HARD | Issuer/risk system declined for risk; blind retries damage the merchant's standing. |

**Sampling weights** (same order): `[0.34, 0.12, 0.10, 0.08, 0.07, 0.06, 0.05, 0.06, 0.06, 0.06]` → ≈46% SOFT, 18% TRANSIENT, 18% ACTION_REQUIRED, 18% HARD.

**Class semantics used by policy and priors:**
- SOFT → retries permitted; timing matters.
- TRANSIENT → retries permitted; short delay preferred.
- ACTION_REQUIRED → retries permitted by rules but expected to be nearly useless; contact/link preferred. (We leave retries legal here so the bandit can *learn* they are useless — that is a visible learning demonstration.)
- HARD → retries **forbidden by policy**; only reminder/link/escalate/stop.

**Method-compatibility repair (in `generate`, deterministic, applied after sampling):**
| Sampled code | Incompatible method | Replacement |
|---|---|---|
| `MANDATE_PAUSED`, `MANDATE_REVOKED` | not `upi_autopay` | `INSUFFICIENT_FUNDS` |
| `EXPIRED_CARD`, `CARD_LOST_STOLEN` | not `card` | `DO_NOT_HONOR` |
| `UPI_TIMEOUT` | not `upi_autopay` | `ISSUER_UNAVAILABLE` |

All other codes are valid for all methods.

---

## SECTION G — Policy engine (`policy.py`)

### G.1 Constants

```
ARMS = ["RETRY_2H","RETRY_24H","RETRY_SALARY_DAY","SEND_REMINDER","PAYMENT_LINK","ESCALATE","STOP"]
RETRY_ARMS   = {"RETRY_2H","RETRY_24H","RETRY_SALARY_DAY"}
CONTACT_ARMS = {"SEND_REMINDER","PAYMENT_LINK"}
COST = {"RETRY_2H":3.0,"RETRY_24H":3.0,"RETRY_SALARY_DAY":3.0,"SEND_REMINDER":0.5,"PAYMENT_LINK":1.5,"ESCALATE":0.0,"STOP":0.0}
ACTION_DELAY_H = {"RETRY_2H":2,"RETRY_24H":24,"SEND_REMINDER":24,"PAYMENT_LINK":48}   # RETRY_SALARY_DAY is dynamic
MIN_SALARY_DELAY_H = 2
MIN_ATTEMPTS_BEFORE_ESCALATION = 1
DEFAULT_CONTROLS = {...}   # Section E.3
```

**Why costs matter:** the bandit maximizes `EV = p·amount − cost`. Without costs, a 2% retry on a ₹199 payment would still look "worth it" and the system would spam gateways. Costs make the controller stop when the expected recovery no longer covers the fee, which is exactly the economics a merchant cares about (net recovered, not gross).

### G.2 `validate_controls(controls) -> dict`
Returns a sanitized copy. Rules: ints coerced; `max_retries` clamped 0..8; `contact_cap` 0..5; `recovery_window_days` 1..60; `escalate_above ≥ 0`; `min_retry_gap_h ≥ 1`; `pre_debit_notice_h ≥ 0`; `quiet_hours` must be a 2-tuple of ints 0..23. Raises `ValueError` on non-numeric input. Merges missing keys from defaults.

### G.3 `allowed_actions(case, now, controls=DEFAULT_CONTROLS) -> dict[str, tuple[bool, str]]`

Pure, deterministic, no randomness, no I/O. Evaluate rules **in this order** per arm; the first failing rule provides the reason.

Preliminaries:
- `age_days = (now - case.failed_at) / 24`
- `earliest_delay(arm)`: `ACTION_DELAY_H[arm]` for fixed arms; `salary_delay(case, now)` for `RETRY_SALARY_DAY`; `0` for ESCALATE/STOP.
- `earliest_exec = now + earliest_delay(arm)`

| Rule | Applies to | Block condition | Reason string (exact) |
|---|---|---|---|
| R7 Window | all arms except STOP | `age_days > recovery_window_days` | `"recovery window of {d} days exceeded"` |
| R1 Hard decline | RETRY_ARMS | `case.failure_class == "HARD"` | `"network rule: never reattempt a hard decline ({error_code})"` |
| R3 Max retries | RETRY_ARMS | `case.retries >= max_retries` | `"max retries ({max_retries}) reached"` |
| R4 Min gap | RETRY_ARMS | `case.last_retry_at != -999 and earliest_exec - case.last_retry_at < min_retry_gap_h` | `"minimum gap of {g}h between retries not met"` |
| R2 UPI notice | RETRY_ARMS | `case.method == "upi_autopay" and earliest_delay(arm) < pre_debit_notice_h` | `"UPI Autopay: {h}h pre-debit notification required before re-presentment"` |
| R5 Contact cap | CONTACT_ARMS | `case.messages >= contact_cap` | `"customer contact cap ({cap}) reached"` |
| R6 Quiet hours | CONTACT_ARMS | **never blocks**; enforced by deferral (`defer_quiet`) at scheduling | reason `"ok"` |
| R8 Escalation | ESCALATE | `case.amount < escalate_above` → `"below escalation threshold (₹{escalate_above:,.0f})"`; else `len(case.history) < MIN_ATTEMPTS_BEFORE_ESCALATION` → `"no automated attempt made yet"` | |
| STOP | STOP | never blocked | `"ok"` |

Allowed arms get `(True, "ok")`.

**Pitfall to avoid (binding):** the min-gap rule must use `earliest_exec`, not `now`. After a retry executes at hour `t`, the case is re-queued at `t`; if the gap rule compared `now - last_retry_at` it would be 0 and block all retries forever after the first one. Using `now + delay - last_retry_at` fixes this.

**Note on R2:** with defaults, `RETRY_2H` is blocked for UPI Autopay (2 < 24); `RETRY_24H` allowed (24 ≥ 24); `RETRY_SALARY_DAY` blocked only if the computed salary delay is < 24h (e.g., salary day is today). This produces the visible "24h pre-debit notice" rationale in the Case Explorer.

### G.4 Scheduling helpers (defined here, re-exported by `engine.py`)

- `is_quiet(hour, quiet) -> bool`: `h = hour % 24`; if `start > end` (wrap): `h >= start or h < end`; else `start <= h < end`.
- `defer_quiet(hour, quiet) -> int`: if not quiet → `hour`; else advance to the next hour where `h == end`: wrap case: `h >= start` → `hour + (24 - h) + end`; `h < end` → `hour + (end - h)`; non-wrap case: `hour + (end - h)`.
- `salary_delay(case, now) -> int`: `days_ahead = (case.salary_day - day_of_month(now)) % 28`; `target = (now // 24 + days_ahead) * 24 + 10` (10:00 on that day); if `target <= now`: `target += 28 * 24`; return `max(MIN_SALARY_DELAY_H, target - now)`.

### G.5 `check_violations(case_before, arm, decided_at, executed_at, controls) -> list[str]`

Independent auditor applied to **every executed action of every policy** (smart and naive). It does not depend on `allowed_actions`, so a bug in the policy would be caught here rather than hidden. `case_before` is the case snapshot *before* counters are incremented.

| Check | Condition | Tag |
|---|---|---|
| retry on hard | arm ∈ RETRY_ARMS and class HARD | `retry_on_hard_decline` |
| retries exceeded | arm ∈ RETRY_ARMS and `case_before.retries >= max_retries` | `max_retries_exceeded` |
| min gap | arm ∈ RETRY_ARMS and `last_retry_at != -999` and `executed_at - last_retry_at < min_retry_gap_h` | `min_retry_gap` |
| UPI notice | arm ∈ RETRY_ARMS and method upi_autopay and `executed_at - decided_at < pre_debit_notice_h` | `upi_pre_debit_notice` |
| contact cap | arm ∈ CONTACT_ARMS and `case_before.messages >= contact_cap` | `contact_cap_exceeded` |
| quiet hours | arm ∈ CONTACT_ARMS and `is_quiet(executed_at, quiet_hours)` | `quiet_hours` |
| window | `(decided_at - failed_at)/24 > recovery_window_days` | `outside_recovery_window` |

`violation = len(reasons)`. Smart policy must yield 0 by construction — a test asserts this over several seeds.

---

## SECTION H — Thompson Sampling decision engine (`decide.py`)

### H.1 Model
For each `(failure_class, arm)` with `arm ∈ RETRY_ARMS ∪ CONTACT_ARMS`, maintain a Beta(α, β) belief over P(recover | class, arm). Thompson sampling: draw `p ~ Beta(α, β)` per arm per decision, act on the draw, update with the Bernoulli outcome.

### H.2 Informed priors (`PRIORS: dict[(class, arm), (α, β)]`)

```
SOFT:            RETRY_2H (1,8)  RETRY_24H (2,6)  RETRY_SALARY_DAY (5,3)  SEND_REMINDER (2,6)  PAYMENT_LINK (3,5)
TRANSIENT:       RETRY_2H (6,2)  RETRY_24H (5,3)  RETRY_SALARY_DAY (3,3)  SEND_REMINDER (2,6)  PAYMENT_LINK (3,4)
ACTION_REQUIRED: RETRY_2H (1,20) RETRY_24H (1,20) RETRY_SALARY_DAY (1,20) SEND_REMINDER (3,5)  PAYMENT_LINK (4,4)
HARD:            SEND_REMINDER (1,10)  PAYMENT_LINK (2,6)          (retries never legal → no prior needed)
DEFAULT for any missing pair: (1,3)
```
Priors encode domain knowledge but are deliberately weak (α+β ≤ 21) so the posterior moves visibly within a few hundred cases.

### H.3 `Bandit` class
- `__init__(self, seed: int)`: `self.rng = random.Random(seed)`, `self.post: dict = {}` (posterior overrides), `self.counts: dict[(class, arm), int] = {}` (number of updates), `self.seed`.
- `params(fc, arm) -> (α, β)`: `self.post.get(key, PRIORS.get(key, (1,3)))`.
- `sample(fc, arm) -> float`: `rng.betavariate(α, β)`.
- `mean(fc, arm) -> float`: `α/(α+β)`.
- `update(fc, arm, success: int)`: `success ∈ {0,1}`; `post[key] = (α + success, β + 1 − success)`; `counts[key] += 1`.
- `snapshot() -> list[dict]`: rows `{class, arm, prior_alpha, prior_beta, prior_mean, alpha, beta, posterior_mean, observations}` for all classes × learnable arms. Used by Decision Intelligence screen.

### H.4 `decide(case, now, bandit, controls) -> tuple[str, dict]`

```
allowed = allowed_actions(case, now, controls)
fc = case.failure_class
considered = []
for arm in ARMS excluding {ESCALATE, STOP}:
    ok, why = allowed[arm]
    if ok:  p = bandit.sample(fc, arm); ev = p * case.amount - COST[arm]
    else:   p = None; ev = None
    considered.append({arm, allowed: ok, reason: why, sampled_p: p, cost: COST[arm], ev, chosen: False})
viable = [c for c in considered if c.allowed and c.ev > 0]
if viable:            best = argmax ev; chosen = best.arm; fallback = None
elif allowed[ESCALATE][0]: chosen = "ESCALATE"; fallback_reason = "no allowed action with positive expected value; case qualifies for human review"
else:                 chosen = "STOP";     fallback_reason = "no allowed action with positive expected value; " + allowed[ESCALATE][1]
mark chosen in considered
return chosen, rationale
```
Ties in EV: first in `ARMS` order wins (deterministic).

**Invariant:** `chosen ∈ {a for a,(ok,_) in allowed.items() if ok}` — tested with 1000 random cases.

### H.5 Rationale schema
```
{
  "decided_at": now, "chosen": arm, "failure_class": fc,
  "expected_p": float|None, "expected_value": float|None,
  "fallback": None|"ESCALATE"|"STOP", "fallback_reason": str|None,
  "considered": [ {arm, allowed, reason, sampled_p, cost, ev, chosen} ... ]   # always 5 rows, ARMS order
}
```

### H.6 `explain_rationale(rationale, case) -> list[str]`
Pure string builder for the UI. Produces, in order: (1) diagnosis line: `"{error_code} on {method} → class {fc}."`; (2) one line per blocked arm: `"{arm} blocked — {reason}."`; (3) selection line: `"{chosen} selected — highest expected value ₹{ev:,.0f} (sampled P(recover)={p:.0%}, cost ₹{cost})."` or fallback line; (4) for each allowed-but-not-chosen arm: `"{arm} allowed but ranked lower (EV ₹{ev:,.0f})."`

### H.7 Learning loop
`engine.run` calls `bandit.update(fc, arm, int(success))` immediately after each executed action of the smart policy, in time order. Because events are processed by a time-ordered heap, later cases benefit from earlier outcomes (online learning). The naive policy never updates the bandit.

---

## SECTION I — Workflow / state machine (`engine.py`)

### I.1 States and transitions

```
             ┌──────────────────────────────────────────────┐
             │                                              │
FAILED ──► OPEN ──► DECIDE ──► (arm ∈ executable) ──► SCHEDULE ──► EXECUTE ──► outcome ──┤
                     │                                                          success → RECOVERED (terminal)
                     │                                                          failure → OPEN (loop)
                     ├── arm == ESCALATE ──► ESCALATED (terminal; human may later resolve → RECOVERED/EXHAUSTED)
                     └── arm == STOP ──────► EXHAUSTED (terminal)
```

| Transition | Cause |
|---|---|
| OPEN → SCHEDULE/EXECUTE | `decide` returned an executable arm |
| EXECUTE → RECOVERED | `rng.random() < hidden_recovery_prob(case, arm, executed_at)` |
| EXECUTE → OPEN | outcome false; case re-queued at `executed_at` |
| OPEN → ESCALATED | `decide` returned ESCALATE (no viable action, high value, ≥1 attempt) |
| OPEN → EXHAUSTED | `decide` returned STOP |
| ESCALATED → RECOVERED / EXHAUSTED | human approval executes PAYMENT_LINK (Section M) |

### I.2 Termination proof
Each pass through EXECUTE increments exactly one of `retries` (bounded by `max_retries`) or `messages` (bounded by `contact_cap`). Once both bounds are hit, no executable arm is allowed, so `decide` returns ESCALATE or STOP, both terminal. Additionally every execution advances time by ≥ 2 hours and the window rule blocks all executables after `recovery_window_days`. The naive policy is bounded by its own `retries < 3`. Therefore the loop performs at most `(max_retries + contact_cap + 1)` decisions per case. A test with `max_retries=8, contact_cap=5, n=300` asserts the loop finishes and every case is terminal.

### I.3 `run(cases, controls=DEFAULT_CONTROLS, policy="smart", seed=1) -> (cases, audit, bandit)`

```
controls = validate_controls(controls)
cases = deepcopy(cases)                      # never mutate caller's list (fair benchmark)
outcome_rng = random.Random(seed)            # world randomness
bandit = Bandit(seed * 7 + 1)                # decision randomness (independent stream)
audit = []; seq = 0
heap = [(c.failed_at, c.id, c.id) for c in cases]; heapify
while heap:
    now, _, cid = heappop(heap); case = by_id[cid]
    if case.state != "OPEN": continue
    if policy == "smart": arm, rationale = decide(case, now, bandit, controls)
    else:                 arm = "RETRY_24H" if case.retries < 3 else "STOP"
                          rationale = {"decided_at": now, "chosen": arm, "failure_class": fc, "note": "naive fixed schedule: retry every 24h ×3, ignores decline code and policy"}
    if arm in {"ESCALATE","STOP"}:
        case.state = "ESCALATED" if arm=="ESCALATE" else "EXHAUSTED"
        append terminal entry (kind="terminal", executed_at=None, success=None, violation=0); continue
    # schedule
    delay = salary_delay(case, now) if arm=="RETRY_SALARY_DAY" else ACTION_DELAY_H[arm]
    at = now + delay; deferred = False
    if arm in CONTACT_ARMS and policy=="smart": at2 = defer_quiet(at, quiet); deferred = at2 != at; at = at2
    # violations (independent auditor, evaluated on pre-increment snapshot)
    reasons = check_violations(case, arm, now, at, controls)
    # execute against the world
    success = outcome_rng.random() < hidden_recovery_prob(case, arm, at)
    case.cost += COST[arm]
    if arm in RETRY_ARMS: case.retries += 1; case.last_retry_at = at
    else:                 case.messages += 1
    entry = {...kind="action"...}; case.history.append(entry); audit.append(entry)
    if policy=="smart": bandit.update(fc, arm, int(success))
    if success: case.state="RECOVERED"; case.recovered_at=at
    else:       heappush(heap, (at, seq, cid))
return cases, audit, bandit
```
Heap tiebreak uses a monotonically increasing `seq` so ordering is deterministic. The naive policy does **not** apply quiet-hour deferral (it "ignores policy") — but it never sends messages anyway, so this is moot; keep the code path explicit.

### I.4 `execute_human_action(case, arm, controls, audit, bandit, seed) -> dict`
Used by HITL. `arm` must be `PAYMENT_LINK` (only supported human action). `decided_at = last entry's executed_at or decided_at`; `at = defer_quiet(decided_at + ACTION_DELAY_H[arm], quiet)`; `success = random.Random(seed + 10_000 + case.id).random() < hidden_recovery_prob(case, arm, at)`; increments `messages`, `cost`; state → RECOVERED or EXHAUSTED; appends entry with `kind="human"`, `rationale={"chosen": arm, "note": "approved by human reviewer"}`; `bandit.update(fc, arm, success)`; returns the entry. Contact cap is intentionally **not** enforced for a human-approved action (the human is the override), but `check_violations` still runs and is recorded — this is honest: the UI shows "human override" if a violation tag appears.

---

## SECTION J — Simulator (`simulator.py`)

### J.1 `generate(n: int, seed: int = 42) -> list[Case]`
```
rng = random.Random(seed)
for i in range(n):
    method = rng.choices(["card","upi_autopay","netbanking"], [0.45,0.45,0.10])[0]
    code   = rng.choices(list(CODES), WEIGHTS)[0]
    apply compatibility repair (Section F)
    amount = round(rng.choice([199,299,499,999,1499,2999,4999]) * rng.uniform(0.9,1.3), 2)
    failed_at = rng.randint(0, 119)
    salary_day = rng.randint(1, 28)
    responsiveness = rng.random()
    Case(i, method, amount, code, failed_at, salary_day, responsiveness)
```
`n = 0` returns `[]`. `n < 0` raises `ValueError`. Draw order must not change (reproducibility).

### J.2 `day_of_month(hour: int) -> int` = `(hour // 24) % 28 + 1`.

### J.3 `hidden_recovery_prob(case, action, at_hour) -> float`  — **ground truth**

```
fc = case.failure_class; r = case.responsiveness
since_salary = (day_of_month(at_hour) - case.salary_day) % 28
if action in RETRY arms:
    HARD → 0.0
    ACTION_REQUIRED → 0.02
    TRANSIENT → 0.75 if at_hour - failed_at >= 2 else 0.15
    SOFT → 0.65 if since_salary <= 2 else 0.12
elif action == "SEND_REMINDER":
    base = {HARD:0.0, TRANSIENT:0.30, SOFT:0.25, ACTION_REQUIRED:0.35}[fc]; return base * (0.4 + 0.6*r)
elif action == "PAYMENT_LINK":
    base = {HARD:0.25, TRANSIENT:0.50, SOFT:0.40, ACTION_REQUIRED:0.55}[fc]; return base * (0.4 + 0.6*r)
else: 0.0
```
Note: retries are deliberately independent of `responsiveness` (a retry doesn't need the customer); messages/links depend on it. Any change to this function changes the demo numbers; tune only here and in `PRIORS`.

### J.4 Data boundary
`hidden_recovery_prob` and `responsiveness` are the "external world". Only `engine.run` (execution step) and `engine.execute_human_action` may call/read them. `tests/test_boundaries.py` reads the source of `policy.py` and `decide.py` and asserts neither string appears.

---

## SECTION K — Metrics and benchmark (`metrics.py`)

### K.1 `summarize(cases, audit) -> dict`
```
cases_n, at_risk = len, Σ amount
recovered_cases, recovered = count/Σ amount where state==RECOVERED
rate = recovered_cases / cases_n (0.0 if n==0)
retries = # audit entries kind in {action,human} with arm ∈ RETRY_ARMS
messages = # ... arm ∈ CONTACT_ARMS
cost = Σ case.cost
net = recovered - cost
violations = Σ entry.violation
escalated = # state==ESCALATED; exhausted = # state==EXHAUSTED
```

### K.2 `by_class(cases) -> pandas.DataFrame`
Index = class in fixed order `[SOFT, TRANSIENT, ACTION_REQUIRED, HARD]`; columns `cases, recovered, recovery_rate, amount_at_risk, amount_recovered`. Missing classes appear with zeros (reindex).

### K.3 `confidence(n, controls, seeds=range(10)) -> pandas.DataFrame`
For each seed `s`: `cases = generate(n, 1000 + s)`; run smart with `seed=s`, naive with `seed=s`; row: `seed, smart_rate, naive_rate, lift_pp = 100*(smart_rate-naive_rate), smart_net, naive_net, net_lift, smart_violations, naive_violations, smart_retries, naive_retries`. UI computes `mean` and `std` (sample SD, `ddof=1`) and prints "mean ± SD across {k} seeds". No p-values, no "significant".

### K.4 Fairness rules
Both policies receive deep copies of the identical case list and identical controls; both use the same outcome-RNG seed. Differences in outcomes stem only from different actions (and thus different RNG consumption) — state this in README.

---

## SECTION L — Outreach / LLM guardrails (`outreach.py`)

### L.1 Templates
```
SEND_REMINDER: "Hi! Your payment of ₹{amount} could not be processed. We'll retry shortly — please ensure funds are available. Reply STOP to opt out."
PAYMENT_LINK:  "Hi! Your payment of ₹{amount} failed. Pay securely via UPI in one tap: <razorpay-payment-link>. Reply STOP to opt out."
```
`amount` formatted `f"{case.amount:.2f}"`. Other arms → `""`.

### L.2 `draft(case, arm, use_llm=False, timeout_s=8) -> tuple[str, str]`
Returns `(message, mode)`. Flow: build template; if empty → `("", "n/a")`. If `not use_llm` → `(template, "template (deterministic mode)")`. If no `GEMINI_API_KEY` in `os.environ` → `(template, "template (no API key)")`. Else try `_llm_rewrite(template, amount, timeout_s)`; on any exception → `(template, f"template (LLM unavailable: {ExceptionName})")`; run `validate_rewrite`; on failure → `(template, "template (LLM output failed guardrail: {reason})")`; else `(rewritten, "gemini-1.5-flash (guardrail passed)")`.

### L.3 `_llm_rewrite(template, amount_str, timeout_s) -> str`
Lazy `import google.generativeai as genai`; prompt: *"Rewrite the following customer message in a warm, concise tone (≤60 words). You MUST keep the exact amount ₹{amount}, keep any `<razorpay-payment-link>` placeholder verbatim, and keep the sentence 'Reply STOP to opt out.' You MUST NOT mention discounts, offers, penalties, legal action, deadlines, or urgency. Return only the message."* Use `request_options={"timeout": timeout_s}`.

### L.4 `validate_rewrite(original, rewritten, amount_str) -> tuple[bool, str]`
Checks in order: non-empty; `amount_str in rewritten`; `"STOP" in rewritten`; if `"<razorpay-payment-link>" in original` then it must be in `rewritten`; word count ≤ 80; no banned substrings (case-insensitive): `discount, offer, % off, cashback, free, penalty, legal, court, blacklist, last chance, final warning, urgent, immediately, within 24 hours, suspend, terminate`; no currency amount other than the original (regex `₹\s?\d[\d,]*(\.\d+)?` — every match must equal `₹`+amount_str). Returns `(True, "ok")` or `(False, reason)`. Fully testable without network.

### L.5 What the LLM cannot do
Choose actions, change amount, remove opt-out, threaten, create urgency, invent discounts, alter terms. It's invoked only *after* `decide` has already selected `SEND_REMINDER` or `PAYMENT_LINK`, and only when the UI toggle "Enable LLM rewrite" is on.

---

## SECTION M — Human-in-the-loop

- Source: cases with `state == "ESCALATED"` after a smart run.
- Display per case: id, amount, method, error code, class, retries, messages, last decision's `fallback_reason` (the "reason for escalation"), and the timeline.
- Action: **Approve Payment Link** → `engine.execute_human_action(case, "PAYMENT_LINK", controls, audit, bandit, seed)` → show outcome badge (RECOVERED / EXHAUSTED) → `st.rerun()`.
- Secondary (P1): **Close case** → sets `EXHAUSTED`, appends `kind="human"`, `arm="STOP"` entry.
- Empty queue: informational message "No cases awaiting review. Lower the escalation threshold in Policy Controls to route more cases to humans."
- All human actions appear in the Audit Trail with `kind="human"`.

---

## SECTION N — Complete UI/UX architecture (`app.py`)

### N.0 Global
- `st.set_page_config(page_title="Recover", page_icon="↺", layout="wide", initial_sidebar_state="expanded")`.
- Inject one CSS block: system font stack; KPI cards (`div[data-testid="stMetric"]` white card, 1px border `#E2E8F0`, radius 12px, padding 16px); badges via inline HTML spans (`.badge-track`, `.badge-sim` amber, `.badge-ok` green, `.badge-block` red); section headers with a thin accent bar `#2563EB`; hide Streamlit footer/hamburger. No animations.
- Sidebar: logo text "↺ RECOVER", caption "Policy-bounded payment recovery", navigation `st.radio` with the 8 sections, then a persistent "Simulation" box: n slider (50–2000, step 50, default 400), seed number input (default 42), **Run recovery simulation** primary button, and a small status line ("Last run: n=400, seed=42, controls hash …" or "Not run yet"). A checkbox "Enable LLM rewrite (needs GEMINI_API_KEY)" default off. Persistent amber badge: "SIMULATION — no real payments".
- Session state keys: `controls` (dict), `n`, `seed`, `llm`, `sim` (dict: `cases, smart, audit_smart, bandit, naive, audit_naive, controls_used, n, seed`), `stale` (bool: controls changed since last run), `selected_case` (int).
- On first load: auto-run with defaults so the Overview is never empty.
- `run_simulation()` helper in app.py: validates controls, generates, runs smart and naive, stores in `sim`, clears `stale`.

### N.1 Overview (landing)
- Hero row: title "RECOVER", tagline "Turn failed payments into recovered revenue.", badges: "Track 3 · AI Revenue Recovery", "Runs locally · no API key", "Simulation".
- If `stale`: warning "Policy controls changed — re-run to apply."
- KPI row (6 `st.metric`): Revenue at Risk (₹), Revenue Recovered (₹, delta vs naive), Recovery Rate (%, delta pp), Net Recovered (₹, delta), Retry Attempts (delta, inverse color), Policy Violations (value, delta "naive: N", inverse).
- Two columns: left "Recover vs Naive" grouped bar (recovered ₹, net ₹, cost ₹); right "Recovery by Failure Class" grouped bar (recover vs naive recovery_rate). Use `st.bar_chart` on a tidy DataFrame.
- Footer strip: three principle cards: "Rules build the fence", "The bandit chooses within it", "Every decision is audited".

### N.2 Recovery Operations
- Filters row: state multiselect, class multiselect, method multiselect, text search by case id.
- Table (`st.dataframe`, `use_container_width`, column_config): Case ID, Method, Amount (₹), Failure Code, Failure Class, State (badge-like text), Retries, Messages, Last Action, Recovered At, Cost.
- Selecting a row (via `selectbox` of case ids filtered) sets `selected_case` and shows a button "Open in Case Explorer".

### N.3 Case Explorer (most important)
- Quick-jump chips (buttons): "A hard decline", "Insufficient funds (UPI Autopay)", "Transient issuer outage", "Escalated high-value" — each picks the first matching case id (deterministic) and sets `selected_case`.
- Case picker: selectbox labelled `#id · method · code · ₹amount · state`.
- Panel 1 **Payment**: method, amount, failed at (day/hour), state, cost so far.
- Panel 2 **Diagnosis**: error code → class with one-line meaning (from a small dict in app.py mirroring Section F).
- Panel 3 **Timeline**: table of `case.history` (decided_at, executed_at, arm, success, deferred, violation).
- Panel 4 **Last decision explained**: bullets from `explain_rationale`; then table of `rationale.considered` with columns Action, Allowed (✓/✗), Reason, Sampled P, Cost, EV, Chosen (★). Highlight blocked rows in red text, chosen in green (use column_config or emoji markers — no HTML tables).
- Panel 5 **Outcome**: RECOVERED at hour X / EXHAUSTED / ESCALATED with reason.
- Panel 6 **Outreach draft**: if last executed arm ∈ CONTACT_ARMS → `draft(case, arm, use_llm=st.session_state.llm)`; show message and mode caption.
- For cases with only a terminal entry: show the terminal rationale ("Stopped immediately because …").

### N.4 Decision Intelligence
- Intro line: "The bandit learned these online, in time order, from observed outcomes only."
- Table from `bandit.snapshot()`: Class, Action, Prior (α,β), Prior mean, Posterior (α,β), Posterior mean, Observations, Δ (posterior − prior mean). Use `column_config.ProgressColumn` for posterior mean.
- Chart: for each class a bar chart of posterior mean per arm (4 small charts in 2×2 grid).
- Callout: "Look for: ACTION_REQUIRED retries collapsing toward ~2%; SOFT RETRY_SALARY_DAY rising; HARD never retried."

### N.5 Human Review — Section M.

### N.6 Audit Trail
- Filters: policy (smart/naive/human), kind, class, violation only, case id.
- Table with columns: seq, kind, decided_at, executed_at, case_id, arm, class, amount, success, violation, violation_reasons, deferred.
- Download buttons: "Download audit (JSON)" for smart+human entries; "Download naive audit (JSON)".
- Caption: "Append-only within a run. Re-running the simulation creates a new log."

### N.7 Experiment
- Head-to-head table for the current run: rows = metric (Recovery Rate, Recovered ₹, Net ₹, Fees ₹, Retries, Messages, Violations, Escalated), cols = Recover, Naive, Δ.
- Section "Is the lift real? 10-seed check": button "Run 10-seed experiment" (cached by `(n_capped, controls_tuple)` using `@st.cache_data`; cap n at 400 for speed); results table; summary sentence: `Recovery-rate lift: {mean:.1f} ± {sd:.1f} pp · Net lift: ₹{mean:,.0f} ± {sd:,.0f} (mean ± SD across 10 seeds, n={n})`; bar chart of lift_pp by seed.
- Methodology expander: identical cases, identical controls, same outcome seed per policy; simulated world; no significance claim.

### N.8 Policy Controls
- Editable (write to `session_state.controls`, set `stale=True`): Max retries (0–8), Contact cap (0–5), Escalate above ₹ (0–100000, step 500), Recovery window days (3–45).
- Read-only "Hard safety fence" list with lock icons: Never retry hard declines; UPI Autopay 24h pre-debit notice; Min 2h between retries; Quiet hours 21:00–09:00 (messages deferred); Contact arms never chosen by the LLM.
- Button "Apply & re-run" → `run_simulation()`.
- Explanation card: "These controls change the fence, not the code. The bandit only learns inside it."

### N.9 Design principles (enforced)
Business numbers first; one idea per screen; no decorative charts; every table has units; no developer jargon on Overview (jargon allowed in Decision Intelligence); every screen carries the "Simulation" badge in the sidebar.

---

## SECTION O — Module-by-module implementation

(Contracts are in Section P; behaviors in G–L. This section pins what each module *exports*.)

**`recover/__init__.py`**: `__version__ = "1.0.0"`, nothing else.

**`recover/simulator.py`** exports: `Case`, `CODES`, `WEIGHTS`, `METHODS`, `CLASSES` (ordered list), `generate`, `day_of_month`, `hidden_recovery_prob`.

**`recover/policy.py`** exports: `ARMS, RETRY_ARMS, CONTACT_ARMS, COST, ACTION_DELAY_H, MIN_SALARY_DELAY_H, MIN_ATTEMPTS_BEFORE_ESCALATION, DEFAULT_CONTROLS, validate_controls, allowed_actions, is_quiet, defer_quiet, salary_delay, check_violations`.

**`recover/decide.py`** exports: `PRIORS, Bandit, decide, explain_rationale`.

**`recover/engine.py`** exports: `run, execute_human_action`, and re-exports `salary_delay, defer_quiet` (`from .policy import salary_delay, defer_quiet`).

**`recover/metrics.py`** exports: `summarize, by_class, confidence`.

**`recover/outreach.py`** exports: `TEMPLATES, BANNED, draft, validate_rewrite`.

**`app.py`** internal helpers: `inject_css()`, `init_state()`, `run_simulation()`, `sidebar()`, `page_overview()`, `page_operations()`, `page_case_explorer()`, `page_intelligence()`, `page_review()`, `page_audit()`, `page_experiment()`, `page_controls()`, `history_df(entries)`, `fmt_inr(x)`.

---

## SECTION P — Core functions with inputs/outputs

| Function | Inputs | Output | Side effects | Calls |
|---|---|---|---|---|
| `simulator.generate(n, seed=42)` | `n:int≥0`, `seed:int` | `list[Case]` | none | `random.Random` |
| `simulator.day_of_month(hour)` | `int` | `int 1..28` | none | — |
| `simulator.hidden_recovery_prob(case, action, at_hour)` | `Case`, arm str, int | `float 0..1` | none | `day_of_month` |
| `policy.validate_controls(controls)` | dict | sanitized dict | none | — |
| `policy.allowed_actions(case, now, controls)` | `Case`, int, dict | `dict[arm → (bool, str)]` with all 7 arms | none | `salary_delay` |
| `policy.is_quiet(hour, quiet)` | int, (int,int) | bool | none | — |
| `policy.defer_quiet(hour, quiet)` | int, (int,int) | int ≥ hour | none | `is_quiet` |
| `policy.salary_delay(case, now)` | `Case`, int | int ≥ 2 | none | `day_of_month` |
| `policy.check_violations(case_before, arm, decided_at, executed_at, controls)` | snapshot, arm, int, int, dict | `list[str]` | none | `is_quiet` |
| `decide.Bandit(seed)` | int | instance | — | — |
| `Bandit.params(fc, arm)` | str, str | `(α, β)` | none | — |
| `Bandit.sample(fc, arm)` | str, str | float | consumes rng | `params` |
| `Bandit.mean(fc, arm)` | str, str | float | none | `params` |
| `Bandit.update(fc, arm, success)` | str, str, int∈{0,1} | None | mutates `post`, `counts` | `params` |
| `Bandit.snapshot()` | — | `list[dict]` | none | — |
| `decide.decide(case, now, bandit, controls)` | `Case`, int, Bandit, dict | `(arm, rationale)` | consumes bandit rng | `allowed_actions`, `Bandit.sample` |
| `decide.explain_rationale(rationale, case)` | dict, Case | `list[str]` | none | — |
| `engine.run(cases, controls, policy, seed)` | list[Case], dict, `"smart"\|"naive"`, int | `(cases_copy, audit, bandit)` | none on inputs | everything above |
| `engine.execute_human_action(case, arm, controls, audit, bandit, seed)` | Case, `"PAYMENT_LINK"`, dict, list, Bandit, int | audit entry dict | mutates case, audit, bandit | `defer_quiet`, `hidden_recovery_prob`, `check_violations` |
| `metrics.summarize(cases, audit)` | list, list | dict (K.1) | none | — |
| `metrics.by_class(cases)` | list | DataFrame | none | pandas |
| `metrics.confidence(n, controls, seeds)` | int, dict, iterable | DataFrame | none | `generate`, `run`, `summarize` |
| `outreach.draft(case, arm, use_llm=False, timeout_s=8)` | Case, arm, bool, int | `(str, str)` | network only if `use_llm` and key | `validate_rewrite`, `_llm_rewrite` |
| `outreach.validate_rewrite(original, rewritten, amount_str)` | str, str, str | `(bool, str)` | none | re |

---

## SECTION Q — Data flow (end to end)

1. **UI → simulator.** `run_simulation()` reads `n`, `seed`, `controls` from session state → `generate(n, seed)` → `list[Case]` (each has visible fields + hidden `responsiveness`).
2. **Simulator → engine.** `run(cases, controls, "smart", seed)` deep-copies the list, builds a min-heap keyed by `failed_at`.
3. **Engine → decide.** Pops the earliest event `(now, case)`; calls `decide(case, now, bandit, controls)`.
4. **decide → policy.** `allowed_actions(case, now, controls)` returns 7 `(allowed, reason)` pairs computed purely from visible case fields, `now`, controls, and scheduling constants.
5. **decide → bandit.** For each allowed executable arm: `bandit.sample(fc, arm)` → `p`; `ev = p·amount − cost`. Blocked arms get `p = ev = None` but stay in `considered`.
6. **decide → engine.** Returns `(arm, rationale)`; `arm` is guaranteed allowed.
7. **Engine scheduling.** `at = now + delay(arm)`; contact arms pass through `defer_quiet`; `deferred` flag recorded.
8. **Engine auditor.** `check_violations(case_before, arm, now, at, controls)` → tags (should be empty for smart).
9. **Engine → world.** `success = outcome_rng.random() < hidden_recovery_prob(case, arm, at)` — the only place the world is consulted.
10. **Engine bookkeeping.** Increment `retries`/`messages`, add cost, set `last_retry_at`; build audit entry; append to `case.history` and global `audit`.
11. **Engine → bandit.** `bandit.update(fc, arm, success)` (smart only).
12. **Engine state.** Success → RECOVERED; failure → re-push `(at, seq, id)`; ESCALATE/STOP → terminal entries.
13. **Engine → metrics.** `summarize`, `by_class` on smart and naive outputs; `confidence` reruns 2–12 over seeds.
14. **Metrics/engine → UI.** Overview KPIs, Operations table, Case Explorer (history + rationale + `explain_rationale` + `draft`), Intelligence (`bandit.snapshot`), Review (`execute_human_action`), Audit (entries + JSON), Experiment (`confidence`), Controls (writes `controls`, sets `stale`).

---

## SECTION R — Testing strategy

Run with `pytest -q`. Target: ≥ 25 tests, < 5 s total.

**`tests/test_simulator.py`**
1. `generate(100, 42)` twice → identical field-by-field. 2. Different seeds differ. 3. No incompatible method/code pairs in 2000 cases. 4. All amounts > 0, `failed_at ∈ [0,120)`, salary_day 1..28. 5. `n=0 → []`; `n=-1 → ValueError`. 6. `hidden_recovery_prob` returns 0.0 for HARD retries and within [0,1] for all combos.

**`tests/test_policy.py`**
7. Hard decline → all RETRY arms blocked with "hard decline" in reason. 8. UPI Autopay: `RETRY_2H` blocked with "pre-debit", `RETRY_24H` allowed. 9. Contact cap blocks contact arms. 10. Window exceeded blocks everything except STOP. 11. Max retries blocks retries. 12. Min-gap: case with `last_retry_at = now` → `RETRY_2H` still allowed when gap=2 (delay-aware); `RETRY_2H` blocked when `min_retry_gap_h=5`. 13. Escalation blocked below threshold / before attempts, allowed above with history. 14. `is_quiet`/`defer_quiet`: 23:00 → 09:00 next day; 03:00 → 09:00; 12:00 unchanged; non-wrap window `(13,15)`. 15. `salary_delay` ≥ 2; lands at hour-of-day 10 on the salary day; wraps to next month when past. 16. `check_violations` flags a HARD retry, a UPI 2h retry, a quiet-hour message; returns [] for a legal action. 17. `validate_controls` clamps and raises on garbage.

**`tests/test_decide.py`**
18. Invariant: over 1000 random cases/`now`/controls combos, `decide` never returns an arm that `allowed_actions` blocked. 19. All EV ≤ 0 (amount 1.0, costs 3.0) → STOP. 20. High-value, no viable → ESCALATE. 21. `Bandit.update(1)` raises mean, `update(0)` lowers it; counts increment. 22. Same seed → same decision sequence. 23. `explain_rationale` mentions every blocked arm's reason.

**`tests/test_engine.py`**
24. Every case terminal after `run` (smart & naive) for n=300, `max_retries=8, contact_cap=5`. 25. Smart violations == 0 across seeds 1..5, n=300, default controls. 26. Naive violations > 0 when HARD cases present. 27. Audit entries count == Σ len(case.history); every entry has all schema keys; `seq` strictly increasing. 28. Input cases not mutated by `run`. 29. Deferred flag true for a contact action scheduled into quiet hours (construct case with `failed_at` such that `now+24` lands at 23:00). 30. `execute_human_action` changes state to RECOVERED/EXHAUSTED and appends a `kind="human"` entry.

**`tests/test_metrics.py`**
31. `summarize` on empty list → zeros, rate 0.0, no exception. 32. `net == recovered - cost`. 33. `by_class` has exactly 4 rows in order. 34. `confidence(100, controls, seeds=range(2))` returns 2 rows with expected columns.

**`tests/test_outreach.py`**
35. `draft` with no key and `use_llm=True` → template + "no API key" mode. 36. `draft` with `use_llm=False` never imports genai (monkeypatch `sys.modules` guard). 37. `validate_rewrite` rejects: missing amount, missing STOP, banned word, extra amount, > 80 words, missing link placeholder; accepts a clean rewrite. 38. Monkeypatched `_llm_rewrite` raising → template with "LLM unavailable".

**`tests/test_boundaries.py`**
39. Source of `policy.py` and `decide.py` contains neither `hidden_recovery_prob` nor `responsiveness`. 40. `engine.py` references `hidden_recovery_prob` at most twice (run + human action).

---

## SECTION S — Error handling

| Situation | Handling |
|---|---|
| `n == 0` | `generate` returns `[]`; `run` returns `([], [], bandit)`; `summarize` returns zeros; UI shows "No cases — increase the batch size." |
| Invalid controls | `validate_controls` clamps ints, raises `ValueError` on non-numeric; UI sliders make this unreachable but `run_simulation` wraps in `try/except ValueError` → `st.error`. |
| Missing API key | `draft` returns template with mode "no API key"; no exception. |
| genai not installed | lazy import inside try → template with "LLM unavailable: ImportError". |
| LLM timeout/HTTP error | caught → template. |
| LLM invalid output | `validate_rewrite` fails → template with reason. |
| Simulation exception | `run_simulation` catches `Exception`, shows `st.exception` in an expander and keeps the previous `sim` in state. |
| Empty escalation queue | informational message + hint. |
| Selected case id no longer valid after re-run | reset `selected_case` to first case id. |
| Case with no history (immediate terminal) | Case Explorer shows terminal rationale gracefully. |
| `confidence` slow for large n | cap at 400 in UI; cached; spinner. |

---

## SECTION T — Security / safety boundaries

1. **Policy over intelligence:** `decide` is the only caller of the bandit; it filters by `allowed_actions` first. Tested (R.18).
2. **World isolation:** `hidden_recovery_prob`/`responsiveness` invisible to policy/decide. Tested (R.39–40).
3. **LLM isolation:** LLM invoked only in `outreach.draft`, only after an action is chosen, only when toggle on and key present; output validated; on failure template is used. The LLM never sees case history, policy, or amounts other than the one in the message.
4. **No network by default:** the only network path is `_llm_rewrite`. No telemetry.
5. **No real money:** no Razorpay SDK, no HTTP client, no credentials besides the optional Gemini key; `.env.example` contains only `GEMINI_API_KEY=`.
6. **Secrets:** read via `os.environ`; never logged or displayed; UI shows only "key present: yes/no".
7. **Determinism:** all randomness from seeded `random.Random` instances; no `random.random()` module-level calls; no time-of-day reads.
8. **Auditability:** append-only lists; the UI never deletes entries; download is the full list.

---

## SECTION U — Razorpay conceptual mapping

| Recover concept | Razorpay surface (conceptual, not integrated) |
|---|---|
| Failed-payment event (`Case`) | Webhooks `payment.failed`, `subscription.pending`, `subscription.halted`; UPI Autopay presentment failure notifications |
| `error_code` | Razorpay `error.code`/`error.reason` + issuer decline reason (e.g., `payment_failed`, `BAD_REQUEST_ERROR` with reason `insufficient_funds`, mandate status `paused`/`revoked`) |
| `RETRY_*` | Subscription charge retry / mandate re-presentment (subject to pre-debit notification) |
| `PAYMENT_LINK` | Payment Links API (UPI intent / alternate method) |
| `SEND_REMINDER` | Notification / customer communication via merchant's channel |
| Policy controls | Merchant dashboard settings |
| Audit trail | Merchant-side decision log for disputes and compliance |
| Naive baseline | Fixed retry schedule many billing systems use today |

State in README and in a footnote on the Overview: *"Conceptual mapping only. Recover makes no API calls."*

---

## SECTION V — P0 / P1 / P2 priority

**P0 (demo dies without it):** simulator; taxonomy; policy engine + `check_violations`; bandit + `decide` + rationale; `run` with audit; `summarize`, `by_class`; naive baseline; Overview; Case Explorer (panels 1–5); Policy Controls (editable 4 + fence list); Experiment head-to-head; Audit table + JSON download; template outreach; tests R.7–R.12, R.18, R.24–R.27, R.39; README run instructions.

**P1 (strongly improves score):** `confidence` 10-seed + UI; Decision Intelligence screen; Human Review with approve; quick-jump chips; Recovery Operations filters; `explain_rationale` bullets; CSS polish; remaining tests; README full.

**P2 (only if time remains):** LLM rewrite path + guardrail tests; "Close case" button; per-class 2×2 charts; `.streamlit/config.toml` theme; screenshots in README.

---

## SECTION W — One-day implementation timeline (≈14 h)

| Time | Phase | Output |
|---|---|---|
| 0:00–0:30 | Task 1 skeleton | `pytest` collects 0 tests, app placeholder runs |
| 0:30–1:30 | Task 2 simulator + tests | 6 tests green |
| 1:30–3:00 | Task 3 policy + tests | 11 tests green; UPI/hard-decline rules proven |
| 3:00–4:00 | Task 4 bandit + decide + tests | invariant test green |
| 4:00–5:30 | Task 5 engine + tests | termination, 0 smart violations |
| 5:30–6:15 | Task 6 metrics + tests | numbers sane in a REPL |
| 6:15–6:45 | Task 7 outreach + tests | template fallback proven |
| 6:45–8:00 | Task 8 app shell + Overview | KPIs on screen |
| 8:00–9:30 | Task 9 Operations + Case Explorer | demo screens 7–13 work |
| 9:30–10:30 | Task 10 Intelligence + Review + Audit | screens 14–17 work |
| 10:30–11:15 | Task 11 Experiment + Controls | screens 18–19 work |
| 11:15–12:00 | Tune `hidden_recovery_prob`/`PRIORS` if story unclear (only these two) | clear lift, 0 vs N violations |
| 12:00–13:00 | Task 12 polish, README, full test run, smoke test AA | tag v1.0 |
| 13:00–14:00 | Buffer / P2 | — |

Rule: no UI work until Tasks 2–6 are green. UI must never mask backend defects.

---

## SECTION X — Sequential AI-IDE coding tasks (index)

| # | Name | Creates | Modifies | Depends on |
|---|---|---|---|---|
| 1 | Project skeleton | `requirements.txt`, `.env.example`, `recover/__init__.py`, `app.py` (placeholder), `tests/__init__.py`, `README.md` (stub), `.gitignore` | — | — |
| 2 | Simulator | `recover/simulator.py`, `tests/test_simulator.py` | — | 1 |
| 3 | Policy engine | `recover/policy.py`, `tests/test_policy.py` | — | 2 |
| 4 | Bandit + decision | `recover/decide.py`, `tests/test_decide.py`, `tests/test_boundaries.py` | — | 3 |
| 5 | Workflow engine | `recover/engine.py`, `tests/test_engine.py` | `tests/test_boundaries.py` | 4 |
| 6 | Metrics | `recover/metrics.py`, `tests/test_metrics.py` | — | 5 |
| 7 | Outreach | `recover/outreach.py`, `tests/test_outreach.py` | — | 2 |
| 8 | App shell + Overview | — | `app.py` | 6 |
| 9 | Operations + Case Explorer | — | `app.py` | 8, 7 |
| 10 | Intelligence + Human Review + Audit | — | `app.py` | 9 |
| 11 | Experiment + Policy Controls | — | `app.py` | 10 |
| 12 | Polish, README, final verification | `.streamlit/config.toml` (optional) | `app.py`, `README.md` | 11 |

---

## SECTION Y — Ready-to-paste AI-IDE prompt for every task

> **Preamble to prepend to every prompt (copy once into the IDE's system/rules file):**
> You are implementing the RECOVER project from the blueprint. Before editing, inspect the repository. Follow the architecture exactly; do not add modules, dependencies, or infrastructure beyond `streamlit`, `pandas`, `pytest`, and optional `google-generativeai`. Keep modules small and deterministic (all randomness via seeded `random.Random`). Write tests alongside code, run `pytest -q` after each task, fix failures before continuing. Never remove a requirement silently. Never let the learning layer bypass `allowed_actions`. Never let an LLM choose a recovery action. Never add real payment API calls. `policy.py` and `decide.py` must never reference `hidden_recovery_prob` or `responsiveness`. The app must run with no API key. Do not overengineer. At the end of each task, report: files changed, test output, and anything you were unable to do.

---

**TASK 1 — Project skeleton**

```
OBJECTIVE: Create the repository scaffold so tests and the app can run.
FILES TO CREATE: requirements.txt, .env.example, .gitignore, recover/__init__.py, tests/__init__.py, app.py (placeholder), README.md (stub)
FILES TO MODIFY: none
IMPLEMENTATION DETAILS:
- requirements.txt: streamlit>=1.32, pandas>=2.0, pytest>=7, google-generativeai>=0.5 (comment: optional; app works without a key).
- .env.example: single line "GEMINI_API_KEY=" with a comment that it is optional.
- .gitignore: .venv/, __pycache__/, .env, .pytest_cache/, .streamlit/secrets.toml
- recover/__init__.py: __version__ = "1.0.0"
- app.py: minimal Streamlit page with title "RECOVER" and caption "scaffold" (replaced in Task 8).
- README.md: title, one-line pitch, "Run: pip install -r requirements.txt && pytest -q && streamlit run app.py".
DEPENDENCIES: none
TESTS REQUIRED: none (pytest must collect 0 tests without error)
COMMANDS: python -m venv .venv && (activate) && pip install -r requirements.txt && pytest -q && streamlit run app.py --server.headless true (Ctrl+C after it starts)
EXPECTED RESULT: pytest reports "no tests ran"; Streamlit starts without error.
DONE CRITERIA: all files exist; commands succeed.
DO NOT CHANGE: nothing else; do not add extra dependencies.
```

---

**TASK 2 — Simulator**

```
OBJECTIVE: Implement the domain model and seeded synthetic world.
FILES TO CREATE: recover/simulator.py, tests/test_simulator.py
IMPLEMENTATION DETAILS:
- Module constants: METHODS = ["card","upi_autopay","netbanking"]; CLASSES = ["SOFT","TRANSIENT","ACTION_REQUIRED","HARD"];
  CODES (ordered dict) = INSUFFICIENT_FUNDS:SOFT, DO_NOT_HONOR:SOFT, ISSUER_UNAVAILABLE:TRANSIENT, UPI_TIMEOUT:TRANSIENT,
  EXPIRED_CARD:ACTION_REQUIRED, MANDATE_PAUSED:ACTION_REQUIRED, AUTH_TIMEOUT:ACTION_REQUIRED, MANDATE_REVOKED:HARD,
  CARD_LOST_STOLEN:HARD, RISK_DECLINE:HARD; WEIGHTS = [0.34,0.12,0.10,0.08,0.07,0.06,0.05,0.06,0.06,0.06].
- @dataclass Case with fields and defaults exactly: id:int, method:str, amount:float, error_code:str, failed_at:int,
  salary_day:int, responsiveness:float, state:str="OPEN", retries:int=0, messages:int=0, last_retry_at:int=-999,
  recovered_at:int=-1, cost:float=0.0, history:list=field(default_factory=list); property failure_class -> CODES[error_code].
  Docstring must state: responsiveness is HIDDEN (only hidden_recovery_prob may read it); salary_day is an observable estimate.
- generate(n, seed=42): raise ValueError if n<0; rng=random.Random(seed); per case, in this exact draw order:
  method=rng.choices(METHODS,[0.45,0.45,0.10])[0]; code=rng.choices(list(CODES),WEIGHTS)[0];
  repair: MANDATE_* on non-upi_autopay -> INSUFFICIENT_FUNDS; EXPIRED_CARD/CARD_LOST_STOLEN on non-card -> DO_NOT_HONOR;
  UPI_TIMEOUT on non-upi_autopay -> ISSUER_UNAVAILABLE; amount=round(rng.choice([199,299,499,999,1499,2999,4999])*rng.uniform(0.9,1.3),2);
  failed_at=rng.randint(0,119); salary_day=rng.randint(1,28); responsiveness=rng.random().
- day_of_month(hour) = (hour//24)%28+1.
- hidden_recovery_prob(case, action, at_hour): implement the table in blueprint Section J.3 exactly; actions starting with "RETRY" are retries.
  Docstring: "GROUND TRUTH of the simulated world. Only engine.run and engine.execute_human_action may call this."
FUNCTIONS: generate, day_of_month, hidden_recovery_prob
DEPENDENCIES: stdlib only
TESTS REQUIRED (tests/test_simulator.py): reproducibility same seed; different seeds differ; no incompatible pairs in 2000 cases;
  value ranges; n=0 -> []; n=-1 -> ValueError; hidden prob is 0.0 for HARD retries and in [0,1] for all class/action combos.
COMMANDS: pytest -q tests/test_simulator.py
EXPECTED RESULT: 6+ tests pass.
DONE CRITERIA: tests green; generate(400,42) runs in <50 ms.
DO NOT CHANGE: app.py, requirements.txt.
```

---

**TASK 3 — Policy engine**

```
OBJECTIVE: Implement the deterministic safety fence, scheduling helpers, and the independent violation auditor.
FILES TO CREATE: recover/policy.py, tests/test_policy.py
IMPLEMENTATION DETAILS:
- Constants exactly as blueprint Section G.1 (ARMS order matters; COST; ACTION_DELAY_H; MIN_SALARY_DELAY_H=2;
  MIN_ATTEMPTS_BEFORE_ESCALATION=1; DEFAULT_CONTROLS from Section E.3).
- Import day_of_month from .simulator ONLY. Do not import decide or engine.
- validate_controls(controls): return sanitized copy merged with defaults; clamp ranges per Section G.2; ValueError on non-numeric.
- is_quiet(hour, quiet), defer_quiet(hour, quiet), salary_delay(case, now): exactly per Section G.4.
- allowed_actions(case, now, controls=DEFAULT_CONTROLS) -> dict[arm -> (bool, reason)] for all 7 arms; apply rules in the order
  and with the exact reason strings of Section G.3. CRITICAL: the min-gap rule uses earliest_exec = now + earliest_delay(arm);
  the UPI rule compares earliest_delay(arm) with controls["pre_debit_notice_h"]; RETRY_SALARY_DAY's delay comes from salary_delay.
  Quiet hours never block (reason "ok"). STOP always allowed. Pure function: no randomness, no I/O, no mutation.
- check_violations(case_before, arm, decided_at, executed_at, controls) -> list[str] with tags exactly per Section G.5.
  This function must NOT call allowed_actions (independent auditor).
FUNCTIONS: validate_controls, is_quiet, defer_quiet, salary_delay, allowed_actions, check_violations
DEPENDENCIES: Task 2
TESTS REQUIRED (tests/test_policy.py): blueprint tests R.7–R.17, including the delay-aware min-gap regression test
  (case.last_retry_at == now with gap 2 -> RETRY_2H allowed; with min_retry_gap_h=5 -> blocked) and an exhaustive assertion
  that allowed_actions always returns all 7 arms.
COMMANDS: pytest -q
EXPECTED RESULT: all tests pass.
DONE CRITERIA: For a Case(method="upi_autopay", error_code="INSUFFICIENT_FUNDS"), allowed_actions at now=24 returns
  RETRY_2H=(False,"UPI Autopay: 24h pre-debit notification required before re-presentment") and RETRY_24H=(True,"ok").
DO NOT CHANGE: simulator.py behavior.
```

---

**TASK 4 — Bandit and decision engine**

```
OBJECTIVE: Implement Thompson Sampling over policy-filtered arms with a full rationale.
FILES TO CREATE: recover/decide.py, tests/test_decide.py, tests/test_boundaries.py
IMPLEMENTATION DETAILS:
- PRIORS dict exactly as Section H.2; default (1,3).
- class Bandit(seed): rng=random.Random(seed); post={}; counts={}; methods params/sample/mean/update/snapshot per Section H.3.
  snapshot() returns rows for classes ["SOFT","TRANSIENT","ACTION_REQUIRED","HARD"] x arms
  ["RETRY_2H","RETRY_24H","RETRY_SALARY_DAY","SEND_REMINDER","PAYMENT_LINK"] (for HARD, retry rows may be omitted).
- decide(case, now, bandit, controls) -> (arm, rationale) per Section H.4/H.5. Considered list always has 5 rows in ARMS order.
  Select max EV among allowed with ev > 0; ties -> first in ARMS order. Fallback ESCALATE if allowed else STOP, with fallback_reason text.
- explain_rationale(rationale, case) -> list[str] per Section H.6.
- Import only from .policy. The file must not contain the strings "hidden_recovery_prob" or "responsiveness".
FUNCTIONS: Bandit.__init__, params, sample, mean, update, snapshot, decide, explain_rationale
DEPENDENCIES: Task 3
TESTS REQUIRED: tests/test_decide.py -> R.18 invariant over 1000 random (case, now, controls) combos generated with a seeded rng
  (vary retries/messages/last_retry_at/method/class); R.19–R.23. tests/test_boundaries.py -> read source of recover/policy.py and
  recover/decide.py; assert neither contains "hidden_recovery_prob" or "responsiveness".
COMMANDS: pytest -q
EXPECTED RESULT: all pass.
DONE CRITERIA: decide never selects a blocked arm; rationale JSON-serializable (json.dumps(rationale, default=str) works).
DO NOT CHANGE: policy.py rule semantics.
```

---

**TASK 5 — Workflow engine**

```
OBJECTIVE: Implement the bounded, time-ordered event loop, audit trail, violation recording, online learning, and the HITL executor.
FILES TO CREATE: recover/engine.py, tests/test_engine.py
FILES TO MODIFY: tests/test_boundaries.py (add: engine.py source contains "hidden_recovery_prob" at most 2 times)
IMPLEMENTATION DETAILS:
- from .policy import (COST, ACTION_DELAY_H, RETRY_ARMS, CONTACT_ARMS, DEFAULT_CONTROLS, validate_controls,
  check_violations, salary_delay, defer_quiet); from .simulator import hidden_recovery_prob; from .decide import Bandit, decide.
  Re-export salary_delay and defer_quiet (they must be importable as recover.engine.salary_delay / defer_quiet).
- run(cases, controls=DEFAULT_CONTROLS, policy="smart", seed=1) -> (cases_copy, audit, bandit): implement Section I.3 exactly:
  deepcopy input; outcome_rng=random.Random(seed); bandit=Bandit(seed*7+1); heap entries (time, seq, case_id) with a global
  increasing seq for deterministic tiebreak; naive policy = RETRY_24H while retries<3 else STOP with the naive rationale note;
  terminal entries for ESCALATE/STOP; quiet-hour deferral for CONTACT_ARMS under smart policy; violations via check_violations
  on the pre-increment snapshot; outcome via hidden_recovery_prob; counters, cost, last_retry_at updates; audit entry schema
  exactly Section E.4 (both case.history and global audit reference the same dict); bandit.update only for smart; re-push on failure.
- execute_human_action(case, arm, controls, audit, bandit, seed) -> entry per Section I.4; only arm == "PAYMENT_LINK" supported (ValueError otherwise).
- ValueError for policy not in {"smart","naive"}.
FUNCTIONS: run, execute_human_action (+ re-exports)
DEPENDENCIES: Task 4
TESTS REQUIRED (tests/test_engine.py): R.24–R.30. For R.29 construct a card INSUFFICIENT_FUNDS case whose SEND_REMINDER at now+24
  lands at 23:00 and force the decision by using a controls dict with max_retries=0 so only contact arms are allowed; assert
  deferred True and executed_at % 24 == 9.
COMMANDS: pytest -q
EXPECTED RESULT: all pass; run(generate(400,42)) for both policies completes in < 1 s total.
DONE CRITERIA: summarize-like manual check in a REPL: smart violations 0, naive violations > 0, all states terminal.
DO NOT CHANGE: simulator.py, policy.py, decide.py.
```

---

**TASK 6 — Metrics**

```
OBJECTIVE: Implement benchmark metrics.
FILES TO CREATE: recover/metrics.py, tests/test_metrics.py
IMPLEMENTATION DETAILS:
- summarize(cases, audit) -> dict with keys: cases, at_risk, recovered_cases, recovered, rate, retries, messages, cost, net,
  violations, escalated, exhausted (Section K.1). Handle empty input (rate 0.0).
- by_class(cases) -> DataFrame indexed by class in fixed order [SOFT,TRANSIENT,ACTION_REQUIRED,HARD] with columns
  cases, recovered, recovery_rate, amount_at_risk, amount_recovered (reindex, fill 0).
- confidence(n, controls, seeds=range(10)) -> DataFrame with columns seed, smart_rate, naive_rate, lift_pp, smart_net, naive_net,
  net_lift, smart_violations, naive_violations, smart_retries, naive_retries; cases = generate(n, 1000+s); run smart and naive with seed=s.
FUNCTIONS: summarize, by_class, confidence
DEPENDENCIES: Task 5
TESTS REQUIRED: R.31–R.34.
COMMANDS: pytest -q; python -c "from recover.simulator import generate; from recover.engine import run; from recover.metrics import summarize; c=generate(400,42); print(summarize(*run(c,policy='smart',seed=42)[:2])); print(summarize(*run(c,policy='naive',seed=42)[:2]))"
EXPECTED RESULT: smart shows higher rate and net than naive, violations 0 vs >0. If smart does not beat naive clearly (≥10 pp), report it — do NOT change metrics; tuning happens only in simulator.hidden_recovery_prob / decide.PRIORS in Task 12 with explicit approval.
DONE CRITERIA: tests pass; printed numbers reported back.
DO NOT CHANGE: engine.py.
```

---

**TASK 7 — Outreach with guardrails**

```
OBJECTIVE: Implement deterministic message templates with optional, guardrailed LLM rewrite.
FILES TO CREATE: recover/outreach.py, tests/test_outreach.py
IMPLEMENTATION DETAILS:
- TEMPLATES and BANNED list per Section L.1/L.4.
- validate_rewrite(original, rewritten, amount_str) -> (bool, reason) per Section L.4, using re for currency amounts.
- _llm_rewrite(template, amount_str, timeout_s) -> str: lazy import google.generativeai inside the function; model "gemini-1.5-flash";
  prompt per Section L.3; request_options={"timeout": timeout_s}.
- draft(case, arm, use_llm=False, timeout_s=8) -> (message, mode) per Section L.2. Never raise. Never call the network unless
  use_llm is True AND os.environ.get("GEMINI_API_KEY") is non-empty.
FUNCTIONS: draft, validate_rewrite, _llm_rewrite
DEPENDENCIES: Task 2
TESTS REQUIRED: R.35–R.38 (use monkeypatch to set/unset GEMINI_API_KEY and to replace _llm_rewrite).
COMMANDS: pytest -q
EXPECTED RESULT: all pass with no network access.
DONE CRITERIA: draft(case,"PAYMENT_LINK") returns the template and a mode string containing "template".
DO NOT CHANGE: other modules.
```

---

**TASK 8 — App shell, state, sidebar, Overview**

```
OBJECTIVE: Replace the placeholder app with the console shell and the Overview page.
FILES TO MODIFY: app.py
IMPLEMENTATION DETAILS:
- Implement per Section N.0 and N.1: set_page_config; inject_css() (one st.markdown block; KPI cards, badges, hide footer);
  init_state() creating controls (copy of DEFAULT_CONTROLS), n=400, seed=42, llm=False, sim=None, stale=False, selected_case=None;
  run_simulation() = validate_controls -> generate -> run smart -> run naive -> store sim dict; wrap in try/except showing st.error;
  sidebar() with logo, nav radio for the 8 sections (Overview, Recovery Operations, Case Explorer, Decision Intelligence,
  Human Review, Audit Trail, Experiment, Policy Controls), simulation box (n slider 50–2000 step 50, seed input, Run button,
  status line, LLM checkbox, amber "SIMULATION — no real payments" badge).
- Auto-run on first load if sim is None.
- page_overview(): hero + badges; stale warning; 6 KPI metrics with deltas vs naive (Retry Attempts and Policy Violations use
  delta_color="inverse"); two charts (Recover vs Naive: recovered/net/cost; Recovery by class: smart vs naive recovery_rate) via st.bar_chart
  on tidy DataFrames; three principle cards at the bottom.
- Helpers: fmt_inr(x) -> "₹12,345"; history_df(entries) -> DataFrame dropping the rationale column.
- Other pages: create stub functions that render st.info("Coming in next task") so navigation works.
DEPENDENCIES: Tasks 6, 7
TESTS REQUIRED: none new; pytest -q must still pass.
COMMANDS: streamlit run app.py
EXPECTED RESULT: Overview renders KPIs within 2 s; changing n/seed and clicking Run updates numbers; navigation works.
DONE CRITERIA: screenshot-worthy Overview; no exceptions in terminal.
DO NOT CHANGE: recover/* modules.
```

---

**TASK 9 — Recovery Operations and Case Explorer**

```
OBJECTIVE: Build the case table and the explainability screen.
FILES TO MODIFY: app.py
IMPLEMENTATION DETAILS:
- page_operations() per Section N.2: filters (state, class, method multiselects; case id text), st.dataframe with column_config
  (Amount as number format "₹%.2f"), and a case selector + "Open in Case Explorer" button that sets selected_case and switches nav.
- page_case_explorer() per Section N.3: quick-jump chips (first HARD case; first upi_autopay INSUFFICIENT_FUNDS case; first TRANSIENT;
  first ESCALATED — each deterministic, disabled if none); case selectbox; Panels 1–6. Panel 4 uses decide.explain_rationale for bullets
  and renders rationale["considered"] as a DataFrame with columns Action, Allowed, Reason, Sampled P, Cost, EV, Chosen where Allowed shows
  "✓"/"✗" and Chosen shows "★"; format Sampled P as percent, EV as ₹. For the diagnosis panel include a CLASS_MEANING dict
  (4 one-liners) and a CODE_MEANING dict (10 one-liners) mirroring Section F.
- Panel 6 calls outreach.draft(case, last_arm, use_llm=st.session_state.llm) only when last executed arm is a contact arm; show mode caption.
- Handle cases whose history has only a terminal entry.
DEPENDENCIES: Task 8
TESTS REQUIRED: pytest -q still green.
COMMANDS: streamlit run app.py
EXPECTED RESULT: For a UPI Autopay INSUFFICIENT_FUNDS case, the explanation shows "RETRY_2H blocked — UPI Autopay: 24h pre-debit
  notification required before re-presentment." For a HARD case all three retry rows show ✗ with the hard-decline reason.
DONE CRITERIA: demo steps 7–13 of Section AB are performable.
DO NOT CHANGE: recover/* modules.
```

---

**TASK 10 — Decision Intelligence, Human Review, Audit Trail**

```
OBJECTIVE: Show learning, enable human approval, expose the audit log.
FILES TO MODIFY: app.py
IMPLEMENTATION DETAILS:
- page_intelligence() per Section N.4: bandit.snapshot() -> DataFrame; ProgressColumn for posterior_mean (0–1); Δ column;
  2x2 grid of per-class bar charts of posterior mean by arm; callout text.
- page_review() per Section M/N.5: list ESCALATED cases from sim["smart"]; per case a card with details + reason (last entry's
  rationale.fallback_reason) + expander with timeline; button "Approve payment link" (key unique per case) ->
  engine.execute_human_action(case, "PAYMENT_LINK", sim["controls_used"], sim["audit_smart"], sim["bandit"], sim["seed"]) ->
  st.success/warning with the resulting state -> st.rerun(). Empty state message per Section M. P1: "Close case" button.
- page_audit() per Section N.6: build DataFrame from sim["audit_smart"] (+ naive optionally via a toggle); filters; violation_reasons
  joined by ", "; two download buttons (json.dumps(..., default=str, indent=1)); caption about append-only.
DEPENDENCIES: Task 9
TESTS REQUIRED: pytest -q still green.
COMMANDS: streamlit run app.py
EXPECTED RESULT: Approving a case changes its state, adds a kind="human" audit row, and updates Overview KPIs after rerun.
DONE CRITERIA: demo steps 14–17 performable.
DO NOT CHANGE: recover/* modules.
```

---

**TASK 11 — Experiment and Policy Controls**

```
OBJECTIVE: Deliver the evidence screen and merchant controls.
FILES TO MODIFY: app.py
IMPLEMENTATION DETAILS:
- page_experiment() per Section N.7: head-to-head table (Recover, Naive, Δ) from summarize on current sim; "Run 10-seed experiment"
  button calling a @st.cache_data-wrapped function _confidence_cached(n_capped, controls_items_tuple) that calls metrics.confidence;
  results table; summary sentence with mean ± SD (ddof=1) for lift_pp and net_lift; bar chart of lift_pp by seed; methodology expander
  with the exact honesty wording from Section K.4 and "no statistical significance is claimed".
- page_controls() per Section N.8: sliders/number inputs writing to st.session_state.controls and setting stale=True on change;
  read-only fence list; "Apply & re-run" button -> run_simulation(); explanation card.
- Overview must show the stale warning when controls changed and not yet applied.
DEPENDENCIES: Task 10
TESTS REQUIRED: pytest -q still green.
COMMANDS: streamlit run app.py
EXPECTED RESULT: Changing contact cap from 2 to 0 and applying visibly reduces messages and changes recovery; 10-seed run completes in < 10 s at n=400.
DONE CRITERIA: demo steps 18–19 performable; reviewer can "change an input and watch the output change".
DO NOT CHANGE: recover/* modules.
```

---

**TASK 12 — Polish, README, final verification**

```
OBJECTIVE: Make it presentation-grade and verified.
FILES TO CREATE: .streamlit/config.toml (optional theme: primaryColor="#2563EB", backgroundColor="#FFFFFF", secondaryBackgroundColor="#F8FAFC", textColor="#0F172A", font="sans serif")
FILES TO MODIFY: app.py (copy/labels/spacing only), README.md
IMPLEMENTATION DETAILS:
- Run the smoke checklist in Section AA; fix any defect in app.py only.
- If the Overview lift is < 10 pp or smart violations != 0 with default controls, STOP and report numbers; only with explicit approval
  adjust simulator.hidden_recovery_prob or decide.PRIORS (nothing else), then re-run all tests.
- README per Section 46 of the spec: pitch, problem, solution, architecture (ASCII diagram from blueprint Section C), policy engine
  rules table, bandit explanation, workflow/state machine, auditability, benchmark methodology (honest wording), UI sections,
  Razorpay conceptual mapping (Section U), installation, running, testing, limitations (Section AD), roadmap, "Observable vs hidden"
  note (Section E.2), and a "This is a simulation" banner near the top. Add screenshot placeholders with filenames.
DEPENDENCIES: Task 11
TESTS REQUIRED: full pytest -q green; report count and runtime.
COMMANDS: pytest -q; streamlit run app.py; run through Section AB script once.
EXPECTED RESULT: ≥25 tests pass in < 5 s; the 3-minute demo flows without errors; app works with GEMINI_API_KEY unset.
DONE CRITERIA: git tag v1.0; README complete.
DO NOT CHANGE: rule semantics, audit schema, function signatures.
```

---

## SECTION Z — Integration checklist

- [ ] `app.py` imports only from `recover.*`, `streamlit`, `pandas`, `json`, `copy`; no business rules in `app.py`.
- [ ] `run_simulation()` uses `validate_controls` before `run`.
- [ ] Smart and naive runs use the same `cases` list and same `seed`.
- [ ] `selected_case` reset on re-run.
- [ ] Human approval mutates the objects stored in `st.session_state.sim` (not copies) so KPIs update.
- [ ] Overview KPIs recomputed from `sim` on every render (never cached separately).
- [ ] `confidence` cache key includes controls; cap `n` at 400.
- [ ] LLM checkbox state passed into `draft`; app never crashes when key missing.
- [ ] Every page shows content when `sim` exists; no page assumes an escalated case exists.
- [ ] Nav switch from Operations → Case Explorer works via session state.
- [ ] All dataframes use `use_container_width=True`; amounts formatted with ₹.
- [ ] `pytest -q` green after every task; `test_boundaries` present.

---

## SECTION AA — Final smoke-test checklist

1. Fresh venv → `pip install -r requirements.txt` → `pytest -q` → all pass.
2. `unset GEMINI_API_KEY` → `streamlit run app.py` → Overview loads with defaults (n=400, seed=42) in < 3 s.
3. KPIs: smart recovered ₹ > naive; recovery rate lift ≥ 10 pp; smart violations = 0; naive violations > 0.
4. Change seed to 7, Run → numbers change; back to 42 → numbers identical to step 3.
5. Case Explorer → "A hard decline" chip → all retries ✗ with hard-decline reason; last action is PAYMENT_LINK/REMINDER or STOP/ESCALATE.
6. Chip "Insufficient funds (UPI Autopay)" → RETRY_2H ✗ with pre-debit reason; RETRY_SALARY_DAY or RETRY_24H ★.
7. Chip "Transient" → RETRY_2H typically chosen with high sampled P.
8. Decision Intelligence → ACTION_REQUIRED retry posterior means < 0.10 with observations > 0; SOFT RETRY_SALARY_DAY posterior > prior.
9. Human Review → at least one case (default threshold 2500); Approve → state changes; Audit shows `kind=human`; Overview recovered ₹ updates if recovered.
10. Audit Trail → filter "violation only" on smart → empty; toggle naive → rows with `retry_on_hard_decline`.
11. Experiment → 10-seed run completes; sentence shows mean ± SD; all seeds positive lift (report if not).
12. Policy Controls → contact cap 0 → Apply → messages KPI 0; escalate_above 500 → more escalated.
13. Set a fake `GEMINI_API_KEY=xyz`, enable LLM checkbox → outreach shows template with "LLM unavailable"/"failed guardrail"; no crash.
14. Download audit JSON opens and parses.
15. Terminal shows no tracebacks during steps 1–14.

---

## SECTION AB — 3-minute demo flow

| t | Screen | Say / do |
|---|---|---|
| 0:00 | Overview | "Recover. Everything runs on this laptop; no API keys; all outcomes simulated." Point to Revenue at Risk. Click **Run**. |
| 0:20 | Overview | "Same 400 failures, two policies. Naive retries everything every 24h ×3. Recover recovers ₹X more, uses fewer attempts, and—this card—zero constraint violations versus N." |
| 0:45 | Overview chart | "By class: naive wastes three retries on every hard decline; we never retry them. On insufficient funds we wait for salary day." |
| 1:05 | Case Explorer → hard decline chip | "Every retry blocked by a network rule, with the reason. The bandit only saw reminder and link." |
| 1:25 | Chip: insufficient funds UPI Autopay | "RETRY_2H blocked: 24-hour pre-debit notification. RETRY_SALARY_DAY selected with the highest expected value. Here's the draft message—template mode." |
| 1:50 | Decision Intelligence | "This is what it learned online: retries on action-required failures collapsed to ~2%; salary-day retries rose." |
| 2:10 | Human Review | "High-value cases the controller refused to decide alone. Approve." Show outcome. |
| 2:25 | Audit Trail | "Append-only log; every row has the full rationale; download it." |
| 2:40 | Experiment | "Lift holds across 10 seeds: mean ± SD. We claim the architecture, not the numbers." |
| 2:55 | Policy Controls | "Rules build the fence; the bandit chooses inside it. Change the fence, not the code." |

---

## SECTION AC — Hackathon judging strategy

- **Lead with money and safety in the same breath** (KPI row shows both ₹ lift and 0 violations).
- **Pre-empt "where's the AI?"**: the AI is a bandit because decisions must be cheap, auditable, and bounded; the LLM is deliberately confined to wording.
- **Pre-empt "it's simulated"**: open `simulator.py` on request; show `test_boundaries.py`; say the engine changes zero lines if webhooks replace the simulator.
- **Show the fence changing**: live change contact cap or escalation threshold; judges remember interactivity.
- **Show failure tolerance**: enable LLM with no key; app degrades to templates.
- **Show tests**: `pytest -q` output in README and, if allowed, live.
- **Use the honesty slide**: limitations stated by you score better than limitations discovered by them.
- **Keep Track 3 language**: "detect revenue at risk → decide intervention → bounded workflow → recover."

---

## SECTION AD — Known limitations (state them)

1. All payment outcomes are simulated; `hidden_recovery_prob` is hand-authored, not fitted to data.
2. No real Razorpay integration; error codes are modeled, not pulled from the API.
3. Bandit is per failure class, not per customer; no contextual features (bank, BIN, history).
4. `salary_day` is assumed observable; in production it would be an estimate with error.
5. No off-policy evaluation; the benchmark is a simulated A/B, and the 10-seed check measures variance across synthetic datasets only.
6. Naive baseline is intentionally simple; stronger baselines (e.g., Hyperswitch-style rule retries) would narrow the gap.
7. Quiet hours and pre-debit notice are simplified models of regulatory constraints, not legal advice.
8. Single-process, in-memory; state resets on app restart.
9. Costs are illustrative constants.
10. No messaging channel; outreach is drafted, not sent.

---

## SECTION AE — Final repository structure

```
recover/
├── app.py                      # Streamlit console (8 sections, state, CSS)
├── recover/
│   ├── __init__.py             # version
│   ├── simulator.py            # Case, CODES, generate, day_of_month, hidden_recovery_prob (WORLD)
│   ├── policy.py               # arms, costs, delays, controls, allowed_actions, scheduling helpers, check_violations (FENCE)
│   ├── decide.py               # PRIORS, Bandit, decide, explain_rationale (INTELLIGENCE)
│   ├── engine.py               # run, execute_human_action (EXECUTION + AUDIT)
│   ├── metrics.py              # summarize, by_class, confidence (EVIDENCE)
│   └── outreach.py             # templates, draft, validate_rewrite (VOICE, guardrailed)
├── tests/
│   ├── __init__.py
│   ├── test_simulator.py
│   ├── test_policy.py
│   ├── test_decide.py
│   ├── test_engine.py
│   ├── test_metrics.py
│   ├── test_outreach.py
│   └── test_boundaries.py      # proves the hidden-world boundary
├── .streamlit/config.toml      # optional theme
├── requirements.txt
├── .env.example                # GEMINI_API_KEY=   (optional)
├── .gitignore
└── README.md
```

