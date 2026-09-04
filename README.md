# ↺ RECOVER — Decline-Aware, Policy-Bounded AI Revenue Recovery

> **Razorpay Buildathon — Track 3: AI Revenue Recovery**  
> *"AI chooses within the fence. Rules build the fence. Every action is measured. Every decision is explainable. Every workflow is bounded."*

---

> [!IMPORTANT]
> **This prototype uses a local Razorpay-shaped mock integration. No real payments are processed.**  
> Inspired by the architecture of `stripe-mock` and standard fintech webhook gateways, RECOVER runs 100% locally on your laptop with **ZERO external API keys, ZERO live credentials, and ZERO live network dependencies**.

---

## 1. Project Overview

**RECOVER** is an intelligent, policy-bounded revenue recovery engine designed for subscription merchants, SaaS platforms, and recurring billing systems in India (handling UPI Autopay, recurring cards, and netbanking).

When recurring debits fail, merchants face a critical dilemma:
- **Blind naive retries** violate payment network rules, incur gateway fees, annoy customers, and trigger bank declines.
- **Premature abandonment** surrenders recoverable revenue and accelerates involuntary subscriber churn.

RECOVER solves this with a **bifurcated architecture**:
1. **The Fence (Deterministic Policy Engine):** Enforces 8 strict regulatory, network, and merchant safety rules (RBI mandate rules, NPCI 24h pre-debit notices, cooldowns, contact caps, quiet hours). Blocked actions are completely disallowed.
2. **The Decision (Thompson Sampling AI):** Within permitted actions, an online Bayesian Beta-Bernoulli multi-armed bandit samples conversion probabilities and optimizes for **Net Expected Value** ($EV = p \cdot \text{amount} - \text{cost}$).
3. **The Integration (Local Mock Razorpay & Idempotency Layer):** Ingests realistic Razorpay webhooks, protects against duplicate execution via SQLite idempotency, executes recovery actions against a mock Razorpay API, and learns online from observed payment outcomes.

---

## 2. End-to-End Pipeline Architecture Diagram

```
                       INCOMING FAILURE EVENT
                                 │
                     Razorpay Webhook (payment.failed)
                                 │
                                 ▼
                     SQLITE IDEMPOTENCY GATE
              (UNIQUE event_id check + Thread Lock)
                                 │
               ┌─────────────────┴─────────────────┐
       Duplicate Event                     New Unique Event
               │                                   │
               ▼                                   ▼
      Return Cached Result               FAILURE CLASSIFICATION
      (0 Re-executions)             (10 Codes → 4 Clinical Classes)
                                                   │
                                                   ▼
                                         POLICY SAFETY FENCE
                                     (Deterministic Rules R1 to R8)
                                                   │
                                                   ▼
                                          THOMPSON SAMPLING AI
                                    (Samples p ~ Beta(α, β) per arm)
                                                   │
                                                   ▼
                                      EXPECTED VALUE OPTIMIZATION
                                       (Argmax EV = p · amount - fee)
                                                   │
                                                   ▼
                                        BOUNDED WORKFLOW ACTION
                                                   │
                      ┌────────────────────────────┼────────────────────────────┐
                      ▼                            ▼                            ▼
             MOCK RAZORPAY RETRY           PAYMENT LINK ARM             HUMAN ESCALATION
         (POST /v1/subscriptions/retry)  (POST /v1/payment_links)     (Amounts ≥ ₹10,000)
                      │                            │                            │
                      └────────────────────────────┼────────────────────────────┘
                                                   ▼
                                         MOCK PAYMENT OUTCOME
                                       (captured vs failed)
                                                   │
                                                   ▼
                                        ONLINE BANDIT LEARNING
                                      (Posterior α, β updates)
                                                   │
                                                   ▼
                                        IMMUTABLE AUDIT TRAIL
                                    + FINANCIAL EFFICIENCY REPORT
```

---

## 3. Local Mock Razorpay API Integration

The `recover/mock_razorpay.py` module acts as a realistic, local payment provider API boundary. It emulates Razorpay's recurring billing and payment link APIs without live network calls:

| Action / Endpoint | Mock Implementation | Simulated Payload Returned |
|---|---|---|
| **Recurring Debit Retry** | `MockRazorpay.retry_payment()` | `{"id": "pay_mock_...", "entity": "payment", "status": "captured"|"failed", "amount": 149900, "currency": "INR", "method": "card", "simulated": true}` |
| **Payment Link Creation** | `MockRazorpay.create_payment_link()` | `{"id": "plink_mock_...", "entity": "payment_link", "status": "created", "short_url": "https://mock.razorpay.local/plink/...", "simulated": true}` |
| **Customer Notification** | `MockRazorpay.send_recovery_notification()` | `{"id": "notif_mock_...", "entity": "notification", "channel": "whatsapp", "status": "sent", "simulated": true}` |
| **Payment Resolution** | `MockRazorpay.resolve_payment()` | `{"id": "pay_mock_...", "status": "captured", "recovered": true, "simulated": true}` |
| **High-Value Escalation** | `MockRazorpay.escalate_payment()` | `{"id": "pay_mock_...", "status": "escalated_to_human", "reason": "...", "simulated": true}` |

