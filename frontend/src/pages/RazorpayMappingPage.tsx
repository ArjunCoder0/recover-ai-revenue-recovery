import React, { useState, useEffect } from 'react';
import {
  Map,
  Server,
  Zap,
  ShieldCheck,
  Cpu,
  Layers,
  CheckCircle2,
  ExternalLink,
  Code2,
  Database,
  Lock,
} from 'lucide-react';
import { api } from '../api/client';
import { IntegrationMapData } from '../types';

export const RazorpayMappingPage: React.FC = () => {
  const [mapData, setMapData] = useState<IntegrationMapData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const fetchMap = async () => {
      setLoading(true);
      try {
        const res = await api.getIntegrationMap();
        if (isMounted) setMapData(res);
      } catch (err) {
        console.error('Failed to load integration map:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchMap();
    return () => {
      isMounted = false;
    };
  }, []);

  if (loading || !mapData) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-3" />
        <span className="ml-3 font-medium text-sm">Loading integration architecture map...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Title */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Razorpay Integration & Architecture Mapping
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          How RECOVER maps to official Razorpay recurring billing APIs, webhook subscriptions, and security layers.
        </p>
      </div>

      {/* Production Readiness Callout */}
      <div className="bg-gradient-to-r from-blue-900 via-slate-900 to-blue-950 text-white rounded-2xl p-6 shadow-md border border-slate-800">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-blue-600 text-white flex-shrink-0">
            <Server className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-blue-500/40 text-blue-200 border border-blue-400/30">
                PROTOTYPE → PRODUCTION READY
              </span>
              <span className="text-xs text-slate-300">Drop-In Architecture</span>
            </div>
            <h2 className="text-base font-bold text-white mt-2">
              From Local Simulation to Live Razorpay Webhooks
            </h2>
            <p className="text-xs text-slate-300 leading-relaxed mt-1">
              RECOVER was architected from day 1 with production schema fidelity. The local <code className="text-blue-300">MockRazorpay</code> engine mimics canonical Razorpay payloads, event headers, and idempotency keys verbatim.
              Deploying to production requires zero changes to the Decision Engine or Policy Fence: only swapping the mock adapter for live Razorpay Python SDK keys.
            </p>
          </div>
        </div>
      </div>

      {/* Webhook Events Mapping */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Razorpay Webhook Events Subscribed
            </h3>
            <p className="text-xs text-slate-500">
              Asynchronous event triggers consumed by the RECOVER idempotency pipeline
            </p>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-100 text-slate-600">
            HMAC SHA-256 Verified
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-5 py-3">Webhook Event</th>
                <th className="px-5 py-3">Gateway Trigger Cause</th>
                <th className="px-5 py-3">Pipeline Ingestion Handler</th>
                <th className="px-5 py-3">RECOVER System Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {mapData.webhook_events.map((ev, i) => (
                <tr key={i} className="hover:bg-slate-50/50">
                  <td className="px-5 py-3.5 font-mono font-bold text-blue-700">{ev.event}</td>
                  <td className="px-5 py-3.5 text-slate-700">{ev.trigger}</td>
                  <td className="px-5 py-3.5 font-mono text-slate-500 text-[11px]">{ev.handled_by}</td>
                  <td className="px-5 py-3.5 text-slate-800">{ev.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* REST API Endpoints Mapping */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900">
            Razorpay REST API Endpoints Invoked
          </h3>
          <p className="text-xs text-slate-500">
            Downstream outbound actions executed when AI arms win
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-5 py-3">Method</th>
                <th className="px-5 py-3">API Route</th>
                <th className="px-5 py-3">Business Purpose</th>
                <th className="px-5 py-3">Local Simulator Binding</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {mapData.api_endpoints.map((apiItem, i) => (
                <tr key={i} className="hover:bg-slate-50/50">
                  <td className="px-5 py-3.5">
                    <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                      {apiItem.method}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-mono font-bold text-slate-800">{apiItem.endpoint}</td>
                  <td className="px-5 py-3.5 text-slate-700">{apiItem.purpose}</td>
                  <td className="px-5 py-3.5 font-mono text-emerald-700 font-semibold">{apiItem.simulator}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* System Layer Stack */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 mb-4">
          Production Architecture Layer Stack
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mapData.architecture_layers.map((layer, i) => (
            <div key={i} className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600">
                Layer {i + 1}: {layer.layer}
              </span>
              <p className="text-xs font-bold text-slate-900">{layer.component}</p>
              <p className="text-[11px] text-slate-500 flex items-center gap-1 mt-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                <span>{layer.mock_status}</span>
              </p>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
};
