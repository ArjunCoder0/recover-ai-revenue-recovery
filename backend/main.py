"""FastAPI REST API Server for the RECOVER Revenue Recovery Console.

Exposes endpoints for:
- Simulation state, run triggers, and financial KPIs
- Individual case exploration, explainability ("Why AI Chose This"), and outreach previews
- Multi-Armed Bandit (Thompson Sampling) beliefs, win rates, and priors/posteriors
- Policy Fence rules (R1-R8) and interactive merchant controls
- Local Mock Razorpay reliability lab, SQLite idempotency, and 10-duplicate blast tests
- Human-in-the-Loop review queue and manual interventions
- Append-only audit trail and benchmark comparisons
- Failure class taxonomy and Razorpay integration mapping
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    SimulationRequest,
    SimulationStateResponse,
    OverviewKPIs,
    CasesResponse,
    CaseDetailResponse,
    DecisionIntelligenceResponse,
    HumanActionRequest,
    ReliabilityStats,
    BlastTestRequest,
    BlastTestResponse,
    SimulateWebhookRequest,
    BenchmarkRequest,
    BenchmarkResponse,
)
from .state import state
from recover.policy import (
    DEFAULT_CONTROLS,
    validate_controls,
)

HARD_RULES = [
    {
        "id": "R1",
        "name": "Hard Decline Ban",
        "status": "ACTIVE ✓",
        "applies_to": "Retry Arms",
        "condition": "Failure class is HARD",
        "policy_action": "Hard declines (stolen cards, revoked mandates) are NEVER retried. Fulfills network compliance.",
    },
    {
        "id": "R2",
        "name": "UPI Pre-Debit Notice",
        "status": "ACTIVE ✓",
        "applies_to": "Retry Arms",
        "condition": "Method is upi_autopay and delay < 24h",
        "policy_action": "Mandatory 24h pre-debit notice before re-presentment. Complies with NPCI regulations.",
    },
    {
        "id": "R3",
        "name": "Max Retries Cap",
        "status": "ACTIVE ✓",
        "applies_to": "Retry Arms",
        "condition": "Attempts >= Max Retries setting",
        "policy_action": "Blocks further automated retries to protect merchant gateway health.",
    },
    {
        "id": "R4",
        "name": "Minimum Retry Gap",
        "status": "ACTIVE ✓",
        "applies_to": "Retry Arms",
        "condition": "Execution gap < 2 hours",
        "policy_action": "Enforces cooldown between retries, avoiding immediate repeated gateway decline fees.",
    },
    {
        "id": "R5",
        "name": "Contact Cap",
        "status": "ACTIVE ✓",
        "applies_to": "Contact Arms",
        "condition": "Messages >= Contact Cap setting",
        "policy_action": "Caps total SMS/WhatsApp reminders to prevent customer notification fatigue and spam.",
    },
    {
        "id": "R6",
        "name": "Quiet Hours Deferral",
        "status": "ACTIVE ✓",
        "applies_to": "Contact Arms",
        "condition": "Hour falls in 21:00 – 09:00",
        "policy_action": "Automatically defers message dispatch to 09:00 the following morning. Never disturbs users at night.",
    },
    {
        "id": "R7",
        "name": "Recovery Window",
        "status": "ACTIVE ✓",
        "applies_to": "All except STOP",
        "condition": "Case age > Recovery Window",
        "policy_action": "Closes stale recovery pipelines past the merchant window (default 30 days).",
    },
    {
        "id": "R8",
        "name": "High-Value Escalation",
        "status": "ACTIVE ✓",
        "applies_to": "ESCALATE",
        "condition": "Amount >= Threshold and >=1 prior attempt",
        "policy_action": "Routes valuable customer relationships to human operators rather than giving up.",
    },
]

app = FastAPI(
    title="RECOVER API",
    description="Decline-Aware, Policy-Bounded AI Revenue Recovery Console for Razorpay",
    version="1.0.0",
)

# CORS middleware for local Vite frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint confirming local mock mode operation."""
    return {
        "status": "healthy",
        "mock_mode": True,
        "mock_provider": "Razorpay Local Simulator",
        "version": "1.0.0",
    }