---

## 4. Webhook Delivery Flow & Event Schema

RECOVER ingests canonical Razorpay webhook payloads. Events can be generated individually or in batches via `WebhookSimulator`:

```json
{
  "entity": "event",
  "account_id": "acc_mock_merchant_001",
  "event_id": "evt_mock_1a2b3c4d",
  "event": "payment.failed",
  "event_type": "payment.failed",
  "payment_id": "pay_mock_9f8e7d6c",
  "amount": 1499.00,
  "method": "card",
  "error_code": "INSUFFICIENT_FUNDS",
  "timestamp": 1725451200,
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_mock_9f8e7d6c",
        "amount": 149900,
        "currency": "INR",
        "status": "failed",
        "method": "card",
        "error_code": "INSUFFICIENT_FUNDS",
        "error_description": "Payment failed due to INSUFFICIENT_FUNDS",
        "error_source": "issuing_bank",
        "error_step": "payment_authorization",
        "error_reason": "insufficient_funds",
        "created_at": 1725451200
      }
    }
  },
  "simulated": true
}
```

---

## 5. SQLite Idempotency Layer Design

In payment recovery, duplicate webhook deliveries are standard (network timeouts, PSP retries, concurrent deliveries). Without idempotency, a merchant risks **double-charging customers, spamming duplicate SMS messages, or running duplicate retries**.

RECOVER features a robust, thread-safe `IdempotencyStore` built on local SQLite:

- **Database Table:** `webhook_idempotency`
  - `event_id TEXT PRIMARY KEY` (Unique constraint)
  - `payment_id TEXT`
  - `event_type TEXT`
  - `status TEXT` (`PROCESSING`, `PROCESSED`, `DUPLICATE_BLOCKED`, `FAILED`)
  - `action_taken TEXT`
  - `result_json TEXT` (Cached response payload)
  - `duplicate_count INTEGER`
  - `created_at TEXT`, `processed_at TEXT`
- **Concurrency & Race Condition Protection:**
  - Uses `threading.Lock()` and SQLite atomic transactions (`BEGIN IMMEDIATE`).
  - When an `event_id` is received, RECOVER checks for existence:
    - **If found:** Increments `duplicate_count`, returns the cached JSON result immediately, and triggers **zero recovery actions**.
    - **If new:** Inserts with status `PROCESSING`, executes the AI/Policy pipeline, updates status to `PROCESSED` with serialized output, and returns the fresh receipt.

---

## 6. AI Decision Flow & Mathematical Formulation

### Conjugate Beta Prior
For each failure class $c \in$ {`SOFT`, `TRANSIENT`, `ACTION_REQUIRED`, `HARD`} and action arm $a \in \mathcal{A}$, the AI maintains a conjugate Beta prior over the true recovery probability $\theta_{c, a}$:

$$\theta_{c, a} \sim \text{Beta}(\alpha_{c, a}, \beta_{c, a})$$

### Decision Step (Exploration vs Exploitation)
When an eligible case of class $c$ with amount $A$ is evaluated:
1. **Filter legal actions permitted by the policy safety fence:**
   $$\mathcal{A}_{\text{allowed}} = \{a \in \mathcal{A} \mid \text{allowed}(a) = \text{true}\}$$
2. **For each legal arm $a \in \mathcal{A}_{\text{allowed}}$:**
   - Sample conversion probability: $p_a \sim \text{Beta}(\alpha_{c, a}, \beta_{c, a})$
   - Compute Net Expected Value: $\text{EV}_a = p_a \cdot A - \text{Cost}(a)$
3. **Select action with maximum positive net yield:**
   $$a^* = \arg\max_{a \in \mathcal{A}_{\text{allowed}}} \text{EV}_a \quad (\text{if } \text{EV}_{a^*} > 0)$$
   If no legal action yields positive EV:
   - Escalate to human review if amount $A \ge \text{threshold}$ and $\ge 1$ prior attempt was made.
   - Otherwise, safely `STOP` to protect gateway health and customer trust.

### Bayesian Online Learning Step
Upon observing the Bernoulli outcome $y \in \{0, 1\}$ from the mock payment provider:
$$\alpha_{c, a^*} \leftarrow \alpha_{c, a^*} + y$$
$$\beta_{c, a^*} \leftarrow \beta_{c, a^*} + (1 - y)$$
- Posterior Mean: $\mathbb{E}[\theta_{c, a}] = \frac{\alpha}{\alpha + \beta}$
- Posterior Uncertainty (Standard Deviation): $\sigma = \sqrt{\frac{\alpha \beta}{(\alpha+\beta)^2(\alpha+\beta+1)}}$

