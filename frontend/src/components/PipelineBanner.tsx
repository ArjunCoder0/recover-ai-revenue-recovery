import React from 'react';
import { ArrowRight, ShieldCheck, Cpu, Database, RefreshCw, UserCheck, CheckCircle2 } from 'lucide-react';

export const PipelineBanner: React.FC = () => {
  return (
    <div className="bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 text-white rounded-xl p-3.5 sm:p-4 mb-6 shadow-md border border-slate-800">
      <div className="flex items-center justify-between gap-2 overflow-x-auto text-xs sm:text-sm py-1 font-medium scrollbar-none">
        
        {/* Step 1 */}
        <div className="flex items-center gap-2 whitespace-nowrap px-2 py-1 rounded bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
          <span>Payment Failed</span>
        </div>

        <ArrowRight className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />

        {/* Step 2 */}
        <div className="flex items-center gap-1.5 whitespace-nowrap px-2 py-1 rounded bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <Database className="w-3.5 h-3.5 text-sky-400" />
          <span>Decline Diagnosis</span>
        </div>

        <ArrowRight className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />

        {/* Step 3: Policy Fence */}
        <div className="flex items-center gap-1.5 whitespace-nowrap px-2.5 py-1 rounded bg-rose-500/20 border border-rose-500/40 text-rose-300 font-semibold shadow-glow-sm">
          <ShieldCheck className="w-4 h-4 text-rose-400" />
          <span>Policy Safety Fence (R1–R8)</span>
        </div>

        <ArrowRight className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />

        {/* Step 4: AI */}
        <div className="flex items-center gap-1.5 whitespace-nowrap px-2.5 py-1 rounded bg-blue-500/20 border border-blue-500/40 text-blue-300 font-semibold shadow-glow-sm">
          <Cpu className="w-4 h-4 text-blue-400" />
          <span>Thompson Sampling AI (Max EV)</span>
        </div>

        <ArrowRight className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />

        {/* Step 5: Mock Razorpay & Idempotency */}
        <div className="flex items-center gap-1.5 whitespace-nowrap px-2 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
          <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
          <span>Mock Razorpay Execution</span>
        </div>

        <ArrowRight className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />

        {/* Step 6: Learning & Audit */}
        <div className="flex items-center gap-1.5 whitespace-nowrap px-2 py-1 rounded bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Online Learning & Audit</span>
        </div>

      </div>
    </div>
  );
};
