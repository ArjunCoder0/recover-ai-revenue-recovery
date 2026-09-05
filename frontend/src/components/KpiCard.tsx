import React from 'react';

interface KpiCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  delta?: {
    text: string;
    isPositive: boolean;
  };
  icon?: React.ReactNode;
  variant?: 'blue' | 'green' | 'amber' | 'purple' | 'slate';
  tooltip?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  subValue,
  delta,
  icon,
  variant = 'slate',
  tooltip,
}) => {
  const accentBorder = {
    blue: 'border-l-4 border-l-blue-500',
    green: 'border-l-4 border-l-emerald-500',
    amber: 'border-l-4 border-l-amber-500',
    purple: 'border-l-4 border-l-purple-500',
    slate: 'border-l-4 border-l-slate-400',
  };

  const iconBg = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
    slate: 'bg-slate-100 text-slate-600',
  };

  return (
    <div
      title={tooltip}
      className={`bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm card-hover relative overflow-hidden ${accentBorder[variant]}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
          <p className="text-2xl font-bold text-slate-900 mt-1 tracking-tight">{value}</p>
          {subValue && <p className="text-xs text-slate-500 mt-0.5">{subValue}</p>}
        </div>
        {icon && (
          <div className={`p-2.5 rounded-lg ${iconBg[variant]} flex items-center justify-center`}>
            {icon}
          </div>
        )}
      </div>

      {delta && (
        <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-xs">
          <span
            className={`font-semibold flex items-center ${
              delta.isPositive ? 'text-emerald-600' : 'text-rose-600'
            }`}
          >
            {delta.isPositive ? '↑' : '↓'} {delta.text}
          </span>
          <span className="text-slate-400">vs naive baseline</span>
        </div>
      )}
    </div>
  );
};
