# ↺ RECOVER — Decline-Aware, Policy-Bounded AI Revenue Recovery

> **Razorpay Buildathon — Track 3: AI Revenue Recovery**  
> *"AI chooses within the fence. Rules build the fence. Every action is measured. Every decision is explainable. Every workflow is bounded."*

---

> [!NOTE]
> **SIMULATION & INTEGRATION TRANSPARENCY NOTICE:**  
> - **100% Local-First & Zero API Keys:** The core application, policy fence, Thompson Sampling AI, bounded workflow, and console run locally without any external credentials or network access.
> - **Simulated Events & Outcomes:** All payment failure events, issuer decline codes, and resolution outcomes are simulated locally. No real money or live payment gateways are touched.
> - **Zero Live Razorpay API Calls in Prototype:** Razorpay webhooks and APIs are mapped conceptually to demonstrate production readiness while ensuring deterministic hackathon reproducibility on a normal laptop.

---

## 1. Executive Summary & One-Line Pitch

**RECOVER** is a policy-bounded AI controller that turns failed recurring payments into recovered revenue by pairing a **deterministic compliance policy engine** with an **online Beta-Thompson Sampling bandit** that maximizes Net Expected Value while guaranteeing zero regulatory or network violations.

---

## 2. Track 3 Alignment (AI Revenue Recovery)

RECOVER directly satisfies the complete Track 3 recovery lifecycle:
```
Revenue at Risk 
  → Decline Diagnosis 
  → Deterministic Policy Fence 
  → Thompson Sampling AI (Net EV) 
  → Bounded Execution Workflow 
  → Measured Money Recovered 
  → Online Bayesian Learning 
  → Compliant Human Escalation 
  → Stopping Rules 
  → Append-Only Audit Trail
```

---

## 3. The Problem with Existing Billing Retries

Subscription billing systems and payment gateways in India (handling UPI Autopay, card recurring mandates, and netbanking) typically default to **naive fixed retries** (e.g. retry every 24 hours × 3). This naive strategy fails catastrophically:

1. **Network Violations:** Reattempting hard declines (revoked mandates, stolen cards) violates payment network rules and incurs merchant penalties.
2. **Regulatory Non-Compliance:** Retrying UPI Autopay without an NPCI 24-hour pre-debit notification causes avoidable declines and bank rejections.
3. **Fee Cannibalization:** Blindly retrying ₹199 payments drains ₹3 gateway fees on near-zero probability attempts, resulting in negative net revenue.
4. **Customer Churn:** Blasting SMS reminders during midnight hours (21:00–09:00) causes spam complaints, friction, and mandate cancellations.
5. **Zero Learning:** The same blind schedule is executed repeatedly regardless of whether the decline was a temporary bank outage or an expired card.

---

## 4. The RECOVER Solution

RECOVER replaces blind retries with a clinical, policy-fenced AI controller:
- **Rules build the fence:** A pure, deterministic policy engine evaluates 8 compliance, regulatory, and merchant rules before the AI is even consulted.
- **AI chooses within the fence:** An online Beta-Thompson Sampling bandit evaluates only legal actions and selects the action with the highest **Net Expected Value ($EV = p \cdot \text{amount} - \text{cost}$)**.
- **Every decision is explainable:** Every case records the exact reason alternative arms were blocked and why the winning action was chosen.
- **Online Bayesian learning:** The AI learns from observed payment outcomes in real time, steering future cases toward higher recovery.
- **Human-in-the-Loop safety net:** High-value cases where automated attempts cease are escalated to human operators with one-click payment link dispatch.

---

## 5. Clear Separation: AI vs Policy Engine

A central principle of RECOVER is the strict architectural separation between **Policy** and **AI**:

| Dimension | Deterministic Policy Engine (The Fence) | Thompson Sampling AI (The Decision) |
|---|---|---|
| **Role** | Determines what actions are **legally allowed** | Chooses the **best economic action** among allowed |
| **Philosophy** | Zero tolerance, safety first, non-probabilistic | Expected value maximization, exploration vs exploitation |
| **Inputs** | Decline code, rail, retry count, time of day, controls | Allowed actions, case amount, action fee, belief posterior |
| **Logic** | Boolean rule evaluation (R1–R8) | Bayesian sampling: $p \sim \text{Beta}(\alpha, \beta)$, $EV = p \cdot \text{amount} - \text{cost}$ |
| **Guarantees** | Zero hard decline retries, zero quiet-hour messages | Maximum net revenue, fee minimization |

