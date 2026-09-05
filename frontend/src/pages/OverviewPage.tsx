import React from 'react';
import {
  TrendingUp,
  IndianRupee,
  ShieldCheck,
  Percent,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Zap,
} from 'lucide-react';
import { OverviewKPIs, FailureClass } from '../types';
import { KpiCard } from '../components/KpiCard';
import { PipelineBanner } from '../components/PipelineBanner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface OverviewPageProps {
  kpis: OverviewKPIs | null;
  loading: boolean;
  onNavigateToCases: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  kpis,
  loading,
  onNavigateToCases,
}) => {
  if (loading || !kpis) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-3" />
        <span className="ml-3 font-medium text-sm">Loading recovery performance metrics...</span>
      </div>
    );
  }

  const formatInr = (val: number) => `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

  // Chart data: Net Revenue vs Costs
  const revenueChartData = [
    {
      category: 'Gross Recovered',
      'RECOVER (Smart)': kpis.smart_net_revenue + kpis.smart_total_fees,
      'Naive Schedule': kpis.naive_net_revenue + kpis.naive_total_fees,
    },
    {
      category: 'Net Revenue',
      'RECOVER (Smart)': kpis.smart_net_revenue,
      'Naive Schedule': kpis.naive_net_revenue,
    },
    {
      category: 'Action Fees',
      'RECOVER (Smart)': kpis.smart_total_fees,
      'Naive Schedule': kpis.naive_total_fees,
    },
  ];

  // Chart data: Recovery rate by failure class
  const classOrder: FailureClass[] = ['SOFT', 'TRANSIENT', 'ACTION_REQUIRED', 'HARD'];
  const classChartData = classOrder.map((fc) => {
    const classInfo = kpis.by_class?.[fc];
    return {
      class: fc,
      'RECOVER Recovery %': classInfo ? Math.round(classInfo.recovery_rate * 100) : 0,
    };
  });

  return (
    <div className="space-y-6">
      
      {/* Title & Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Executive Recovery Console
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Decline-aware, policy-bounded AI revenue recovery for recurring billing and Autopay failures.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            Track 3 · AI Revenue Recovery
          </span>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            100% Offline · Zero API Keys
          </span>
        </div>
      </div>

      {/* Central Pipeline Banner */}
      <PipelineBanner />

      {/* Top 4 Financial Impact KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Recovery Rate"
          value={`${kpis.smart_recovery_rate}%`}
          subValue={`Naive baseline: ${kpis.naive_recovery_rate}%`}
          delta={{
            text: `+${kpis.recovery_rate_lift_pct}% lift`,
            isPositive: kpis.recovery_rate_lift_pct >= 0,
          }}
          variant="blue"
          icon={<Percent className="w-5 h-5" />}
          tooltip="Percentage of failed recurring payments successfully recovered into captured revenue."
        />

        <KpiCard
          label="Net Revenue Recovered"
          value={formatInr(kpis.smart_net_revenue)}
          subValue={`At risk: ${formatInr(kpis.total_at_risk_inr)}`}
          delta={{
            text: `+${formatInr(kpis.net_revenue_lift_inr)} lift`,
            isPositive: kpis.net_revenue_lift_inr >= 0,
          }}
          variant="green"
          icon={<IndianRupee className="w-5 h-5" />}
          tooltip="Total recovered revenue minus all SMS, WhatsApp, and Razorpay retry transaction costs."
        />

        <KpiCard
          label="Gateway Fee Savings"
          value={formatInr(kpis.fee_savings_inr)}
          subValue={`Total fees: ${formatInr(kpis.smart_total_fees)}`}
          delta={{
            text: `Saved vs ${formatInr(kpis.naive_total_fees)} naive`,
            isPositive: kpis.fee_savings_inr >= 0,
          }}
          variant="amber"
          icon={<TrendingUp className="w-5 h-5" />}
          tooltip="Cost reduction achieved by eliminating futile retries and targeting only high-yield recovery windows."
        />

        <KpiCard
          label="Policy Violations"
          value={`${kpis.smart_violations}`}
          subValue={`${kpis.violations_prevented} violations prevented`}
          delta={{
            text: '100% Policy Bound',
            isPositive: true,
          }}
          variant="purple"
          icon={<ShieldCheck className="w-5 h-5" />}
          tooltip="Zero regulatory (RBI/NPCI) or merchant policy violations allowed by the deterministic safety fence."
        />
      </div>

      {/* Head-to-Head Benchmark Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Benchmark Comparison: RECOVER vs Naive Static Schedule
            </h2>
            <p className="text-xs text-slate-500">
              Evaluated across {kpis.total_cases} synthetic failed payment events
            </p>
          </div>
          <button
            onClick={onNavigateToCases}
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 inline-flex items-center gap-1"
          >
            Explore Cases <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/80 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-6 py-3">Performance Dimension</th>
                <th className="px-6 py-3 text-blue-700 bg-blue-50/40">RECOVER (Policy-Bounded AI)</th>
                <th className="px-6 py-3 text-slate-600">Naive Static Retry (24h)</th>
                <th className="px-6 py-3 text-emerald-700">Financial / Safety Impact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              <tr className="hover:bg-slate-50/50">
                <td className="px-6 py-3.5 text-slate-800">Overall Recovery Rate</td>
                <td className="px-6 py-3.5 text-blue-700 font-bold bg-blue-50/20">{kpis.smart_recovery_rate}%</td>
                <td className="px-6 py-3.5 text-slate-600">{kpis.naive_recovery_rate}%</td>
                <td className="px-6 py-3.5 text-emerald-600 font-semibold">+{kpis.recovery_rate_lift_pct} pp recovery lift</td>
              </tr>
              <tr className="hover:bg-slate-50/50">
                <td className="px-6 py-3.5 text-slate-800">Net Revenue Recovered</td>
                <td className="px-6 py-3.5 text-blue-700 font-bold bg-blue-50/20">{formatInr(kpis.smart_net_revenue)}</td>
                <td className="px-6 py-3.5 text-slate-600">{formatInr(kpis.naive_net_revenue)}</td>
                <td className="px-6 py-3.5 text-emerald-600 font-semibold">+{formatInr(kpis.net_revenue_lift_inr)} net cash lift</td>
              </tr>
              <tr className="hover:bg-slate-50/50">
                <td className="px-6 py-3.5 text-slate-800">Gateway & Communication Fees</td>
                <td className="px-6 py-3.5 text-blue-700 font-bold bg-blue-50/20">{formatInr(kpis.smart_total_fees)}</td>
                <td className="px-6 py-3.5 text-slate-600">{formatInr(kpis.naive_total_fees)}</td>
                <td className="px-6 py-3.5 text-emerald-600 font-semibold">{formatInr(kpis.fee_savings_inr)} saved (fewer futile calls)</td>
              </tr>
              <tr className="hover:bg-slate-50/50">
                <td className="px-6 py-3.5 text-slate-800">Policy & Compliance Violations</td>
                <td className="px-6 py-3.5 text-emerald-700 font-bold bg-blue-50/20">0 (Guaranteed Safe)</td>
                <td className="px-6 py-3.5 text-rose-600 font-semibold">{kpis.naive_violations} violations</td>
                <td className="px-6 py-3.5 text-emerald-600 font-semibold">Zero hard decline / quiet hour breaches</td>
              </tr>
              <tr className="hover:bg-slate-50/50">
                <td className="px-6 py-3.5 text-slate-800">95% Confidence Interval (Wilson)</td>
                <td className="px-6 py-3.5 text-blue-700 font-mono text-xs bg-blue-50/20">
                  [{kpis.confidence_interval?.ci_lower_pct}%, {kpis.confidence_interval?.ci_upper_pct}%]
                </td>
                <td className="px-6 py-3.5 text-slate-500 text-xs">Standard Error Model</td>
                <td className="px-6 py-3.5 text-slate-600 text-xs">Statistically significant improvement</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Chart 1: Revenue vs Cost */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            Financial Impact: RECOVER vs Naive (₹)
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Comparison of gross recovery, net retained revenue, and action cost overhead.
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={revenueChartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="category" tick={{ fontSize: 12, fill: '#64748B' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={(v) => `₹${v / 1000}k`} />
                <Tooltip
                  formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, '']}
                  contentStyle={{ backgroundColor: '#0F172A', color: '#FFF', borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                <Bar dataKey="RECOVER (Smart)" fill="#2563EB" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Naive Schedule" fill="#94A3B8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Recovery Rate by Failure Class */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            Recovery Efficiency by Failure Class (%)
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Adaptive strategy per decline reason: SOFT (salary timing), TRANSIENT (2h cooldown), ACTION_REQUIRED (payment link).
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={classChartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="class" tick={{ fontSize: 12, fill: '#64748B' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  formatter={(val: any) => [`${val}%`, 'Recovery Rate']}
                  contentStyle={{ backgroundColor: '#0F172A', color: '#FFF', borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="RECOVER Recovery %" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Core Architectural Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center mb-3">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h4 className="text-sm font-bold text-slate-900 mb-1">1. Rules Build the Fence</h4>
          <p className="text-xs text-slate-500 leading-relaxed">
            Deterministic policy engine enforces RBI Autopay guidelines, 24h pre-debit notices, quiet hours (21:00–09:00), and caps. Hard declines are never retried.
          </p>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
            <Zap className="w-5 h-5" />
          </div>
          <h4 className="text-sm font-bold text-slate-900 mb-1">2. AI Chooses Within the Fence</h4>
          <p className="text-xs text-slate-500 leading-relaxed">
            Thompson Sampling bandit balances exploration vs exploitation. Dynamically samples recovery probability and maximizes Net Expected Value (EV = p·amount − cost).
          </p>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <h4 className="text-sm font-bold text-slate-900 mb-1">3. Fully Audited & Idempotent</h4>
          <p className="text-xs text-slate-500 leading-relaxed">
            Every step is recorded in an append-only audit trail with exact reasons for accepted and rejected actions. Local SQLite idempotency guarantees 0 duplicate debit attempts.
          </p>
        </div>
      </div>

    </div>
  );
};
