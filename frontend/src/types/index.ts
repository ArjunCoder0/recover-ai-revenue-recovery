export type FailureClass = 'SOFT' | 'TRANSIENT' | 'ACTION_REQUIRED' | 'HARD';
export type PaymentMethod = 'card' | 'upi_autopay' | 'netbanking';
export type CaseState = 'OPEN' | 'RECOVERED' | 'EXHAUSTED' | 'ESCALATED';

export interface CaseItem {
  id: number;
  method: PaymentMethod;
  amount: number;
  error_code: string;
  failure_class: FailureClass;
  risk_score: number;
  failed_at: number;
  salary_day: number;
  created_at: number;
  retries: number;
  contacts: number;
  cost: number;
  state: CaseState;
  recovered_at: number | null;
  history: Array<{
    seq: number;
    kind: string;
    decided_at: number;
    executed_at: number | null;
    arm: string;
    success: boolean | null;
    violation: number;
    deferred: boolean;
    rationale?: any;
    violation_reasons?: string[];
  }>;
  latest_rationale?: any;
}

export interface ClassMetrics {
  cases: number;
  recovered: number;
  recovery_rate: number;
  amount_at_risk: number;
  amount_recovered: number;
}

export interface OverviewKPIs {
  smart_recovery_rate: number;
  naive_recovery_rate: number;
  recovery_rate_lift_pct: number;
  smart_net_revenue: number;
  naive_net_revenue: number;
  net_revenue_lift_inr: number;
  smart_total_fees: number;
  naive_total_fees: number;
  fee_savings_inr: number;
  smart_violations: number;
  naive_violations: number;
  violations_prevented: number;
  total_cases: number;
  total_at_risk_inr: number;
  by_class: Record<FailureClass, ClassMetrics>;
  confidence_interval: {
    metric: string;
    rate_pct: number;
    ci_lower_pct: number;
    ci_upper_pct: number;
    confidence_level: string;
  };
}

export interface PolicyControls {
  max_retries: number;
  min_retry_gap_h: number;
  contact_cap: number;
  quiet_hours: [number, number];
  recovery_window_days: number;
  escalate_above: number;
  pre_debit_notice_h: number;
}

export interface HardRule {
  id: string;
  name: string;
  status: string;
  applies_to: string;
  condition: string;
  policy_action: string;
}

export interface AlternativeArm {
  arm: string;
  allowed: boolean;
  rejection_reason: string | null;
  sampled_p: number;
  expected_value: number;
  cost: number;
  alpha: number;
  beta: number;
}

export interface CaseDetail {
  case: CaseItem;
  why_chosen: {
    chosen_arm: string;
    rationale: any;
    explanation_text: string[];
  };
  alternatives: AlternativeArm[];
  outreach_preview: {
    arm: string;
    message: string;
    source: string;
  } | null;
  history: any[];
}

export interface BanditArm {
  arm: string;
  failure_class: FailureClass;
  alpha: number;
  beta: number;
  pulls: number;
  mean_prob: number;
  cost: number;
}

export interface DecisionIntelligenceData {
  arms: BanditArm[];
  arms_by_class: Record<FailureClass, BanditArm[]>;
  total_decisions: number;
}

export interface HumanReviewItem {
  case_id: number;
  amount: number;
  method: string;
  failure_class: FailureClass;
  error_code: string;
  risk_score: number;
  failed_at: number;
  retries: number;
  state: string;
  reason: string;
  recommended_action: string;
}

export interface ReliabilityStats {
  total_events: number;
  processed_count: number;
  failed_count: number;
  total_duplicates_blocked: number;
}

export interface BlastTestResponse {
  event_id: string;
  total_bursts: number;
  processed: number;
  blocked: number;
  duplicate_executions: number;
  execution_time_ms: number;
  status: string;
  message: string;
}

export interface ReliabilityEvent {
  event_id: string;
  event_type: string;
  payment_id: string;
  error_code: string;
  amount: number;
  total_burst: number;
  processed: number;
  blocked: number;
  duplicate_executions: number;
  timestamp: string;
}

export interface AuditEntry {
  seq: number;
  kind: string;
  policy: string;
  decided_at: number;
  executed_at: number | null;
  case_id: number;
  arm: string;
  failure_class: FailureClass;
  method: string;
  amount: number;
  success: boolean | null;
  violation: number;
  violation_reasons: string[];
  deferred: boolean;
  rationale?: any;
}

export interface BenchmarkSeedResult {
  seed: number;
  smart_recovered_pct: number;
  naive_recovered_pct: number;
  smart_net_revenue: number;
  naive_net_revenue: number;
  smart_cost: number;
  naive_cost: number;
  smart_violations: number;
  naive_violations: number;
}

export interface BenchmarkSummary {
  seeds_tested: number;
  batch_size_per_seed: number;
  avg_smart_recovery_rate: number;
  avg_naive_recovery_rate: number;
  avg_recovery_lift_pct: number;
  avg_smart_net_revenue: number;
  avg_naive_net_revenue: number;
  avg_net_revenue_lift: number;
  avg_fee_savings: number;
  total_smart_violations: number;
  total_naive_violations: number;
  violations_prevented: number;
}

export interface BenchmarkData {
  summary: BenchmarkSummary;
  seeds_data: BenchmarkSeedResult[];
}

export interface TaxonomyClass {
  name: string;
  description: string;
  retry_policy: string;
  codes: string[];
  badge_color: string;
}

export interface TaxonomyData {
  classes: Record<FailureClass, TaxonomyClass>;
  code_meanings: Record<string, string>;
}

export interface IntegrationMapData {
  webhook_events: Array<{
    event: string;
    trigger: string;
    handled_by: string;
    action: string;
  }>;
  api_endpoints: Array<{
    method: string;
    endpoint: string;
    purpose: string;
    simulator: string;
  }>;
  architecture_layers: Array<{
    layer: string;
    component: string;
    mock_status: string;
  }>;
}