```
FAILED PAYMENT
      ↓
FAILURE CLASSIFICATION (10 Codes → 4 Clinical Classes)
      ↓
POLICY SAFETY CHECK (Rules build the fence — R1 to R8)
      ↓
AI / THOMPSON SAMPLING (AI samples EV strictly within permitted options)
      ↓
BEST ALLOWED ACTION (Highest Net Expected Value)
      ↓
BOUNDED WORKFLOW (Event queue, quiet hour deferral, max attempt caps)
      ↓
WORLD OUTCOME (Simulated response)
      ↓
ONLINE LEARNING (α, β posterior updates) + APPEND-ONLY AUDIT TRAIL
```

---

## 6. Mathematical Formulation: Thompson Sampling Bandit

For each failure class $c \in \{\text{SOFT}, \text{TRANSIENT}, \text{ACTION\_REQUIRED}, \text{HARD}\}$ and action arm $a \in \text{ARMS}$, the AI maintains a conjugate Beta prior over the true recovery probability $\theta_{c, a}$:

$$\theta_{c, a} \sim \text{Beta}(\alpha_{c, a}, \beta_{c, a})$$

### Decision Step (Exploration vs Exploitation)
When a case of class $c$ with amount $A$ is evaluated:
1. Filter legal actions: $\mathcal{A}_{\text{allowed}} = \{a \in \text{ARMS} \mid \text{policy\_allowed}(a) = \text{True}\}$.
2. For each legal arm $a \in \mathcal{A}_{\text{allowed}}$:
   - Sample $p_a \sim \text{Beta}(\alpha_{c, a}, \beta_{c, a})$.
   - Compute Net Expected Value: $\text{EV}_a = p_a \cdot A - \text{Cost}(a)$.
3. Select action with maximum positive net yield:
   $$a^* = \arg\max_{a \in \mathcal{A}_{\text{allowed}}} \text{EV}_a \quad (\text{if } \text{EV}_{a^*} > 0)$$
   If no legal action yields positive EV:
   - Escalate to human if $A \ge \text{threshold}$ and $\ge 1$ attempt has been made.
   - Otherwise, safely `STOP` to protect gateway health.

### Bayesian Online Update Step
Upon observing the Bernoulli outcome $y \in \{0, 1\}$ at execution hour $t$:
$$\alpha_{c, a^*} \leftarrow \alpha_{c, a^*} + y$$
$$\beta_{c, a^*} \leftarrow \beta_{c, a^*} + (1 - y)$$
Posterior mean: $\mathbb{E}[\theta_{c, a}] = \frac{\alpha}{\alpha + \beta}$.  
Posterior uncertainty (standard deviation): $\sigma = \sqrt{\frac{\alpha \beta}{(\alpha+\beta)^2(\alpha+\beta+1)}}$.

---

## 7. Clinical Decline Taxonomy (10 Codes, 4 Classes)

| Decline Code | Class | Diagnosis & Strategy |
|---|:---:|---|
| `INSUFFICIENT_FUNDS` | **SOFT** | Customer balance temporarily low. Retrying immediately wastes fees; retry on salary day (10:00 AM). |
| `DO_NOT_HONOR` | **SOFT** | Generic issuer refusal. Cooldown retry or alternate payment method. |
| `ISSUER_UNAVAILABLE` | **TRANSIENT** | Bank core banking system outage. Rapid 2h retry recovers >75% of payments once bank recovers. |
| `UPI_TIMEOUT` | **TRANSIENT** | PSP / NPCI rail timeout. Short cooldown retry recovers without customer friction. |
| `EXPIRED_CARD` | **ACTION_REQUIRED** | Card instrument expired. Reattempts will fail; 1-tap payment link required. |
| `MANDATE_PAUSED` | **ACTION_REQUIRED** | Customer paused autopay mandate in app. Retrying fails; customer notification required. |
| `AUTH_TIMEOUT` | **ACTION_REQUIRED** | Customer didn't enter OTP/PIN in time. Needs customer intervention via link. |
| `MANDATE_REVOKED` | **HARD** | Customer revoked mandate. Network rules strictly forbid reattempts. Stop or send alternate link. |
| `CARD_LOST_STOLEN` | **HARD** | Card flagged lost/stolen. Retrying is a severe network rule violation. |
| `RISK_DECLINE` | **HARD** | Issuer risk decline. Repeated retries damage merchant reputation. |

---

## 8. Deterministic Policy Fence Rules (R1 – R8)

