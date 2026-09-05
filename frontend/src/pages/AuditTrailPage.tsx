import React, { useState, useEffect } from 'react';
import {
  History,
  Download,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Search,
  RefreshCw,
  FileJson,
} from 'lucide-react';
import { api } from '../api/client';
import { AuditEntry } from '../types';
import { ClassBadge, ArmBadge } from '../components/Badge';

export const AuditTrailPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [policy, setPolicy] = useState<string>('smart');
  const [armFilter, setArmFilter] = useState<string>('ALL');
  const [violationOnly, setViolationOnly] = useState<boolean>(false);
  const [caseIdFilter, setCaseIdFilter] = useState<string>('');

  const fetchAudit = async () => {
    setLoading(true);
    try {
      const parsedCaseId = caseIdFilter.trim() ? Number(caseIdFilter) : undefined;
      const res = await api.getAuditTrail({
        page,
        page_size: 25,
        policy,
        arm: armFilter,
        violation_only: violationOnly,
        case_id: isNaN(parsedCaseId as number) ? undefined : parsedCaseId,
      });
      setLogs(res.logs);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load audit trail:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit();
  }, [page, policy, armFilter, violationOnly, caseIdFilter]);

  const handleExportJson = async () => {
    try {
      const data = await api.exportAuditTrail(policy);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `recover_audit_${policy}_run.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const formatInr = (val: number) => `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Append-Only Tamper-Evident Audit Trail
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Every decision, policy fence check, and execution is recorded with full cryptographic idempotency keys.
          </p>
        </div>
        <button
          onClick={handleExportJson}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors shadow-sm"
        >
          <FileJson className="w-4 h-4 text-blue-600" />
          Export JSON Trail
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          
          {/* Policy Toggle */}
          <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl">
            <button
              onClick={() => {
                setPolicy('smart');
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                policy === 'smart'
                  ? 'bg-white text-blue-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Smart Policy (RECOVER)
            </button>
            <button
              onClick={() => {
                setPolicy('naive');
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                policy === 'naive'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Naive Static Baseline
            </button>
          </div>

          {/* Arm Filter */}
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-500">Action Arm:</label>
            <select
              value={armFilter}
              onChange={(e) => {
                setArmFilter(e.target.value);
                setPage(1);
              }}
              className="text-xs py-1.5 px-2.5 rounded-lg border border-slate-200 bg-white"
            >
              <option value="ALL">All Arms</option>
              <option value="RETRY_2H">RETRY_2H</option>
              <option value="RETRY_24H">RETRY_24H</option>
              <option value="RETRY_SALARY_DAY">RETRY_SALARY_DAY</option>
              <option value="SEND_REMINDER">SEND_REMINDER</option>
              <option value="PAYMENT_LINK">PAYMENT_LINK</option>
              <option value="ESCALATE">ESCALATE</option>
              <option value="STOP">STOP</option>
            </select>
          </div>

          {/* Case ID Search */}
          <div className="w-40">
            <input
              type="text"
              placeholder="Case ID #..."
              value={caseIdFilter}
              onChange={(e) => {
                setCaseIdFilter(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs px-3 py-1.5 rounded-lg border border-slate-200 bg-white"
            />
          </div>

          {/* Violation Only Toggle */}
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={violationOnly}
              onChange={(e) => {
                setViolationOnly(e.target.checked);
                setPage(1);
              }}
              className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
            />
            <span>Violations Only</span>
          </label>

        </div>
      </div>

      {/* Audit Trail Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">
            Audit Records ({total} matching entries)
          </h3>
          <span className="text-xs text-slate-400 font-mono">
            Page {page} of {Math.max(1, Math.ceil(total / 25))}
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
            Loading audit records...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            No audit log entries match your active filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
                <tr>
                  <th className="px-4 py-3">Seq</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Decided At</th>
                  <th className="px-4 py-3">Executed At</th>
                  <th className="px-4 py-3">Case</th>
                  <th className="px-4 py-3">Action Arm</th>
                  <th className="px-4 py-3">Class</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Outcome</th>
                  <th className="px-4 py-3">Quiet Deferred?</th>
                  <th className="px-4 py-3">Violations</th>
                  <th className="px-4 py-3">Rationale Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {logs.map((entry) => (
                  <tr key={entry.seq} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3 font-mono font-bold text-slate-900">#{entry.seq}</td>
                    <td className="px-4 py-3 text-[10px] uppercase font-bold text-slate-500">{entry.kind}</td>
                    <td className="px-4 py-3 font-mono">T+{entry.decided_at}h</td>
                    <td className="px-4 py-3 font-mono">
                      {entry.executed_at !== null ? `T+${entry.executed_at}h` : '—'}
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-blue-600">
                      #{entry.case_id}
                    </td>
                    <td className="px-4 py-3">
                      <ArmBadge arm={entry.arm} />
                    </td>
                    <td className="px-4 py-3">
                      <ClassBadge failureClass={entry.failure_class} />
                    </td>
                    <td className="px-4 py-3 font-mono">{formatInr(entry.amount)}</td>
                    <td className="px-4 py-3">
                      {entry.success === true ? (
                        <span className="text-emerald-600 font-semibold">✓ Success</span>
                      ) : entry.success === false ? (
                        <span className="text-rose-600 font-semibold">✗ Failed</span>
                      ) : (
                        <span className="text-slate-400">Terminal</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {entry.deferred ? (
                        <span className="text-amber-600 font-medium">Yes</span>
                      ) : (
                        <span className="text-slate-400">No</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {entry.violation > 0 ? (
                        <span className="text-rose-600 font-bold px-1.5 py-0.5 rounded bg-rose-50 border border-rose-200">
                          {entry.violation} Breach
                        </span>
                      ) : (
                        <span className="text-emerald-600 font-semibold">0 ✓</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-[11px] max-w-xs truncate" title={entry.rationale?.note}>
                      {entry.rationale?.note || `Optimal EV arm chosen`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
          <span>
            Showing {(page - 1) * 25 + 1} to {Math.min(total, page * 25)} of {total} records
          </span>
          <div className="flex items-center gap-1">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-2.5 py-1 rounded bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
            >
              Prev
            </button>
            <button
              disabled={page >= Math.ceil(total / 25)}
              onClick={() => setPage((p) => p + 1)}
              className="px-2.5 py-1 rounded bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};
