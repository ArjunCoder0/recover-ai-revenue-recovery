import React, { useState } from 'react';
import { X, Play, RefreshCw, Sparkles } from 'lucide-react';
import { api } from '../api/client';

interface SimulationModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentN: number;
  currentSeed: number;
  onSuccess: () => void;
}

export const SimulationModal: React.FC<SimulationModalProps> = ({
  isOpen,
  onClose,
  currentN,
  currentSeed,
  onSuccess,
}) => {
  const [n, setN] = useState<number>(currentN || 400);
  const [seed, setSeed] = useState<number>(currentSeed || 42);
  const [llm, setLlm] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.runSimulation({ n, seed, llm });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Simulation execution failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
              <RefreshCw className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Run Recovery Simulation</h3>
              <p className="text-xs text-slate-500">Configure synthetic batch and random seed</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body Form */}
        <form onSubmit={handleRun} className="p-6 space-y-5">
          {error && (
            <div className="p-3 text-xs bg-rose-50 text-rose-700 border border-rose-200 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-sm font-semibold text-slate-700">
                Batch Size (Cases: {n})
              </label>
              <span className="text-xs text-slate-500 font-mono">n={n}</span>
            </div>
            <input
              type="range"
              min="50"
              max="2000"
              step="50"
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-[11px] text-slate-400 mt-1">
              <span>50</span>
              <span>500</span>
              <span>1000</span>
              <span>2000</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">
              Random Seed
            </label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="w-full px-3.5 py-2 rounded-lg border border-slate-200 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              placeholder="e.g. 42"
            />
            <p className="text-xs text-slate-500 mt-1">
              Ensures reproducible transaction distributions and deterministic outcome evaluations.
            </p>
          </div>

          <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50 flex items-start gap-3">
            <input
              type="checkbox"
              id="llm-toggle"
              checked={llm}
              onChange={(e) => setLlm(e.target.checked)}
              className="mt-1 w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
            />
            <div>
              <label htmlFor="llm-toggle" className="text-sm font-semibold text-slate-800 flex items-center gap-1.5 cursor-pointer">
                <Sparkles className="w-4 h-4 text-amber-500" />
                Enable LLM Outreach Rewrite
              </label>
              <p className="text-xs text-slate-500 mt-0.5">
                Uses GEMINI_API_KEY if configured to rewrite customer notices with strict guardrail validation.
                Deterministic templates are used if disabled.
              </p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg shadow-sm hover:shadow transition-all disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Recovery Simulation
                </>
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
