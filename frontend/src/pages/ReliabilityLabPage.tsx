import React, { useState, useEffect } from 'react';
import {
  Server,
  Zap,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Database,
  Send,
  RefreshCw,
  Clock,
  Layers,
} from 'lucide-react';
import { api } from '../api/client';
import { ReliabilityStats, BlastTestResponse, ReliabilityEvent } from '../types';

export const ReliabilityLabPage: React.FC = () => {
  const [stats, setStats] = useState<ReliabilityStats | null>(null);
  const [events, setEvents] = useState<ReliabilityEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [blasting, setBlasting] = useState<boolean>(false);
  const [blastResult, setBlastResult] = useState<BlastTestResponse | null>(null);

  // Single simulator state
  const [singleErrorCode, setSingleErrorCode] = useState<string>('UPI_TIMEOUT');
  const [singleAmount, setSingleAmount] = useState<number>(2499.0);
  const [singleMethod, setSingleMethod] = useState<string>('upi');
  const [simulatingSingle, setSimulatingSingle] = useState<boolean>(false);
  const [singleResult, setSingleResult] = useState<any | null>(null);

  const fetchData = async () => {
    try {
      const [statsRes, eventsRes] = await Promise.all([
        api.getReliabilityStats(),
        api.getReliabilityEvents(),
      ]);
      setStats(statsRes);
      setEvents(eventsRes);
    } catch (err) {
      console.error('Failed to load reliability data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunBlast = async () => {
    setBlasting(true);
    setBlastResult(null);
    try {
      const res = await api.runBlastTest({
        count: 10,
        error_code: 'INSUFFICIENT_FUNDS',
        amount: 1499.0,
      });
      setBlastResult(res);
      await fetchData();
    } catch (err: any) {
      alert(`Blast test error: ${err.message}`);
    } finally {
      setBlasting(false);
    }
  };

  const handleSimulateSingle = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulatingSingle(true);
    setSingleResult(null);
    try {
      const res = await api.simulateWebhook({
        error_code: singleErrorCode,
        amount: singleAmount,
        method: singleMethod,
      });
      setSingleResult(res);
      await fetchData();
    } catch (err: any) {
      alert(`Simulation error: ${err.message}`);
    } finally {
      setSimulatingSingle(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Clear all idempotency records and event logs?')) return;
    try {
      await api.resetReliability();
      setBlastResult(null);
      setSingleResult(null);
      await fetchData();
    } catch (err: any) {
      alert(`Reset error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner: Prominent MOCK RAZORPAY MODE */}
      <div className="bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-slate-50 border-2 border-amber-500/40 rounded-2xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500 text-white shadow-md shadow-amber-500/20">
              <Server className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-extrabold uppercase tracking-widest px-2 py-0.5 rounded bg-amber-500 text-white">
                  MOCK RAZORPAY MODE
                </span>
                <span className="text-xs font-semibold text-amber-800">100% Local Simulation Active</span>
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Zero external network calls. Webhooks, HMAC signature checks, and SQLite-backed idempotency operate entirely on this machine.
              </p>
            </div>
          </div>
          <button
            onClick={handleReset}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-800 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-sm"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset Idempotency DB
          </button>
        </div>
      </div>

      {/* Aggregate Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-[11px] font-bold uppercase text-slate-400">Total Events Received</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{stats.total_events}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Webhook payloads ingested</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-[11px] font-bold uppercase text-slate-400">Unique Processed</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{stats.processed_count}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">First-time event deliveries</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-[11px] font-bold uppercase text-slate-400">Duplicates Blocked</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{stats.total_duplicates_blocked}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Repetitions blocked by SQLite</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-[11px] font-bold uppercase text-slate-400">Duplicate Debits</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">0</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Zero double charges guaranteed</p>
          </div>
        </div>
      )}

      {/* Interactive 10-Duplicate Burst Blast Lab */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4 mb-5">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-500" />
              Interactive 10-Duplicate Webhook Burst Test
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Fires 10 concurrent threads delivering the EXACT same webhook event simultaneously to verify thread-safe SQLite idempotency.
            </p>
          </div>
          <button
            onClick={handleRunBlast}
            disabled={blasting}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-xl shadow-sm transition-all disabled:opacity-50"
          >
            {blasting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Firing 10 Concurrent Webhooks...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Fire 10-Duplicate Burst
              </>
            )}
          </button>
        </div>

        {/* Blast Result Box */}
        {blastResult && (
          <div className="p-5 rounded-xl bg-slate-50 border-2 border-emerald-500/40 space-y-3 animate-in fade-in duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  {blastResult.status}: IDEMPOTENT
                </span>
                <span className="text-xs font-mono text-slate-500">Event ID: {blastResult.event_id}</span>
              </div>
              <span className="text-xs font-mono text-slate-500">
                Completed in {blastResult.execution_time_ms} ms
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1 text-xs">
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <p className="text-slate-400 text-[10px] uppercase font-bold">Total Bursts</p>
                <p className="text-lg font-bold text-slate-900">{blastResult.total_bursts}</p>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <p className="text-slate-400 text-[10px] uppercase font-bold">Processed</p>
                <p className="text-lg font-bold text-emerald-600">{blastResult.processed}</p>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <p className="text-slate-400 text-[10px] uppercase font-bold">Blocked</p>
                <p className="text-lg font-bold text-blue-600">{blastResult.blocked}</p>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <p className="text-slate-400 text-[10px] uppercase font-bold">Duplicate Charges</p>
                <p className="text-lg font-bold text-emerald-600">{blastResult.duplicate_executions}</p>
              </div>
            </div>

            <p className="text-xs text-emerald-800 font-medium flex items-center gap-1.5 pt-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>{blastResult.message}</span>
            </p>
          </div>
        )}
      </div>

      {/* Single Webhook Dispatcher */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
          <Send className="w-4 h-4 text-purple-600" />
          Single Webhook Event Simulator
        </h2>
        <p className="text-xs text-slate-500 mb-5">
          Simulate an individual payment failure from Razorpay to observe real-time decline classification, policy fence evaluation, and AI arm selection.
        </p>

        <form onSubmit={handleSimulateSingle} className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Decline Reason Code</label>
            <select
              value={singleErrorCode}
              onChange={(e) => setSingleErrorCode(e.target.value)}
              className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-white"
            >
              <option value="INSUFFICIENT_FUNDS">INSUFFICIENT_FUNDS (Soft)</option>
              <option value="UPI_TIMEOUT">UPI_TIMEOUT (Transient)</option>
              <option value="ISSUER_UNAVAILABLE">ISSUER_UNAVAILABLE (Transient)</option>
              <option value="EXPIRED_CARD">EXPIRED_CARD (Action Required)</option>
              <option value="MANDATE_PAUSED">MANDATE_PAUSED (Action Required)</option>
              <option value="MANDATE_REVOKED">MANDATE_REVOKED (Hard)</option>
              <option value="CARD_LOST_STOLEN">CARD_LOST_STOLEN (Hard)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Amount (₹)</label>
            <input
              type="number"
              value={singleAmount}
              onChange={(e) => setSingleAmount(Number(e.target.value))}
              className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Method</label>
            <select
              value={singleMethod}
              onChange={(e) => setSingleMethod(e.target.value)}
              className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-white"
            >
              <option value="upi">UPI Autopay</option>
              <option value="card">Credit / Debit Card</option>
              <option value="netbanking">e-NACH / Netbanking</option>
            </select>
          </div>

          <div>
            <button
              type="submit"
              disabled={simulatingSingle}
              className="w-full py-2 px-4 text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {simulatingSingle ? 'Delivering...' : 'Send Webhook'}
            </button>
          </div>
        </form>

        {singleResult && (
          <div className="mt-4 p-4 rounded-xl bg-purple-50/50 border border-purple-200 text-xs space-y-1">
            <p className="font-bold text-purple-900">Webhook Delivered Successfully:</p>
            <p className="text-slate-700">Status: <span className="font-mono font-semibold">{singleResult.status}</span></p>
            <p className="text-slate-700">AI Action Taken: <span className="font-mono font-semibold text-blue-700">{singleResult.data?.action}</span></p>
            <p className="text-slate-700">Case State: <span className="font-mono font-semibold">{singleResult.data?.state}</span></p>
          </div>
        )}
      </div>

      {/* Recent Webhook Events Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">
            Recent Ingested Events Log
          </h3>
          <span className="text-xs text-slate-500 font-mono">
            {events.length} records in active memory
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-5 py-3">Event ID</th>
                <th className="px-5 py-3">Payment ID</th>
                <th className="px-5 py-3">Decline Code</th>
                <th className="px-5 py-3">Amount</th>
                <th className="px-5 py-3">Burst Count</th>
                <th className="px-5 py-3">Processed</th>
                <th className="px-5 py-3">Blocked</th>
                <th className="px-5 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-slate-400">
                    No webhooks processed yet. Click &quot;Fire 10-Duplicate Burst&quot; above to run the test.
                  </td>
                </tr>
              ) : (
                events.map((ev, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50">
                    <td className="px-5 py-3 font-mono text-slate-800">{ev.event_id}</td>
                    <td className="px-5 py-3 font-mono text-slate-500">{ev.payment_id}</td>
                    <td className="px-5 py-3 font-semibold text-slate-700">{ev.error_code}</td>
                    <td className="px-5 py-3 font-mono">₹{ev.amount?.toLocaleString('en-IN')}</td>
                    <td className="px-5 py-3 font-mono">{ev.total_burst}</td>
                    <td className="px-5 py-3 font-mono font-bold text-emerald-600">{ev.processed}</td>
                    <td className="px-5 py-3 font-mono font-bold text-blue-600">{ev.blocked}</td>
                    <td className="px-5 py-3 text-slate-400 font-mono text-[11px]">{ev.timestamp}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