| Rule | Applies To | Condition | Policy Reason String |
|---|---|---|---|
| **R1: Hard Decline Ban** | Retry Arms | `case.failure_class == "HARD"` | `network rule: never reattempt a hard decline ({code})` |
| **R2: UPI Pre-debit Notice** | Retry Arms | `method == "upi_autopay" and delay < 24h` | `UPI Autopay: 24h pre-debit notification required before re-presentment` |
| **R3: Max Retries Cap** | Retry Arms | `case.retries >= max_retries` | `max retries ({max_retries}) reached` |
| **R4: Minimum Retry Gap** | Retry Arms | `earliest_exec - last_retry_at < min_retry_gap_h` | `minimum gap of {g}h between retries not met` |
| **R5: Contact Cap** | Contact Arms | `case.messages >= contact_cap` | `customer contact cap ({cap}) reached` |
| **R6: Quiet Hours Deferral** | Contact Arms | `hour in 21:00..09:00` | Defer execution to 09:00 next day (never blocks, defers) |
| **R7: Recovery Window** | All except STOP | `age_days > recovery_window_days` | `recovery window of {d} days exceeded` |
| **R8: High-Value Escalation** | ESCALATE | `amount >= threshold and len(history) >= 1` | Allowed for high-value cases with prior automated attempt |

---

## 9. Financial Benchmark Results (n=400, Seed 42)

| Metric | Naive Fixed Retry Schedule | RECOVER (Smart Policy) | Net Impact / Lift |
|---|:---:|:---:|:---:|
| **Recovery Rate** | 43.5% | **79.5%** | **+36.0 pp lift** |
| **Gross Recovered Revenue** | ₹330,728.54 | **₹568,848.61** | **+₹238,120.07** |
| **Gateway & Action Fees** | ₹2,805.00 | **₹1,549.50** | **-44.8% fee reduction** |
| **Net Revenue (After Fees)** | ₹327,923.54 | **₹567,299.11** | **+₹239,375.57 net profit** |
| **Total Retry Attempts** | 935 | **438** | **-53.2% fewer attempts** |
| **Revenue per Retry Attempt** | ₹353.72 | **₹1,298.74** | **3.67× higher efficiency** |
| **Cost per ₹1 Recovered** | ₹0.0085 | **₹0.0027** | **68% lower recovery cost** |
| **Policy Violations** | 168 | **0** | **100% compliant (0 violations)** |
| **High-Value Escalations** | 0 (blindly failed) | **20** | **Human safety net active** |

---

## 10. Human-in-the-Loop (HITL)

High-value customer relationships (e.g. amounts $\ge$ ₹2,500) are protected from premature automated abandonment:
- **AI recommends:** Displays the case details, decline diagnosis, recovery probability, expected value, and the recommended 1-tap Payment Link.
- **Human operator actions:**
  - **APPROVE (Send Payment Link):** Dispatches the link immediately and updates case history and audit log.
  - **REJECT (Close Case):** Safely marks case `EXHAUSTED` and logs an operator override in the audit trail.
- All human interventions are recorded with `kind="human"` in the immutable audit trail.

---

## 11. Multi-Seed Validation (10 Seeds, n=400)

To prove that RECOVER's lift is consistent and not cherry-picked from a lucky random seed:
- **Recovery Rate Lift:** **+35.8 ± 2.1 pp** (mean ± SD across 10 independent seeds)
- **Net Revenue Lift:** **+₹236,450 ± ₹14,200**
- **Smart Violations:** **0.0 ± 0.0** across all 10 seeds
- **Naive Violations:** **171.4 ± 12.8** across all 10 seeds

---

## 12. Razorpay Integration Mapping

| RECOVER Concept | Razorpay Platform Surface | Production Implementation |
|---|---|---|
| Failed Payment Event | Webhook: `payment.failed`, `subscription.pending` | Ingest payload, extract error metadata |
| Decline Code Classification | Razorpay `error.code`, `error.reason`, issuer code | Map into 4 clinical taxonomy classes |
| Automated Retry Arms | Razorpay Subscriptions recurring debit retry API | Schedule re-presentment with pre-debit notice |
| Payment Link Arm | Razorpay Payment Links API | Generate 1-tap UPI Intent / Netbanking link |
| Customer Communication | Merchant SMS / WhatsApp / Email gateway | Deliver guardrailed outreach notification |
| Policy Controls | Razorpay Merchant Dashboard settings | Merchant configurable retry & contact caps |
| Audit Trail | Razorpay Merchant Activity & Compliance Log | Append-only event store for dispute audit |

---

## 13. Quickstart & Local Installation

RECOVER runs 100% locally on standard Python 3.10+:

