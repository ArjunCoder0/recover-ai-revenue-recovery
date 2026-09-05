import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Send,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';
import { HumanReviewItem } from '../types';
import { ClassBadge } from '../components/Badge';

export const HumanReviewPage: React.FC = () => {
  const [queue, setQueue] = useState<HumanReviewItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionInProgress, setActionInProgress] = useState<number | null>(null);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await api.getHumanReviewQueue();
      setQueue(res);
    } catch (err) {
      console.error('Failed to load human review queue:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleAction = async (caseId: number, action: 'APPROVE' | 'REJECT') => {
    setActionInProgress(caseId);
    setNotification(null);
    try {
      const note = notes[caseId] || (action === 'APPROVE' ? 'Approved via HITL console' : 'Case dismissed');
      const res = await api.executeHumanAction(caseId, action, note);
      if (res.success) {
        setNotification({
          type: 'success',
          text: `Case #${caseId} successfully ${action === 'APPROVE' ? 'approved (PAYMENT_LINK dispatched)' : 'rejected and closed (STOP)'}.`,
        });
        // Remove from local queue
        setQueue((prev) => prev.filter((item) => item.case_id !== caseId));
      }
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: `Action failed for Case #${caseId}: ${err.message}`,
      });
    } finally {
      setActionInProgress(null);
    }
  };

  const formatInr = (val: number) => `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Human-in-the-Loop Review Queue
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Supervised revenue operations for high-value transactions, elevated churn risks, and customer-action escalations.
          </p>
        </div>
        <button
          onClick={fetchQueue}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Queue
        </button>
      </div>

      {/* HITL Purpose Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-amber-50 text-amber-600 flex-shrink-0">
            <UserCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Why Human Supervision Matters in B2B / High-Ticket Recovery
            </h2>
            <p className="text-xs text-slate-600 leading-relaxed mt-1">
              For high-value subscriptions (≥ ₹2,500 threshold), blind retries risk alienating VIP customers.
              RECOVER automatically escalates these cases into this review queue.
              Human operators can verify account context, approve payment links, or manually write off invoices.
              Every human intervention is signed and recorded directly into the append-only audit trail.
            </p>
          </div>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div
          className={`p-4 rounded-xl text-xs font-semibold flex items-center gap-2 animate-in fade-in duration-150 ${
            notification.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {notification.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          )}
          <span>{notification.text}</span>
        </div>
      )}

      {/* Queue Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">
            Pending Escalation Queue ({queue.length} cases)
          </h3>
          <span className="text-xs text-slate-400 font-mono">Sorted by Value (High to Low)</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
            Loading escalation items...
          </div>
        ) : queue.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-xs">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-80" />
            <p className="text-sm font-semibold text-slate-700">Queue is Clear!</p>
            <p className="mt-0.5">No transactions currently exceed the escalation thresholds.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
                <tr>
                  <th className="px-5 py-3">Case</th>
                  <th className="px-5 py-3">Amount</th>
                  <th className="px-5 py-3">Classification</th>
                  <th className="px-5 py-3">Escalation Trigger</th>
                  <th className="px-5 py-3">Recommended</th>
                  <th className="px-5 py-3">Reviewer Note</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {queue.map((item) => (
                  <tr key={item.case_id} className="hover:bg-slate-50/50">
                    <td className="px-5 py-4 font-mono font-bold text-slate-900">
                      #{item.case_id}
                    </td>
                    <td className="px-5 py-4 font-bold text-slate-900">
                      {formatInr(item.amount)}
                    </td>
                    <td className="px-5 py-4">
                      <div className="space-y-1">
                        <ClassBadge failureClass={item.failure_class} />
                        <p className="text-[11px] font-mono text-slate-500">{item.error_code}</p>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-slate-600 max-w-xs text-[11px]">
                      {item.reason}
                    </td>
                    <td className="px-5 py-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                        {item.recommended_action}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <input
                        type="text"
                        placeholder="Optional note..."
                        value={notes[item.case_id] || ''}
                        onChange={(e) =>
                          setNotes({ ...notes, [item.case_id]: e.target.value })
                        }
                        className="w-36 px-2 py-1 text-[11px] rounded border border-slate-200 bg-white"
                      />
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleAction(item.case_id, 'APPROVE')}
                          disabled={actionInProgress === item.case_id}
                          className="px-3 py-1 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors shadow-sm disabled:opacity-50"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleAction(item.case_id, 'REJECT')}
                          disabled={actionInProgress === item.case_id}
                          className="px-3 py-1 text-xs font-semibold text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
};
