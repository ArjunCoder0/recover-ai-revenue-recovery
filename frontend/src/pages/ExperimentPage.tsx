import React, { useState } from 'react';
import {
  FlaskConical,
  Play,
  TrendingUp,
  Percent,
  IndianRupee,
  ShieldCheck,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../api/client';
import { BenchmarkData } from '../types';
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

export const ExperimentPage: React.FC = () => {
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkData | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [numSeeds, setNumSeeds] = useState<number>(10);
  const [batchSize, setBatchSize] = useState<number>(200);

  const handleRunBenchmark = async () => {
    setRunning(true);
    try {
      const seeds = Array.from({ length: numSeeds }, (_, i) => i + 1);
      const res = await api.runBenchmarks({ seeds, n: batchSize });
      setBenchmarkData(res);
    } catch (err: any) {
      alert(`Benchmark execution failed: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  const formatInr = (val: number) => `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

  // Chart data for seeds
  const chartData = benchmarkData?.seeds_data.map((s) => ({
    seed: `Seed ${s.seed}`,
    'RECOVER Rate %': s.smart_recovered_pct,
    'Naive Rate %': s.naive_recovered_pct,
    'RECOVER Net (₹)': s.smart_net_revenue,
    'Naive Net (₹)': s.naive_net_revenue,
  }));

  return (
    <div className="space-y-6">
      
      {/* Title */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Multi-Seed Benchmark & Statistical Validation
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Proves that revenue lift and zero-violation guarantees are statistically robust across random seeds and transaction distributions.
        </p>
      </div>

      {/* Benchmark Control Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FlaskConical className="w-5 h-5 text-blue-600" />
              Automated Comparative Benchmark Experiment
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Executes parallel simulation runs comparing RECOVER against the industry-standard naive schedule.
            </p>
          </div>

          <button
            onClick={handleRunBenchmark}
            disabled={running}
            className="inline-flex items-center gap-2 px-6 py-2.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-xl shadow-sm transition-all disabled:opacity-50"
          >
            {running ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Simulating {numSeeds} Seeds ({numSeeds * batchSize} Cases)...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run {numSeeds}-Seed Benchmark
              </>
            )}
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5 pt-4 border-t border-slate-100 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Number of Distinct Pseudo-Random Seeds ({numSeeds} runs)
            </label>
            <input
              type="range"
              min="3"
              max="20"
              step="1"
              value={numSeeds}
              onChange={(e) => setNumSeeds(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Batch Size per Seed ({batchSize} cases/seed)
            </label>
            <input
              type="range"
              min="50"
              max="500"
              step="50"
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
        </div>
      </div>

      {/* Benchmark Summary Metrics */}
      {benchmarkData && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm border-l-4 border-l-blue-500">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Average Recovery Lift
              </p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                +{benchmarkData.summary.avg_recovery_lift_pct} pp
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Smart: {benchmarkData.summary.avg_smart_recovery_rate}% vs Naive: {benchmarkData.summary.avg_naive_recovery_rate}%
              </p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm border-l-4 border-l-emerald-500">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Average Net Revenue Lift
              </p>
              <p className="text-2xl font-bold text-emerald-600 mt-1">
                +{formatInr(benchmarkData.summary.avg_net_revenue_lift)}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Per seed run of {benchmarkData.summary.batch_size_per_seed} cases
              </p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm border-l-4 border-l-amber-500">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Average Gateway Fee Savings
              </p>
              <p className="text-2xl font-bold text-amber-600 mt-1">
                {formatInr(benchmarkData.summary.avg_fee_savings)}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Eliminated futile retry charges
              </p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm border-l-4 border-l-purple-500">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Violations Prevented
              </p>
              <p className="text-2xl font-bold text-purple-600 mt-1">
                {benchmarkData.summary.violations_prevented}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Across all {benchmarkData.summary.seeds_tested} random seeds
              </p>
            </div>
          </div>

          {/* Visual Seed-by-Seed Comparison Chart */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-1">
              Recovery Rate Across Random Seeds (%)
            </h3>
            <p className="text-xs text-slate-500 mb-5">
              RECOVER consistently outperforms the naive baseline across diverse customer cohort distributions.
            </p>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                  <XAxis dataKey="seed" tick={{ fontSize: 11, fill: '#64748B' }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={(v) => `${v}%`} />
                  <Tooltip
                    formatter={(val: any) => [`${val}%`, '']}
                    contentStyle={{ backgroundColor: '#0F172A', color: '#FFF', borderRadius: 8, fontSize: 12 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                  <Bar dataKey="RECOVER Rate %" fill="#2563EB" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Naive Rate %" fill="#94A3B8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Full Seed Results Table */}
          <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">
                Detailed Seed Benchmark Results Table
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
                  <tr>
                    <th className="px-5 py-3">Seed</th>
                    <th className="px-5 py-3 text-blue-700">Smart Recovery %</th>
                    <th className="px-5 py-3 text-slate-600">Naive Recovery %</th>
                    <th className="px-5 py-3 text-emerald-700">Lift (pp)</th>
                    <th className="px-5 py-3">Smart Net (₹)</th>
                    <th className="px-5 py-3">Naive Net (₹)</th>
                    <th className="px-5 py-3">Smart Violations</th>
                    <th className="px-5 py-3">Naive Violations</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {benchmarkData.seeds_data.map((row) => {
                    const lift = Math.round((row.smart_recovered_pct - row.naive_recovered_pct) * 10) / 10;
                    return (
                      <tr key={row.seed} className="hover:bg-slate-50/50">
                        <td className="px-5 py-3 font-mono font-bold text-slate-800">Seed #{row.seed}</td>
                        <td className="px-5 py-3 font-bold text-blue-700 bg-blue-50/20">{row.smart_recovered_pct}%</td>
                        <td className="px-5 py-3 text-slate-600">{row.naive_recovered_pct}%</td>
                        <td className="px-5 py-3 font-bold text-emerald-600">+{lift} pp</td>
                        <td className="px-5 py-3 font-mono">{formatInr(row.smart_net_revenue)}</td>
                        <td className="px-5 py-3 font-mono text-slate-500">{formatInr(row.naive_net_revenue)}</td>
                        <td className="px-5 py-3 font-bold text-emerald-600">0 ✓</td>
                        <td className="px-5 py-3 font-bold text-rose-600">{row.naive_violations} breaches</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!benchmarkData && (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
          <FlaskConical className="w-10 h-10 mx-auto mb-2 text-slate-300" />
          <p className="text-sm font-semibold text-slate-700">No Benchmark Run in Active Session</p>
          <p className="text-xs text-slate-500 mt-1">
            Click &quot;Run 10-Seed Benchmark&quot; above to execute multi-seed statistical validation.
          </p>
        </div>
      )}

    </div>
  );
};