```powershell
# 1. Open project directory
cd c:\My_Projects\Razorpay_Buildthon

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run automated tests (49 unit and boundary tests)
python -m pytest -q

# 4. Launch the Revenue Operations Console
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 14. 3-Minute Hackathon Demo Script

| Time | Screen | Demo Narration & Action |
|:---:|:---:|---|
| **0:00** | **Overview** | "Welcome to RECOVER. Everything runs locally on standard Python with zero API keys required. We process 400 realistic payment failures. Point to the KPI row: RECOVER achieves **79.5% recovery** vs 43.5% naive, delivering **₹239,375 net lift** with **zero policy violations**." |
| **0:45** | **Benchmark Charts** | "Look at the unit economics: naive schedules waste 900+ attempts retrying hard declines. RECOVER cuts retries by 53%, recovering transient outages rapidly and waiting for salary day on insufficient funds." |
| **1:10** | **Case Explorer** | "Click chip **⚡ Hard Decline (R1)**. In the card **'WHY DID AI CHOOSE THIS ACTION?'**, all retries are blocked by Rule R1. The Thompson Sampling bandit was only permitted to send a Payment Link. Real-time probabilities, EV, and Bayesian observations are displayed." |
| **1:40** | **UPI Autopay Chip** | "Click **⚡ UPI Autopay Pre-debit (R2)**. `RETRY_2H` is blocked by NPCI's 24h pre-debit notice rule. The AI selects `RETRY_SALARY_DAY` with the highest net EV." |
| **2:05** | **Decision Intelligence** | "In Decision Intelligence, look at the Before vs After learning charts. The bandit observed recovery outcomes online: retries on `ACTION_REQUIRED` collapsed toward 2%, while `RETRY_SALARY_DAY` on `SOFT` rose." |
| **2:25** | **Human Review** | "High-value cases (₹2,500+) are routed to Human Review. The AI recommends a payment link; the operator can click **APPROVE** or **REJECT**. Everything updates the audit log." |
| **2:45** | **Policy & Experiment** | "In Policy & Safety, see our 8 active rules. In Experiment, our 10-seed check proves a consistent +35.8 pp lift across independent cohorts. In Razorpay Mapping, see how this plugs directly into Razorpay webhooks." |

---

## 15. Repository Structure

```
c:\My_Projects\Razorpay_Buildthon\
├── app.py                      # 10-Screen Streamlit Revenue Operations Console
├── recover/
│   ├── __init__.py             # Package version 1.0.0
│   ├── simulator.py            # Case dataclass, 10-code taxonomy, seeded generation, ground truth
│   ├── policy.py               # Deterministic safety fence, allowed_actions, independent auditor
│   ├── decide.py               # Beta-Thompson Sampling bandit, Bayesian statistics, explainability
│   ├── engine.py               # Priority event queue, bounded execution loop, HITL executor
│   ├── metrics.py              # Financial summarizer, efficiency metrics, 10-seed confidence check
│   └── outreach.py             # Deterministic templates, multi-tier guardrails, optional Gemini rewrite
├── tests/
│   ├── __init__.py
│   ├── test_simulator.py       # Domain and ground-truth boundary tests (7 tests)
│   ├── test_policy.py          # Deterministic policy rules R1-R8, quiet hours, salary math (12 tests)
│   ├── test_decide.py          # Invariant tests, EV logic, online learning (7 tests)
│   ├── test_engine.py          # Loop termination, 0 smart violations, audit schema, HITL (7 tests)
│   ├── test_metrics.py         # Financial math, summary edge cases, confidence schema (4 tests)
│   ├── test_outreach.py        # Template generation, guardrail validation, fallback modes (4 tests)
│   ├── test_boundaries.py      # AST/source check proving hidden world isolation from decision code (3 tests)
│   └── test_enhanced_features.py # Tests for AI stats, uncertainty, financial efficiency, HITL reject (5 tests)
├── .streamlit/
│   └── config.toml             # Custom theme styling (primaryColor #2563EB)
├── requirements.txt            # Python dependencies (Streamlit, Pandas, Pytest, google-generativeai)
├── .env.example                # Optional environment file
├── .gitignore                  # Git hygiene
└── README.md                   # Complete architectural documentation
```

---

## 16. Known Limitations & Scientific Honesty

1. **Simulation Fidelity:** All payment outcomes are generated via parameterized synthetic response curves (`hidden_recovery_prob`). While modeled after Indian payment patterns, they are not calibrated to proprietary production bank data.
2. **Class-Level Bandit:** The Thompson Sampling bandit models beliefs per `(failure_class, arm)`. In production, contextual bandits would incorporate customer LTV, issuing bank, card bin, and historical debit hours.
3. **No Live Payment Rails in Prototype:** The prototype is intentionally self-contained to ensure anyone can clone and run it in 30 seconds without creating merchant accounts or generating credentials.
4. **No Real Customer Messaging Sent:** Customer outreach is drafted and guardrailed, but not transmitted over real cellular networks.
5. **Regulatory Simplifications:** Quiet hours (21:00–09:00) and UPI Autopay 24h pre-debit notices are modeled as engineering constraints, not formal legal advice.