---

## 7. Deterministic Policy Safety Rules (R1 – R8)

Rules build the fence. AI chooses within the fence.

| Rule | Applies To | Condition | Policy Safety Invariant |
|---|---|---|---|
| **R1: Hard Decline Ban** | Retry Arms | `case.failure_class == "HARD"` | Never reattempt a hard decline (`MANDATE_REVOKED`, `CARD_LOST_STOLEN`). |
| **R2: UPI Pre-debit Notice** | Retry Arms | `method == "upi_autopay" and delay < 24h` | NPCI rule: 24h pre-debit notification required before re-presentment. |
| **R3: Max Retries Cap** | Retry Arms | `case.retries >= max_retries` | Strict ceiling on automated retry attempts (default: 4). |
| **R4: Minimum Retry Gap** | Retry Arms | `earliest_exec - last_retry_at < min_retry_gap_h` | Enforces minimum spacing between retry attempts (default: 2h). |
| **R5: Contact Cap** | Contact Arms | `case.messages >= contact_cap` | Prevents customer spam (max 2 messages per incident). |
| **R6: Quiet Hours Deferral** | Contact Arms | `hour in 21:00..09:00` | Defers outreach to 09:00 next morning (never disturbs customers at night). |
| **R7: Recovery Window** | All except STOP | `age_days > recovery_window_days` | Stops actions once invoice is older than recovery window (default: 30 days). |
| **R8: High-Value Escalation** | ESCALATE | `amount >= threshold and len(history) >= 1` | Routes high-value accounts (≥ ₹10,000) to Human Review with AI guidance. |

---

## 8. Failure Injection & Reliability Lab

Screen 11 (**⚡ Reliability & Integration Lab**) in the console allows live testing of edge cases and fault injection:

- **`[⚡ payment.failed]`**: Ingests and processes a single realistic webhook event.
- **`[🔁 10 Duplicates]`**: Generates 10 identical webhook calls simultaneously to verify the idempotency invariant:
  - **10 Received**
  - **1 Processed**
  - **9 Blocked**
  - **1 Actual Execution**
  - **0 Duplicate Executions**
  - **0 Idempotency Violations**
- **`[⚡ Concurrent Blast]`**: Fires 10 duplicate events across 5 concurrent worker threads (`ThreadPoolExecutor`), proving thread safety and zero race conditions under high concurrency.
- **`[⚠️ Force Failure]`**: Simulates an issuer gateway timeout (503), demonstrating how RECOVER logs execution failures and plans follow-up attempts within policy constraints.
- **`[⏳ Stale Webhook]`**: Delivers an event past the 30-day recovery window, proving that Policy Rule R7 terminates the case with `STOP`.

---

## 9. Benchmark & Performance Results

### Executive Comparison (n=400, Seed 42)

| Metric | Naive Fixed Retry Schedule | RECOVER (Smart Policy) | Net Impact / Lift |
|---|:---:|:---:|:---:|
| **Recovery Rate** | 43.5% | **79.5%** | **+36.0 pp lift** |
| **Gross Recovered Revenue** | ₹330,728.54 | **₹568,848.61** | **+₹238,120.07** |
| **Gateway & Action Fees** | ₹2,805.00 | **₹1,549.50** | **-44.8% fee reduction** |
| **Net Revenue (After Fees)** | ₹327,923.54 | **₹567,299.11** | **+₹239,375.57 net profit** |
| **Total Retry Attempts** | 935 | **438** | **-53.2% fewer attempts** |
| **Revenue per Retry Attempt** | ₹353.72 | **₹1,298.74** | **3.67× higher efficiency** |
| **Cost per Recovered ₹100** | ₹0.85 | **₹0.27** | **68.2% cost reduction** |
| **Policy Violations** | 168 | **0** | **100% compliant (0 violations)** |
| **High-Value Escalations** | 0 (blindly failed) | **20** | **Human safety net active** |

### Multi-Seed Stability (10 Independent Seeds, n=400)
- **Recovery Rate Lift:** **+35.8 ± 2.1 pp**
- **Net Revenue Lift:** **+₹236,412 ± ₹14,890**
- **Policy Violations:** **0.0 ± 0.0** (vs 168.4 ± 8.2 in naive retries)

---

## 10. Automated Test Results

The project includes an extensive automated test suite covering unit math, policy rules, boundary isolation, SQLite idempotency, and concurrent failure injection:

```powershell
python -m pytest -q
...........................................................              [100%]
59 passed in 1.97s
```

