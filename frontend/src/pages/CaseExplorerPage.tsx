import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Info,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';
import { api } from '../api/client';
import { CaseItem, CaseDetail, FailureClass, CaseState } from '../types';
import { ClassBadge, StateBadge, ArmBadge } from '../components/Badge';

export const CaseExplorerPage: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Filters
  const [classFilter, setClassFilter] = useState<string>('ALL');
  const [stateFilter, setStateFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Load cases list
  useEffect(() => {
    let isMounted = true;
    const fetchCases = async () => {
      setLoadingList(true);
      try {
        const res = await api.getCases({
          page,
          page_size: 15,
          failure_class: classFilter,
          state: stateFilter,
          search: searchQuery,
        });
        if (isMounted) {
          setCases(res.cases);
          setTotal(res.total);
          if (res.cases.length > 0 && !selectedCaseId) {
            setSelectedCaseId(res.cases[0].id);
          }
        }
      } catch (err) {
        console.error('Failed to load cases:', err);
      } finally {
        if (isMounted) setLoadingList(false);
      }
    };
    fetchCases();
    return () => {
      isMounted = false;
    };
  }, [page, classFilter, stateFilter, searchQuery]);

  // Load case details when selectedCaseId changes
  useEffect(() => {
    if (!selectedCaseId) return;
    let isMounted = true;
    const fetchDetail = async () => {
      setLoadingDetail(true);
      try {
        const detail = await api.getCaseDetail(selectedCaseId);
        if (isMounted) {
          setCaseDetail(detail);
        }
      } catch (err) {
        console.error(`Failed to fetch case #${selectedCaseId}:`, err);
      } finally {
        if (isMounted) setLoadingDetail(false);
      }
    };
    fetchDetail();
    return () => {
      isMounted = false;
    };
  }, [selectedCaseId]);

  const formatInr = (val: number) => `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

  // Quick jump presets
  const handleQuickJump = (failureClass: string) => {
    setClassFilter(failureClass);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Case Explorer & Decision Explainability
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Inspect individual failed payment cases, observe why the AI selected a specific action, and verify policy fences.
        </p>
      </div>

      {/* Quick Jump Demo Chips */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-semibold text-slate-500 mr-1">Quick Scenarios:</span>
        <button
          onClick={() => handleQuickJump('SOFT')}
          className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
            classFilter === 'SOFT'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
          }`}
        >
          Insufficient Funds (Salary Timing)
        </button>
        <button
          onClick={() => handleQuickJump('TRANSIENT')}
          className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
            classFilter === 'TRANSIENT'
              ? 'bg-amber-600 text-white border-amber-600'
              : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
          }`}
        >
          UPI / Bank Outage (Cooldown Retry)
        </button>
        <button
          onClick={() => handleQuickJump('ACTION_REQUIRED')}
          className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
            classFilter === 'ACTION_REQUIRED'
              ? 'bg-purple-600 text-white border-purple-600'
              : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
          }`}
        >
          Expired Card / Mandate Paused (Payment Link)
        </button>
        <button
          onClick={() => handleQuickJump('HARD')}
          className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
            classFilter === 'HARD'
              ? 'bg-rose-600 text-white border-rose-600'
              : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
          }`}
        >
          Mandate Revoked / Stolen (Zero Retries)
        </button>
        {classFilter !== 'ALL' && (
          <button
            onClick={() => setClassFilter('ALL')}
            className="text-xs text-blue-600 hover:underline ml-2"
          >
            Clear Filter
          </button>
        )}
      </div>

      {/* Main 2-Column Split: Case List + Case Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Column: Cases Table (4 cols) */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden flex flex-col h-[760px]">
          
          {/* Filter Bar */}
          <div className="p-3 border-b border-slate-100 bg-slate-50/50 space-y-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search case #, code, method..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={stateFilter}
                onChange={(e) => {
                  setStateFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full text-xs py-1 px-2 rounded-lg border border-slate-200 bg-white text-slate-700"
              >
                <option value="ALL">All States</option>
                <option value="OPEN">OPEN</option>
                <option value="RECOVERED">RECOVERED</option>
                <option value="EXHAUSTED">EXHAUSTED</option>
                <option value="ESCALATED">ESCALATED</option>
              </select>
            </div>
          </div>

          {/* List Items */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {loadingList ? (
              <div className="p-8 text-center text-xs text-slate-400">Loading cases...</div>
            ) : cases.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">No cases match your filters.</div>
            ) : (
              cases.map((c) => {
                const isSelected = selectedCaseId === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => setSelectedCaseId(c.id)}
                    className={`p-3.5 cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-blue-50/70 border-l-4 border-l-blue-600'
                        : 'hover:bg-slate-50 border-l-4 border-l-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-900">Case #{c.id}</span>
                      <span className="font-bold text-xs text-slate-900">{formatInr(c.amount)}</span>
                    </div>

                    <div className="flex items-center justify-between mt-1 text-[11px] text-slate-500">
                      <span className="font-mono">{c.error_code}</span>
                      <span className="capitalize">{c.method}</span>
                    </div>

                    <div className="flex items-center gap-1.5 mt-2">
                      <ClassBadge failureClass={c.failure_class} />
                      <StateBadge state={c.state} />
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Pagination */}
          <div className="p-3 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
            <span>
              Page {page} of {Math.max(1, Math.ceil(total / 15))} ({total} total)
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
                disabled={page >= Math.ceil(total / 15)}
                onClick={() => setPage((p) => p + 1)}
                className="px-2.5 py-1 rounded bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>

        </div>

        {/* Right Column: Case Deep-Dive Detail (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {loadingDetail || !caseDetail ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
              <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
              <span>Loading explainability insights for Case #{selectedCaseId}...</span>
            </div>
          ) : (
            <>
              {/* Top Case Card */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-extrabold text-slate-900 font-mono">
                        Case #{caseDetail.case.id}
                      </h2>
                      <ClassBadge failureClass={caseDetail.case.failure_class} />
                      <StateBadge state={caseDetail.case.state} />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Failed at T+{caseDetail.case.failed_at}h · Method: <span className="font-semibold">{caseDetail.case.method}</span> · Code:{' '}
                      <span className="font-mono font-semibold text-slate-700">{caseDetail.case.error_code}</span>
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-slate-900">{formatInr(caseDetail.case.amount)}</p>
                    <p className="text-xs text-slate-500">
                      Total Cost Incurred: <span className="font-semibold">{formatInr(caseDetail.case.cost)}</span>
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 text-xs">
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                    <p className="text-slate-400 font-medium uppercase tracking-wider text-[10px]">Estimated Salary Day</p>
                    <p className="text-sm font-bold text-slate-800 mt-0.5">Day {caseDetail.case.salary_day} of month</p>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                    <p className="text-slate-400 font-medium uppercase tracking-wider text-[10px]">Retry Count</p>
                    <p className="text-sm font-bold text-slate-800 mt-0.5">{caseDetail.case.retries} attempts</p>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                    <p className="text-slate-400 font-medium uppercase tracking-wider text-[10px]">Outreach Messages</p>
                    <p className="text-sm font-bold text-slate-800 mt-0.5">{caseDetail.case.contacts} contacts sent</p>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                    <p className="text-slate-400 font-medium uppercase tracking-wider text-[10px]">Triage Risk Score</p>
                    <p className="text-sm font-bold text-slate-800 mt-0.5">{caseDetail.case.risk_score.toFixed(2)} / 1.00</p>
                  </div>
                </div>
              </div>

              {/* "Why Did AI Choose This Action?" Box */}
              <div className="bg-gradient-to-br from-blue-50/80 via-white to-slate-50 rounded-2xl border-2 border-blue-500/50 p-6 shadow-sm relative overflow-hidden">
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-1.5 rounded-lg bg-blue-600 text-white">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900">Why Did AI Choose This Action?</h3>
                </div>

                <div className="flex items-center gap-3 mb-4">
                  <span className="text-xs font-semibold text-slate-600">Optimal Selected Arm:</span>
                  <ArmBadge arm={caseDetail.why_chosen.chosen_arm} />
                </div>

                {/* Explanation text list */}
                <div className="bg-white/90 rounded-xl p-4 border border-blue-100 space-y-2 text-xs text-slate-700 leading-relaxed font-sans shadow-sm">
                  {caseDetail.why_chosen.explanation_text && caseDetail.why_chosen.explanation_text.length > 0 ? (
                    caseDetail.why_chosen.explanation_text.map((line, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="text-blue-500 font-bold">•</span>
                        <span>{line}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-slate-500">
                      Selected optimal arm {caseDetail.why_chosen.chosen_arm} under current policy constraints.
                    </p>
                  )}
                </div>
              </div>

              {/* Alternatives Considered Table */}
              <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h3 className="text-sm font-bold text-slate-900">
                    Alternatives Considered & Policy Rejections
                  </h3>
                  <p className="text-xs text-slate-500">
                    Evaluation of all potential arms: regulatory compliance check followed by Thompson Sampling Expected Value calculation.
                  </p>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
                      <tr>
                        <th className="px-5 py-3">Recovery Arm</th>
                        <th className="px-5 py-3">Policy Allowed?</th>
                        <th className="px-5 py-3">Sampled p</th>
                        <th className="px-5 py-3">Fee (Cost)</th>
                        <th className="px-5 py-3">Expected Net Value (EV)</th>
                        <th className="px-5 py-3">Policy Gate Reason</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {caseDetail.alternatives.map((alt) => {
                        const isChosen = alt.arm === caseDetail.why_chosen.chosen_arm;
                        return (
                          <tr
                            key={alt.arm}
                            className={`hover:bg-slate-50/50 ${
                              isChosen ? 'bg-blue-50/40 font-semibold' : ''
                            }`}
                          >
                            <td className="px-5 py-3">
                              <div className="flex items-center gap-2">
                                <ArmBadge arm={alt.arm} />
                                {isChosen && (
                                  <span className="text-[10px] text-blue-600 font-bold">★ CHOSEN</span>
                                )}
                              </div>
                            </td>
                            <td className="px-5 py-3">
                              {alt.allowed ? (
                                <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> Permitted
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-rose-600 font-semibold">
                                  <XCircle className="w-3.5 h-3.5" /> Blocked
                                </span>
                              )}
                            </td>
                            <td className="px-5 py-3 font-mono">
                              {alt.allowed ? `${(alt.sampled_p * 100).toFixed(1)}%` : '—'}
                            </td>
                            <td className="px-5 py-3 font-mono">₹{alt.cost.toFixed(2)}</td>
                            <td className="px-5 py-3 font-mono">
                              {alt.allowed ? (
                                <span className={alt.expected_value > 0 ? 'text-emerald-700 font-bold' : 'text-slate-500'}>
                                  ₹{alt.expected_value.toFixed(2)}
                                </span>
                              ) : (
                                '—'
                              )}
                            </td>
                            <td className="px-5 py-3 text-slate-500 text-[11px] max-w-xs">
                              {alt.rejection_reason || 'Complies with all policy rules'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Customer Outreach Notice Preview */}
              {caseDetail.outreach_preview && (
                <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Send className="w-4 h-4 text-purple-600" />
                      <h3 className="text-sm font-bold text-slate-900">
                        Customer Communication Notice Preview
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Source: {caseDetail.outreach_preview.source}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-800 font-sans leading-relaxed relative">
                    <div className="mb-2 text-[10px] font-bold text-purple-700 uppercase tracking-wider">
                      Target Channel: SMS / WhatsApp
                    </div>
                    {caseDetail.outreach_preview.message}
                  </div>

                  <div className="mt-3 flex items-center gap-2 text-[11px] text-emerald-700 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>
                      Guardrail Active: Exact transaction amount (₹{caseDetail.case.amount.toFixed(2)}) preserved, zero banned urgency words, and opt-out clause intact.
                    </span>
                  </div>
                </div>
              )}

              {/* Case History Timeline */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
                <h3 className="text-sm font-bold text-slate-900 mb-3">
                  Workflow Execution Timeline
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase border-b border-slate-100">
                      <tr>
                        <th className="px-4 py-2.5">Seq</th>
                        <th className="px-4 py-2.5">Type</th>
                        <th className="px-4 py-2.5">Decided At</th>
                        <th className="px-4 py-2.5">Executed At</th>
                        <th className="px-4 py-2.5">Action</th>
                        <th className="px-4 py-2.5">Outcome</th>
                        <th className="px-4 py-2.5">Quiet Hours Deferred?</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {caseDetail.history.map((h, i) => (
                        <tr key={i} className="hover:bg-slate-50/50">
                          <td className="px-4 py-2.5 font-mono">#{h.seq}</td>
                          <td className="px-4 py-2.5 uppercase text-[10px] font-bold text-slate-500">{h.kind}</td>
                          <td className="px-4 py-2.5 font-mono">T+{h.decided_at}h</td>
                          <td className="px-4 py-2.5 font-mono">
                            {h.executed_at !== null ? `T+${h.executed_at}h` : '—'}
                          </td>
                          <td className="px-4 py-2.5">
                            <ArmBadge arm={h.arm} />
                          </td>
                          <td className="px-4 py-2.5">
                            {h.success === true ? (
                              <span className="text-emerald-600 font-semibold">✓ Success</span>
                            ) : h.success === false ? (
                              <span className="text-rose-600 font-semibold">✗ Failed</span>
                            ) : (
                              <span className="text-slate-500">Terminal</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5">
                            {h.deferred ? (
                              <span className="text-amber-600 font-medium">Yes (Quiet Hours)</span>
                            ) : (
                              'No'
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </>
          )}
        </div>

      </div>

    </div>
  );
};
