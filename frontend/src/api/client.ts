import {
  OverviewKPIs,
  CaseItem,
  CaseDetail,
  DecisionIntelligenceData,
  PolicyControls,
  HardRule,
  HumanReviewItem,
  ReliabilityStats,
  BlastTestResponse,
  ReliabilityEvent,
  AuditEntry,
  BenchmarkData,
  TaxonomyData,
  IntegrationMapData,
} from '../types';

const API_BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = 'API request failed';
    try {
      const err = await res.json();
      errorDetail = err.detail || err.message || errorDetail;
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  async getHealth(): Promise<{ status: string; mock_mode: boolean; version: string }> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse(res);
  },

  async getSimulationState(): Promise<{
    n: number;
    seed: number;
    controls: PolicyControls;
    kpis: OverviewKPIs;
    total_cases: number;
    mock_mode: boolean;
  }> {
    const res = await fetch(`${API_BASE}/simulation/state`);
    return handleResponse(res);
  },

  async runSimulation(params: {
    n: number;
    seed: number;
    controls?: Partial<PolicyControls> | null;
    llm?: boolean;
  }): Promise<{
    n: number;
    seed: number;
    controls: PolicyControls;
    kpis: OverviewKPIs;
    total_cases: number;
  }> {
    const res = await fetch(`${API_BASE}/simulation/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        n: params.n,
        seed: params.seed,
        controls: params.controls || null,
        llm: !!params.llm,
      }),
    });
    return handleResponse(res);
  },

  async getCases(params: {
    page?: number;
    page_size?: number;
    failure_class?: string;
    state?: string;
    search?: string;
    min_amount?: number;
    max_amount?: number;
    risk_min?: number;
  }): Promise<{
    cases: CaseItem[];
    total: number;
    page: number;
    page_size: number;
  }> {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.page_size) query.set('page_size', String(params.page_size));
    if (params.failure_class && params.failure_class !== 'ALL') query.set('failure_class', params.failure_class);
    if (params.state && params.state !== 'ALL') query.set('state', params.state);
    if (params.search) query.set('search', params.search);
    if (params.min_amount !== undefined) query.set('min_amount', String(params.min_amount));
    if (params.max_amount !== undefined) query.set('max_amount', String(params.max_amount));
    if (params.risk_min !== undefined) query.set('risk_min', String(params.risk_min));

    const res = await fetch(`${API_BASE}/cases?${query.toString()}`);
    return handleResponse(res);
  },

  async getCaseDetail(caseId: number): Promise<CaseDetail> {
    const res = await fetch(`${API_BASE}/cases/${caseId}`);
    return handleResponse(res);
  },

  async getDecisionIntelligence(): Promise<DecisionIntelligenceData> {
    const res = await fetch(`${API_BASE}/decision-intelligence`);
    return handleResponse(res);
  },

  async getPolicyControls(): Promise<{
    controls: PolicyControls;
    hard_rules: HardRule[];
  }> {
    const res = await fetch(`${API_BASE}/policy/controls`);
    return handleResponse(res);
  },

  async updatePolicyControls(controls: PolicyControls): Promise<{
    success: boolean;
    controls: PolicyControls;
    message: string;
  }> {
    const res = await fetch(`${API_BASE}/policy/controls`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(controls),
    });
    return handleResponse(res);
  },

  async getReliabilityStats(): Promise<ReliabilityStats> {
    const res = await fetch(`${API_BASE}/reliability/stats`);
    return handleResponse(res);
  },

  async getReliabilityEvents(): Promise<ReliabilityEvent[]> {
    const res = await fetch(`${API_BASE}/reliability/events`);
    return handleResponse(res);
  },

  async runBlastTest(params: {
    count?: number;
    error_code?: string;
    amount?: number;
  }): Promise<BlastTestResponse> {
    const res = await fetch(`${API_BASE}/reliability/blast-test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        count: params.count ?? 10,
        error_code: params.error_code ?? 'INSUFFICIENT_FUNDS',
        amount: params.amount ?? 1499.0,
      }),
    });
    return handleResponse(res);
  },

  async simulateWebhook(params: {
    error_code?: string;
    amount?: number;
    method?: string;
    event_type?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/reliability/simulate-webhook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error_code: params.error_code ?? 'UPI_TIMEOUT',
        amount: params.amount ?? 2499.0,
        method: params.method ?? 'upi',
        event_type: params.event_type ?? 'payment.failed',
      }),
    });
    return handleResponse(res);
  },

  async resetReliability(): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/reliability/reset`, { method: 'POST' });
    return handleResponse(res);
  },

  async getHumanReviewQueue(): Promise<HumanReviewItem[]> {
    const res = await fetch(`${API_BASE}/human-review/queue`);
    return handleResponse(res);
  },

  async executeHumanAction(
    caseId: number,
    action: string,
    note?: string
  ): Promise<{ success: boolean; case: CaseItem; audit_entry: any }> {
    const res = await fetch(`${API_BASE}/human-review/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_id: caseId,
        action,
        note: note || 'Manual action by reviewer',
      }),
    });
    return handleResponse(res);
  },

  async getAuditTrail(params: {
    page?: number;
    page_size?: number;
    case_id?: number;
    arm?: string;
    violation_only?: boolean;
    policy?: string;
  }): Promise<{
    logs: AuditEntry[];
    total: number;
    page: number;
    page_size: number;
  }> {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.page_size) query.set('page_size', String(params.page_size));
    if (params.case_id !== undefined) query.set('case_id', String(params.case_id));
    if (params.arm && params.arm !== 'ALL') query.set('arm', params.arm);
    if (params.violation_only) query.set('violation_only', 'true');
    if (params.policy) query.set('policy', params.policy);

    const res = await fetch(`${API_BASE}/audit-trail?${query.toString()}`);
    return handleResponse(res);
  },

  async exportAuditTrail(policy: string = 'smart'): Promise<AuditEntry[]> {
    const res = await fetch(`${API_BASE}/audit-trail/export?policy=${policy}`);
    return handleResponse(res);
  },

  async runBenchmarks(params: {
    seeds?: number[];
    n?: number;
  }): Promise<BenchmarkData> {
    const res = await fetch(`${API_BASE}/benchmarks/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        seeds: params.seeds || [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        n: params.n || 200,
      }),
    });
    return handleResponse(res);
  },

  async getTaxonomy(): Promise<TaxonomyData> {
    const res = await fetch(`${API_BASE}/taxonomy`);
    return handleResponse(res);
  },

  async getIntegrationMap(): Promise<IntegrationMapData> {
    const res = await fetch(`${API_BASE}/integration-map`);
    return handleResponse(res);
  },
};