@app.get("/api/simulation/state", response_model=SimulationStateResponse)
def get_simulation_state() -> Dict[str, Any]:
    """Returns current active simulation parameters and high-level KPIs."""
    kpis = state.get_kpis()
    return {
        "n": state.n,
        "seed": state.seed,
        "controls": state.controls,
        "kpis": kpis,
        "total_cases": len(state.smart_cases),
        "mock_mode": True,
    }


@app.post("/api/simulation/run", response_model=SimulationStateResponse)
def run_simulation(req: SimulationRequest) -> Dict[str, Any]:
    """Executes a new simulation run with specified batch size, seed, and controls."""
    state.run_simulation(
        n=req.n,
        seed=req.seed,
        controls=req.controls,
        llm=req.llm,
    )
    kpis = state.get_kpis()
    return {
        "n": state.n,
        "seed": state.seed,
        "controls": state.controls,
        "kpis": kpis,
        "total_cases": len(state.smart_cases),
        "mock_mode": True,
    }


@app.get("/api/cases", response_model=CasesResponse)
def get_cases(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    failure_class: Optional[str] = Query(default=None),
    state_filter: Optional[str] = Query(default=None, alias="state"),
    search: Optional[str] = Query(default=None),
    min_amount: Optional[float] = Query(default=None),
    max_amount: Optional[float] = Query(default=None),
    risk_min: Optional[float] = Query(default=None),
) -> Dict[str, Any]:
    """Returns filtered and paginated cases from the current simulation."""
    items, total = state.get_cases(
        page=page,
        page_size=page_size,
        failure_class=failure_class,
        state=state_filter,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
        risk_min=risk_min,
    )
    return {
        "cases": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/cases/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(case_id: int) -> Dict[str, Any]:
    """Returns detailed explainability, alternatives considered, and outreach message for a case."""
    detail = state.get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Case #{case_id} not found.")
    return detail


@app.get("/api/decision-intelligence", response_model=DecisionIntelligenceResponse)
def get_decision_intelligence() -> Dict[str, Any]:
    """Returns Bayesian belief distributions (Beta alpha, beta) and arm statistics."""
    return state.get_decision_intelligence()


@app.get("/api/policy/controls")
def get_policy_controls() -> Dict[str, Any]:
    """Returns current active policy controls alongside R1-R8 rule specifications."""
    return {
        "controls": state.controls,
        "hard_rules": HARD_RULES,
    }


@app.post("/api/policy/controls")
def update_policy_controls(controls: Dict[str, Any]) -> Dict[str, Any]:
    """Validates and updates merchant policy controls, refreshing active simulation."""
    try:
        validated = validate_controls(controls)
        state.controls = validated
        # Re-run simulation with updated controls
        state.run_simulation(state.n, state.seed, state.controls, state.llm)
        return {
            "success": True,
            "controls": state.controls,
            "message": "Policy controls updated and simulation refreshed.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/reliability/stats", response_model=ReliabilityStats)
def get_reliability_stats() -> Dict[str, Any]:
    """Returns current statistics from the local SQLite idempotency table."""
    return state.rel_store.get_stats()


@app.get("/api/reliability/events")
def get_reliability_events() -> List[Dict[str, Any]]:
    """Returns recent webhook events processed through the local pipeline."""
    return state.rel_events_log


@app.post("/api/reliability/blast-test", response_model=BlastTestResponse)
def run_blast_test(req: BlastTestRequest) -> Dict[str, Any]:
    """Simulates a concurrent burst of N duplicate webhooks (e.g. 10 requests).

    Proves idempotency: exactly 1 processed, N-1 blocked, 0 duplicate debit attempts.
    """
    return state.run_duplicate_blast(
        event_id=req.event_id,
        count=req.count,
        error_code=req.error_code,
        amount=req.amount,
    )


@app.post("/api/reliability/simulate-webhook")
def simulate_webhook(req: SimulateWebhookRequest) -> Dict[str, Any]:
    """Simulates an individual incoming payment failure webhook from Mock Razorpay."""
    return state.simulate_single_webhook(
        event_type=req.event_type,
        error_code=req.error_code,
        amount=req.amount,
        method=req.method,
        customer_phone=req.customer_phone,
        customer_email=req.customer_email,
    )


@app.post("/api/reliability/reset")
def reset_reliability() -> Dict[str, Any]:
    """Clears the SQLite idempotency store and local event memory."""
    state.rel_store.clear()
    with state._lock:
        state.rel_events_log.clear()
    return {"success": True, "message": "Idempotency store reset successfully."}


@app.get("/api/human-review/queue")
def get_human_review_queue() -> List[Dict[str, Any]]:
    """Returns the prioritized queue of cases flagged for human review."""
    return state.get_human_queue()


@app.post("/api/human-review/action")
def execute_human_action(req: HumanActionRequest) -> Dict[str, Any]:
    """Applies a human reviewer's approval, rejection, or custom action."""
    try:
        res = state.execute_human_review(
            case_id=req.case_id,
            action=req.action,
            note=req.note,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit-trail")
def get_audit_trail(
    case_id: Optional[int] = Query(default=None),
    arm: Optional[str] = Query(default=None),
    violation_only: bool = Query(default=False),
    policy: str = Query(default="smart"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    """Returns append-only audit trail logs with filtering and pagination."""
    logs, total = state.get_audit_trail(
        case_id=case_id,
        arm=arm,
        violation_only=violation_only,
        policy=policy,
        page=page,
        page_size=page_size,
    )
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/audit-trail/export")
def export_audit_trail(policy: str = "smart") -> Any:
    """Exports all audit trail entries as JSON."""
    logs, _ = state.get_audit_trail(policy=policy, page=1, page_size=10000)
    return logs


@app.post("/api/benchmarks/run", response_model=BenchmarkResponse)
def run_benchmarks(req: BenchmarkRequest) -> Dict[str, Any]:
    """Executes multi-seed benchmarks across seeds to demonstrate statistical lift."""
    return state.run_benchmark(seeds=req.seeds, n=req.n)


@app.get("/api/taxonomy")
def get_taxonomy() -> Dict[str, Any]:
    """Returns failure class taxonomy, error code mappings, and clinical recovery playbooks."""
    return {
        "classes": {
            "SOFT": {
                "name": "Soft Decline",
                "description": "Instrument valid, funds temporarily absent. Timing retry around salary day is key.",
                "retry_policy": "Permitted with exponential backoff / salary alignment",
                "codes": ["INSUFFICIENT_FUNDS", "DO_NOT_HONOR"],
                "badge_color": "blue",
            },
            "TRANSIENT": {
                "name": "Transient Failure",
                "description": "Temporary network or issuer outage. Short-delay retry recovers reliably once systems recover.",
                "retry_policy": "Permitted with short cooldown (2h - 24h)",
                "codes": ["ISSUER_UNAVAILABLE", "UPI_TIMEOUT"],
                "badge_color": "amber",
            },
            "ACTION_REQUIRED": {
                "name": "Customer Action Required",
                "description": "Instrument unusable or mandate paused. Retries futile; customer action via payment link required.",
                "retry_policy": "Direct retries BLOCKED; customer must provide new payment method or auth",
                "codes": ["EXPIRED_CARD", "MANDATE_PAUSED", "AUTH_TIMEOUT"],
                "badge_color": "purple",
            },
            "HARD": {
                "name": "Hard Decline",
                "description": "Mandate revoked or card stolen. Network rules forbid reattempts; payment link or closure only.",
                "retry_policy": "STRICT ZERO RETRY. Retrying is an RBI / card network violation.",
                "codes": ["MANDATE_REVOKED", "CARD_LOST_STOLEN", "RISK_DECLINE"],
                "badge_color": "rose",
            },
        },
        "code_meanings": {
            "INSUFFICIENT_FUNDS": "Customer balance insufficient. Immediate retries waste gateway fees; align with salary day.",
            "DO_NOT_HONOR": "Generic refusal by issuer. Retrying later or offering alternate rails succeeds.",
            "ISSUER_UNAVAILABLE": "Bank system offline. High recovery probability after brief cooldown.",
            "UPI_TIMEOUT": "PSP or NPCI timeout. Transient network glitch on UPI Autopay rail.",
            "EXPIRED_CARD": "Card expired. Re-presentment will fail; customer must update credentials or pay via link.",
            "MANDATE_PAUSED": "Customer paused mandate in app. Automated debit blocked until user unpauses.",
            "AUTH_TIMEOUT": "Customer failed to complete authentication (OTP/PIN). Customer action required.",
            "MANDATE_REVOKED": "Customer cancelled mandate. Any automated retry is a regulatory violation.",
            "CARD_LOST_STOLEN": "Card flagged as lost/stolen. Network rules strictly prohibit reattempts.",
            "RISK_DECLINE": "Declined by risk rules. Retrying damages merchant standing with payment networks.",
        },
    }


@app.get("/api/integration-map")
def get_integration_map() -> Dict[str, Any]:
    """Returns Razorpay API endpoints, webhook subscriptions, and production architecture mapping."""
    return {
        "webhook_events": [
            {
                "event": "payment.failed",
                "trigger": "Recurring auto-debit or initial payment fails at gateway",
                "handled_by": "MockRazorpayPipeline.process_webhook",
                "action": "Diagnose failure class, verify policy fence, calculate arm EV",
            },
            {
                "event": "payment_link.paid",
                "trigger": "Customer completes payment via Razorpay Payment Link",
                "handled_by": "Subscription activation handler",
                "action": "Mark case as RECOVERED, close recovery workflow, record positive reward",
            },
            {
                "event": "subscription.paused",
                "trigger": "Customer pauses mandate from bank/UPI app",
                "handled_by": "Mandate state listener",
                "action": "Transition case to ACTION_REQUIRED, pause automated debit retries",
            },
            {
                "event": "subscription.cancelled",
                "trigger": "Customer or bank cancels mandate",
                "handled_by": "Mandate state listener",
                "action": "Immediate HARD STOP; all automated debits blocked per RBI mandate guidelines",
            },
        ],
        "api_endpoints": [
            {
                "method": "POST",
                "endpoint": "/v1/payment_links",
                "purpose": "Generate smart recovery payment link with pre-filled amount and customer details",
                "simulator": "MockRazorpay.create_payment_link()",
            },
            {
                "method": "POST",
                "endpoint": "/v1/subscriptions/:id/retry",
                "purpose": "Trigger re-presentment / retry of a recurring charge at the chosen optimal time",
                "simulator": "MockRazorpay.retry_payment()",
            },
            {
                "method": "GET",
                "endpoint": "/v1/payments/:id",
                "purpose": "Query definitive status and gateway error codes for a transaction",
                "simulator": "MockRazorpay.get_payment()",
            },
        ],
        "architecture_layers": [
            {
                "layer": "Ingestion & Security",
                "component": "FastAPI Webhook Controller + HMAC-SHA256 Signature Verification",
                "mock_status": "Simulated in MockRazorpay with mock signatures",
            },
            {
                "layer": "Idempotency & Concurrency",
                "component": "SQLite / PostgreSQL Webhook Idempotency Store with distributed locking",
                "mock_status": "Active SQLite store in recover_idempotency.db",
            },
            {
                "layer": "Policy & Safety Fence",
                "component": "Deterministic Rule Engine (R1–R8) enforcing RBI limits, quiet hours, and caps",
                "mock_status": "Active (recover.policy)",
            },
            {
                "layer": "AI Decisioning",
                "component": "Bayesian Multi-Armed Bandit (Thompson Sampling) with Expected Value optimization",
                "mock_status": "Active (recover.decide)",
            },
            {
                "layer": "Execution & Outreach",
                "component": "Mock Razorpay API client + Guardrailed customer communications",
                "mock_status": "Active (recover.outreach, recover.mock_razorpay)",
            },
            {
                "layer": "Audit & Observability",
                "component": "Append-only tamper-evident audit trail + Real-time KPI aggregation",
                "mock_status": "Active (recover.engine, recover.metrics)",
            },
        ],
    }