### Safety & Boundary Proofs
1. **AST Boundary Isolation (`tests/test_boundaries.py`)**: Asserts that `recover/policy.py` and `recover/decide.py` contain zero references to `hidden_recovery_prob` or `responsiveness`.
2. **Policy Invariant (`tests/test_decide.py`)**: 1,000 iterations prove the AI never selects an arm blocked by `allowed_actions()`.
3. **Idempotency Guarantee (`tests/test_mock_razorpay.py`)**: Tests 10 duplicate events and multithreaded concurrent blasts to prove that recovery actions execute at most once per `event_id`.
4. **Hard Decline Network Rule (`tests/test_mock_razorpay.py`)**: Proves retries are strictly blocked on hard decline webhook events.

---

## 11. Quickstart & How to Run Locally

RECOVER runs 100% locally on standard Python 3.10+:

```powershell
# 1. Clone repository
git clone https://github.com/ArjunCoder0/recover-ai-revenue-recovery.git
cd recover-ai-revenue-recovery

# 2. Install minimal dependencies
pip install -r requirements.txt

# 3. Run automated test suite (59 unit, boundary, and idempotency tests)
python -m pytest -q

# 4. Launch the Streamlit Revenue Operations Console
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 12. What is Simulated vs What Would Be Replaced in Production

| Component | Prototype (Local Mock) | Production Replacement |
|---|---|---|
| **Webhook Delivery** | `WebhookSimulator` generating local JSON payloads | Razorpay Webhook endpoint (`POST /webhooks/razorpay`) with secret signature verification (`X-Razorpay-Signature`) |
| **Idempotency Storage** | Local SQLite database (`recover_idempotency.db`) | Distributed Redis / PostgreSQL table with distributed lock or `ON CONFLICT DO NOTHING` |
| **Payment Retry Action** | `MockRazorpay.retry_payment()` | Razorpay Subscriptions API: `POST /v1/subscriptions/{sub_id}/retry` or recurring debit re-presentment |
| **Payment Link Action** | `MockRazorpay.create_payment_link()` | Razorpay Payment Links API: `POST /v1/payment_links` with customer contact and auto-expiry |
| **Customer Messaging** | Guardrailed templated text (optional Gemini rewrite) | WhatsApp Business API / SMS gateway (Twilio, Gupshup, Kaleyra) |
| **Bank Resolution Outcomes** | Parameterized realistic response curve | Real banking network responses (NPCI, Visa, Mastercard, Issuer Core Banking) |

---

## 13. Repository Structure

```
c:\My_Projects\Razorpay_Buildthon\
├── app.py                      # 11-Screen Streamlit Revenue Operations Console
├── recover/
│   ├── __init__.py             # Package exports (v1.1.0)
│   ├── mock_razorpay.py        # Local Mock Razorpay API, Webhook Simulator & SQLite Idempotency Store
│   ├── simulator.py            # Case dataclass, 10-code clinical taxonomy, synthetic generation
│   ├── policy.py               # Deterministic safety fence (R1–R8), allowed_actions, independent auditor
│   ├── decide.py               # Beta-Thompson Sampling bandit, Bayesian statistics, explainability
│   ├── engine.py               # Priority event queue, bounded execution loop, HITL executor
│   ├── metrics.py              # Financial summarizer, efficiency unit economics, 10-seed confidence
│   └── outreach.py             # Deterministic templates, multi-tier guardrails, optional Gemini rewrite
├── tests/
│   ├── test_simulator.py       # Domain and ground-truth boundary tests (7 tests)
│   ├── test_policy.py          # Deterministic policy rules R1-R8, quiet hours, salary math (12 tests)
│   ├── test_decide.py          # Invariant tests, EV logic, online learning (7 tests)
│   ├── test_engine.py          # Loop termination, 0 smart violations, audit schema, HITL (7 tests)
│   ├── test_metrics.py         # Financial math, summary edge cases, confidence schema (4 tests)
│   ├── test_outreach.py        # Template generation, guardrail validation, fallback modes (4 tests)
│   ├── test_boundaries.py      # AST/source check proving hidden world isolation from decision code (2 tests)
│   ├── test_enhanced_features.py # Tests for AI stats, uncertainty, financial efficiency, HITL reject (5 tests)
│   └── test_mock_razorpay.py   # Tests for mock API, 10 duplicates, concurrency, idempotency (11 tests)
├── .streamlit/
│   └── config.toml             # Custom theme styling (primaryColor #2563EB)
├── requirements.txt            # Python dependencies (Streamlit, Pandas, Pytest, google-generativeai)
├── .env.example                # Optional environment file (zero keys required)
├── .gitignore                  # Git hygiene (ignores *.db, *.sqlite3, pycache, venv)
└── README.md                   # Complete architectural documentation & judging guide
```
