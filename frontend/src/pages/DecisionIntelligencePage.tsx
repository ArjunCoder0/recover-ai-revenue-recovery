import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Brain,
  TrendingUp,
  BarChart2,
  CheckCircle2,
  Info,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { api } from '../api/client';
import { DecisionIntelligenceData, FailureClass, BanditArm } from '../types';
import { ClassBadge, ArmBadge } from '../components/Badge';
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

export const DecisionIntelligencePage: React.FC = () => {
  const [data, setData] = useState<DecisionIntelligenceData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedClass, setSelectedClass] = useState<string>('ALL');

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await api.getDecisionIntelligence();
        if (isMounted) setData(res);
      } catch (err) {
        console.error('Failed to load decision intelligence:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchData();
    return () => {
      isMounted = false;
    };
  }, []);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-3" />
        <span className="ml-3 font-medium text-sm">Loading Bayesian bandit distributions...</span>
      </div>
    );
  }

  const filteredArms =
    selectedClass === 'ALL'
      ? data.arms
      : data.arms.filter((a) => a.failure_class === selectedClass);

  // Chart data for selected class
  const chartData = filteredArms.map((a) => ({
    name: `${a.failure_class}: ${a.arm}`,
    'Win Probability %': Math.round(a.mean_prob * 100),
    'Sampled Pulls': a.pulls,
  }));

  return (
    <div className="space-y-6">
      
      {/* Title */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Decision Intelligence & Bayesian Online Learning
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          How Thompson Sampling learns optimal recovery timings and channels online from observed transaction outcomes.
        </p>
      </div>

      {/* Concept Architecture Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-blue-50 text-blue-600 flex-shrink-0">
            <Brain className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Online Bayesian Exploration vs Exploitation
            </h2>
            <p className="text-xs text-slate-600 leading-relaxed mt-1.5">
              The AI maintains probability beliefs modeled as <strong className="text-slate-800">Beta distributions (α, β)</strong> for every legal action arm per failure class.
              Initial beliefs start with domain-informed priors. As webhook outcomes arrive from Mock Razorpay, posterior parameters update dynamically:
              <span className="font-mono text-blue-600 ml-1">α ← α + success</span> and{' '}
              <span className="font-mono text-rose-600">β ← β + failure</span>.
              Decisions are made by drawing samples from these distributions and selecting the action with the highest Net Expected Value (<span className="font-mono font-semibold">EV = p·amount − fee</span>).
            </p>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3 flex-wrap">
        <span className="text-xs font-semibold text-slate-500 mr-2">Filter Failure Class:</span>
        {['ALL', 'SOFT', 'TRANSIENT', 'ACTION_REQUIRED', 'HARD'].map((fc) => (
          <button
            key={fc}
            onClick={() => setSelectedClass(fc)}
            className={`px-3.5 py-1 rounded-full text-xs font-semibold transition-all ${
              selectedClass === fc
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {fc}
          </button>
        ))}
      </div>

      {/* Chart: Arm Recovery Probabilities */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 mb-1">
          Posterior Mean Recovery Probability by Action Arm (%)
        </h3>
        <p className="text-xs text-slate-500 mb-5">
          Learned success rate representing the expected likelihood of payment collection for each arm.
        </p>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
              <XAxis dataKey="name" angle={-25} textAnchor="end" interval={0} tick={{ fontSize: 10, fill: '#64748B' }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={(v) => `${v}%`} />
              <Tooltip
                formatter={(val: any, name: string) => [
                  name === 'Win Probability %' ? `${val}%` : val,
                  name,
                ]}
                contentStyle={{ backgroundColor: '#0F172A', color: '#FFF', borderRadius: 8, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 16 }} />
              <Bar dataKey="Win Probability %" fill="#2563EB" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table: Full Snapshot of Beliefs */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Posterior Distribution Belief Table (α, β, Mean)
            </h3>
            <p className="text-xs text-slate-500">
              Multi-Armed Bandit parameters currently guiding AI decisions
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500 bg-slate-100 px-2.5 py-1 rounded">
            Total decisions: {data.total_decisions}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-5 py-3">Class</th>
                <th className="px-5 py-3">Recovery Arm</th>
                <th className="px-5 py-3">Posterior α (Successes)</th>
                <th className="px-5 py-3">Posterior β (Failures)</th>
                <th className="px-5 py-3">Observations (Pulls)</th>
                <th className="px-5 py-3">Posterior Mean Win %</th>
                <th className="px-5 py-3">Action Fee (Cost)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredArms.map((a, i) => (
                <tr key={i} className="hover:bg-slate-50/50">
                  <td className="px-5 py-3 font-semibold">
                    <ClassBadge failureClass={a.failure_class} />
                  </td>
                  <td className="px-5 py-3">
                    <ArmBadge arm={a.arm} />
                  </td>
                  <td className="px-5 py-3 font-mono text-emerald-700 font-semibold">{a.alpha.toFixed(1)}</td>
                  <td className="px-5 py-3 font-mono text-rose-700 font-semibold">{a.beta.toFixed(1)}</td>
                  <td className="px-5 py-3 font-mono">{a.pulls}</td>
                  <td className="px-5 py-3 font-mono font-bold text-blue-700">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600 rounded-full"
                          style={{ width: `${Math.min(100, Math.max(0, a.mean_prob * 100))}%` }}
                        />
                      </div>
                      <span>{(a.mean_prob * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 font-mono text-slate-600">₹{a.cost.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Strategic Insights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-sm">
          <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 mb-2">
            <span className="w-2 h-2 rounded-full bg-purple-500" />
            ACTION_REQUIRED Convergence
          </h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            For expired cards and paused mandates, re-presentment retries collapse toward <strong className="text-slate-900">~2% success</strong> as failures accumulate.
            The Thompson Sampling bandit rapidly learns that retrying is futile and steers 100% of these cases to <strong className="text-purple-700">PAYMENT_LINK</strong>.
          </p>
        </div>

        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-sm">
          <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 mb-2">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            SOFT Salary-Day Alignment
          </h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            For insufficient funds declines, <strong className="text-slate-900">RETRY_SALARY_DAY</strong> posterior mean climbs significantly above generic 2h/24h retries.
            The model demonstrates that aligning recovery with Indian salary cycles (days 1–5) maximizes collected revenue while preserving gateway quota.
          </p>
        </div>
      </div>

    </div>
  );
};
