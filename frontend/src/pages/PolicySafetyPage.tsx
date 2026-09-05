import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  Sliders,
  AlertCircle,
  Save,
  RefreshCw,
  Lock,
  Moon,
  Clock,
  IndianRupee,
} from 'lucide-react';
import { api } from '../api/client';
import { PolicyControls, HardRule } from '../types';

interface PolicySafetyPageProps {
  onControlsUpdated: () => void;
}

export const PolicySafetyPage: React.FC<PolicySafetyPageProps> = ({ onControlsUpdated }) => {
  const [controls, setControls] = useState<PolicyControls | null>(null);
  const [rules, setRules] = useState<HardRule[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchPolicy = async () => {
      setLoading(true);
      try {
        const res = await api.getPolicyControls();
        if (isMounted) {
          setControls(res.controls);
          setRules(res.hard_rules);
        }
      } catch (err) {
        console.error('Failed to load policy controls:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchPolicy();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!controls) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await api.updatePolicyControls(controls);
      setMessage({ type: 'success', text: res.message || 'Policy controls updated successfully!' });
      onControlsUpdated();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update policy controls' });
    } finally {
      setSaving(false);
    }
  };

  if (loading || !controls) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-3" />
        <span className="ml-3 font-medium text-sm">Loading policy engine specifications...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Title */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Policy Engine & Safety Fence Dashboard
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Deterministic rules build the boundary. The AI model operates strictly inside it.
        </p>
      </div>

      {/* Safety Philosophy Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-rose-50 text-rose-600 flex-shrink-0">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              The Safety Boundary Concept
            </h2>
            <p className="text-xs text-slate-600 leading-relaxed mt-1">
              In debt recovery, an unconstrained AI model would attempt infinite retries or send urgent spam to force collection.
              RECOVER prevents this by inserting a <strong>pure, deterministic Policy Engine</strong> before the AI.
              The Policy Engine evaluates regulatory constraints (RBI Autopay guidelines, NPCI 24h pre-debit mandates), network rules, and merchant caps to build a safe action fence.
              Every blocked arm is strictly excluded before Expected Value evaluation.
            </p>
          </div>
        </div>
      </div>

      {/* R1-R8 Hard Rules Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Active Regulatory & Safety Constraints (R1 – R8)
            </h3>
            <p className="text-xs text-slate-500">
              Immutable guardrails enforced across all automated recovery workflows
            </p>
          </div>
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" /> 8 / 8 Active
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-5 py-3">Rule ID</th>
                <th className="px-5 py-3">Constraint Name</th>
                <th className="px-5 py-3">Applies To</th>
                <th className="px-5 py-3">Trigger Condition</th>
                <th className="px-5 py-3">Policy Enforcement</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-slate-50/50">
                  <td className="px-5 py-3 font-mono font-bold text-blue-600">{rule.id}</td>
                  <td className="px-5 py-3 font-semibold text-slate-800">{rule.name}</td>
                  <td className="px-5 py-3 text-slate-600 font-mono text-[11px]">{rule.applies_to}</td>
                  <td className="px-5 py-3 text-slate-600">{rule.condition}</td>
                  <td className="px-5 py-3 text-slate-700 font-medium max-w-sm">{rule.policy_action}</td>
                  <td className="px-5 py-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {rule.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Interactive Merchant Policy Controls */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 mb-6 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-slate-100 text-slate-700">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Merchant-Configurable Policy Controls
              </h3>
              <p className="text-xs text-slate-500">
                Adjust business guardrails. Saving automatically re-evaluates the active recovery simulation.
              </p>
            </div>
          </div>
        </div>

        {message && (
          <div
            className={`p-3.5 rounded-xl text-xs font-semibold mb-6 flex items-center gap-2 ${
              message.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            {message.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            <span>{message.text}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Control 1: Max Retries */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Max Retries Per Case
                </label>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                  {controls.max_retries} attempts
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="8"
                step="1"
                value={controls.max_retries}
                onChange={(e) => setControls({ ...controls, max_retries: Number(e.target.value) })}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <p className="text-[11px] text-slate-500">
                Maximum automated debit re-attempts allowed per failed invoice before stopping or escalating.
              </p>
            </div>

            {/* Control 2: Contact Cap */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Customer Contact Cap
                </label>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800">
                  {controls.contact_cap} messages
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="5"
                step="1"
                value={controls.contact_cap}
                onChange={(e) => setControls({ ...controls, contact_cap: Number(e.target.value) })}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
              />
              <p className="text-[11px] text-slate-500">
                Maximum SMS or WhatsApp outreach notices per customer to eliminate communication fatigue.
              </p>
            </div>

            {/* Control 3: High-Value Escalation Threshold */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Escalation Threshold (₹)
                </label>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                  ₹{controls.escalate_above.toLocaleString('en-IN')}
                </span>
              </div>
              <input
                type="number"
                min="0"
                max="50000"
                step="500"
                value={controls.escalate_above}
                onChange={(e) => setControls({ ...controls, escalate_above: Number(e.target.value) })}
                className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="text-[11px] text-slate-500">
                Invoices at or above this amount are automatically routed to the Human Review Queue.
              </p>
            </div>

            {/* Control 4: Minimum Retry Gap */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Min Retry Gap (Hours)
                </label>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                  {controls.min_retry_gap_h}h cooldown
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="48"
                step="1"
                value={controls.min_retry_gap_h}
                onChange={(e) => setControls({ ...controls, min_retry_gap_h: Number(e.target.value) })}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
              />
              <p className="text-[11px] text-slate-500">
                Mandatory delay between successive retry attempts to avoid rapid decline penalties.
              </p>
            </div>

            {/* Control 5: Recovery Window Days */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Recovery Window (Days)
                </label>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-800">
                  {controls.recovery_window_days} days
                </span>
              </div>
              <input
                type="range"
                min="3"
                max="45"
                step="1"
                value={controls.recovery_window_days}
                onChange={(e) => setControls({ ...controls, recovery_window_days: Number(e.target.value) })}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-700"
              />
              <p className="text-[11px] text-slate-500">
                Total duration before a case transitions to terminal EXHAUSTED state.
              </p>
            </div>

            {/* Control 6: Quiet Hours Window */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                  <Moon className="w-3.5 h-3.5 text-indigo-500" /> Quiet Hours (Start – End)
                </label>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                  {controls.quiet_hours[0]}:00 – {controls.quiet_hours[1]}:00
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={controls.quiet_hours[0]}
                  onChange={(e) =>
                    setControls({
                      ...controls,
                      quiet_hours: [Number(e.target.value), controls.quiet_hours[1]],
                    })
                  }
                  className="px-2.5 py-1.5 rounded border border-slate-300 text-xs font-mono bg-white"
                  title="Quiet Hours Start"
                />
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={controls.quiet_hours[1]}
                  onChange={(e) =>
                    setControls({
                      ...controls,
                      quiet_hours: [controls.quiet_hours[0], Number(e.target.value)],
                    })
                  }
                  className="px-2.5 py-1.5 rounded border border-slate-300 text-xs font-mono bg-white"
                  title="Quiet Hours End"
                />
              </div>
              <p className="text-[11px] text-slate-500">
                Night window when outgoing SMS/WhatsApp messages are deferred to the following morning.
              </p>
            </div>

          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-xl shadow-sm hover:shadow transition-all disabled:opacity-50"
            >
              {saving ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Saving & Re-evaluating...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save & Apply Policy Controls
                </>
              )}
            </button>
          </div>
        </form>
      </div>

    </div>
  );
};
