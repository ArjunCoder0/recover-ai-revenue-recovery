"""Pydantic schemas for the RECOVER FastAPI backend."""

from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field


class ControlsSchema(BaseModel):
    max_retries: int = Field(default=4, ge=0, le=8)
    min_retry_gap_h: int = Field(default=2, ge=1, le=72)
    contact_cap: int = Field(default=2, ge=0, le=5)
    quiet_hours: Tuple[int, int] = Field(default=(21, 9))
    recovery_window_days: int = Field(default=30, ge=3, le=45)
    escalate_above: float = Field(default=2500.0, ge=0.0)
    pre_debit_notice_h: int = Field(default=24, ge=0, le=72)


class SimulationRequest(BaseModel):
    n: int = Field(default=400, ge=10, le=5000)
    seed: int = Field(default=42, ge=0)
    controls: Optional[Dict[str, Any]] = None
    llm: bool = False


class CaseItem(BaseModel):
    id: int
    method: str
    amount: float
    error_code: str
    failure_class: str
    risk_score: float
    failed_at: int
    salary_day: int
    created_at: int
    retries: int
    contacts: int
    cost: float
    state: str
    recovered_at: Optional[int] = None
    history: List[Dict[str, Any]] = []
    latest_rationale: Optional[Dict[str, Any]] = None


class OverviewKPIs(BaseModel):
    smart_recovery_rate: float
    naive_recovery_rate: float
    recovery_rate_lift_pct: float
    smart_net_revenue: float
    naive_net_revenue: float
    net_revenue_lift_inr: float
    smart_total_fees: float
    naive_total_fees: float
    fee_savings_inr: float
    smart_violations: int
    naive_violations: int
    violations_prevented: int
    total_cases: int
    total_at_risk_inr: float
    by_class: Dict[str, Dict[str, Any]]
    confidence_interval: Dict[str, Any]


class SimulationStateResponse(BaseModel):
    n: int
    seed: int
    controls: Dict[str, Any]
    kpis: OverviewKPIs
    total_cases: int
    mock_mode: bool = True


class CasesResponse(BaseModel):
    cases: List[CaseItem]
    total: int
    page: int
    page_size: int


class AlternativeArm(BaseModel):
    arm: str
    allowed: bool
    rejection_reason: Optional[str] = None
    sampled_p: float
    expected_value: float
    cost: float
    alpha: float
    beta: float


class CaseDetailResponse(BaseModel):
    case: CaseItem
    why_chosen: Dict[str, Any]
    alternatives: List[AlternativeArm]
    outreach_preview: Optional[Dict[str, str]] = None
    history: List[Dict[str, Any]]


class BanditArmState(BaseModel):
    arm: str
    failure_class: str
    alpha: float
    beta: float
    pulls: int
    mean_prob: float
    cost: float


class DecisionIntelligenceResponse(BaseModel):
    arms: List[BanditArmState]
    arms_by_class: Dict[str, List[BanditArmState]]
    total_decisions: int


class HumanReviewItem(BaseModel):
    case_id: int
    amount: float
    method: str
    failure_class: str
    error_code: str
    risk_score: float
    failed_at: int
    retries: int
    state: str
    reason: str
    recommended_action: str


class HumanActionRequest(BaseModel):
    case_id: int
    action: str = Field(description="'APPROVE', 'REJECT', or a specific arm e.g. 'PAYMENT_LINK', 'STOP'")
    note: Optional[str] = "Manual action by human reviewer"


class ReliabilityStats(BaseModel):
    total_events: int
    processed_count: int
    failed_count: int
    total_duplicates_blocked: int


class BlastTestRequest(BaseModel):
    event_id: Optional[str] = None
    count: int = Field(default=10, ge=2, le=50)
    error_code: str = "INSUFFICIENT_FUNDS"
    amount: float = 1299.0


class BlastTestResponse(BaseModel):
    event_id: str
    total_bursts: int
    processed: int
    blocked: int
    duplicate_executions: int
    execution_time_ms: float
    status: str
    message: str


class SimulateWebhookRequest(BaseModel):
    event_id: Optional[str] = None
    event_type: str = "payment.failed"
    error_code: str = "UPI_TIMEOUT"
    amount: float = 2499.0
    method: str = "upi"
    customer_phone: str = "+919876543210"
    customer_email: str = "user@example.com"


class BenchmarkRequest(BaseModel):
    seeds: List[int] = Field(default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    n: int = Field(default=200, ge=50, le=1000)


class BenchmarkSeedResult(BaseModel):
    seed: int
    smart_recovered_pct: float
    naive_recovered_pct: float
    smart_net_revenue: float
    naive_net_revenue: float
    smart_cost: float
    naive_cost: float
    smart_violations: int
    naive_violations: int


class BenchmarkResponse(BaseModel):
    summary: Dict[str, Any]
    seeds_data: List[BenchmarkSeedResult]
