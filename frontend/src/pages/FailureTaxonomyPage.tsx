import React, { useState, useEffect } from 'react';
import {
  Layers,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Send,
  XCircle,
  CheckCircle2,
  HelpCircle,
  FileText,
} from 'lucide-react';
import { api } from '../api/client';
import { TaxonomyData, FailureClass } from '../types';
import { ClassBadge } from '../components/Badge';

export const FailureTaxonomyPage: React.FC = () => {
  const [data, setData] = useState<TaxonomyData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const fetchTaxonomy = async () => {
      setLoading(true);
      try {
        const res = await api.getTaxonomy();
        if (isMounted) setData(res);
      } catch (err) {
        console.error('Failed to load taxonomy:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchTaxonomy();
    return () => {
      isMounted = false;
    };
  }, []);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-3" />
        <span className="ml-3 font-medium text-sm">Loading failure taxonomy mapping...</span>
      </div>
    );
  }

  const classCards: Array<{
    key: FailureClass;
    title: string;
    subtitle: string;
    border: string;
    bg: string;
    badge: string;
    playbook: string;
    forbidden: string;
    regulatory: string;
  }> = [
    {
      key: 'SOFT',
      title: 'SOFT DECLINE',
      subtitle: 'Temporary liquidity shortage on valid payment instruments',
      border: 'border-blue-300',
      bg: 'bg-blue-50/40',
      badge: 'blue',
      playbook: 'Defer retry to customer salary day (days 1–5 of month) or allow 24h backoff cooldown. Do not spam retries.',
      forbidden: 'Immediate rapid retries (wastes gateway transaction fees with near-zero success).',
      regulatory: 'Standard debit reattempts permitted subject to merchant retry caps.',
    },
    {
      key: 'TRANSIENT',
      title: 'TRANSIENT FAILURE',
      subtitle: 'Temporary PSP, NPCI, or issuing bank technical outage',
      border: 'border-amber-300',
      bg: 'bg-amber-50/40',
      badge: 'amber',
      playbook: 'Rapid cooldown retry (2h–24h). High recovery probability (>70%) once bank core systems recover.',
      forbidden: 'Prematurely canceling or writing off invoices before bank recovers.',
      regulatory: 'NPCI UPI Autopay re-routing permitted once gateway health recovers.',
    },
    {
      key: 'ACTION_REQUIRED',
      title: 'CUSTOMER ACTION REQUIRED',
      subtitle: 'Payment instrument unusable or mandate paused in bank app',
      border: 'border-purple-300',
      bg: 'bg-purple-50/40',
      badge: 'purple',
      playbook: 'Direct reattempts blocked. Send smart Razorpay Payment Link via WhatsApp/SMS so user can update method or pay in 1 tap.',
      forbidden: 'Automated backend debit retries (guaranteed to fail repeatedly).',
      regulatory: 'Customer consent required before any new debit instrument is bound.',
    },
    {
      key: 'HARD',
      title: 'HARD DECLINE',
      subtitle: 'Mandate revoked by user or card reported lost/stolen',
      border: 'border-rose-300',
      bg: 'bg-rose-50/40',
      badge: 'rose',
      playbook: 'STRICT ZERO RETRIES. Terminate automated pipeline immediately. Offer manual link or escalate to agent.',
      forbidden: 'ANY automated reattempt. Retrying revoked mandates is an explicit regulatory breach.',
      regulatory: 'RBI Master Directions on Recurring Transactions & Card Network rules strictly prohibit re-presentment.',
    },
  ];

  return (
    <div className="space-y-6">
      
      {/* Title */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Decline Classification & Clinical Recovery Taxonomy
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Every raw gateway error code maps into one of 4 clinical decline classes, determining allowed policy arms and AI recovery strategies.
        </p>
      </div>

      {/* 4 Clinical Classes Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {classCards.map((card) => {
          const classInfo = data.classes[card.key];
          return (
            <div
              key={card.key}
              className={`rounded-2xl border ${card.border} ${card.bg} p-6 shadow-sm flex flex-col justify-between space-y-4`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <ClassBadge failureClass={card.key} />
                    <span className="text-sm font-bold text-slate-900">{card.title}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-600 mb-3">{card.subtitle}</p>

                <div className="space-y-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-white/80 border border-slate-200/80">
                    <span className="font-bold text-slate-800">Associated Decline Codes: </span>
                    <span className="font-mono text-slate-600">
                      {classInfo?.codes.join(', ')}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-white/80 border border-slate-200/80">
                    <span className="font-bold text-emerald-800">Recovery Playbook: </span>
                    <span className="text-slate-700">{card.playbook}</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-white/80 border border-slate-200/80">
                    <span className="font-bold text-rose-800">Strictly Forbidden: </span>
                    <span className="text-slate-700">{card.forbidden}</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                <span>Regulatory Mandate: {card.regulatory}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Gateway Error Code Directory Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900">
            Gateway Decline Code Clinical Directory
          </h3>
          <p className="text-xs text-slate-500">
            Comprehensive mapping from raw Razorpay / Issuer decline codes to clinical interpretations and actions
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-5 py-3">Error Code</th>
                <th className="px-5 py-3">Class</th>
                <th className="px-5 py-3">Clinical Diagnosis</th>
                <th className="px-5 py-3">Recovery Rail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {Object.entries(data.code_meanings).map(([code, meaning]) => {
                // Find class
                let matchedClass: FailureClass = 'SOFT';
                for (const [fc, info] of Object.entries(data.classes)) {
                  if (info.codes.includes(code)) {
                    matchedClass = fc as FailureClass;
                    break;
                  }
                }
                return (
                  <tr key={code} className="hover:bg-slate-50/50">
                    <td className="px-5 py-3.5 font-mono font-bold text-slate-900">{code}</td>
                    <td className="px-5 py-3.5">
                      <ClassBadge failureClass={matchedClass} />
                    </td>
                    <td className="px-5 py-3.5 text-slate-600 max-w-md">{meaning}</td>
                    <td className="px-5 py-3.5">
                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {matchedClass === 'HARD'
                          ? 'Zero Auto Retry'
                          : matchedClass === 'ACTION_REQUIRED'
                          ? 'Payment Link'
                          : 'Smart Retry'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
