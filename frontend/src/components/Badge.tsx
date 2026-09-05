import React from 'react';
import { FailureClass, CaseState } from '../types';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'blue' | 'amber' | 'purple' | 'rose' | 'green' | 'slate' | 'default';
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  className = '',
  dot = false,
}) => {
  const variantStyles = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200/80',
    amber: 'bg-amber-50 text-amber-700 border-amber-200/80',
    purple: 'bg-purple-50 text-purple-700 border-purple-200/80',
    rose: 'bg-rose-50 text-rose-700 border-rose-200/80',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
    slate: 'bg-slate-100 text-slate-700 border-slate-200',
    default: 'bg-slate-100 text-slate-700 border-slate-200',
  };

  const dotColors = {
    blue: 'bg-blue-500',
    amber: 'bg-amber-500',
    purple: 'bg-purple-500',
    rose: 'bg-rose-500',
    green: 'bg-emerald-500',
    slate: 'bg-slate-400',
    default: 'bg-slate-400',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${variantStyles[variant]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
};

export const ClassBadge: React.FC<{ failureClass: FailureClass | string }> = ({
  failureClass,
}) => {
  switch (failureClass) {
    case 'SOFT':
      return <Badge variant="blue" dot>SOFT</Badge>;
    case 'TRANSIENT':
      return <Badge variant="amber" dot>TRANSIENT</Badge>;
    case 'ACTION_REQUIRED':
      return <Badge variant="purple" dot>ACTION_REQUIRED</Badge>;
    case 'HARD':
      return <Badge variant="rose" dot>HARD</Badge>;
    default:
      return <Badge variant="slate">{failureClass}</Badge>;
  }
};

export const StateBadge: React.FC<{ state: CaseState | string }> = ({ state }) => {
  switch (state) {
    case 'RECOVERED':
      return <Badge variant="green" dot>RECOVERED</Badge>;
    case 'OPEN':
      return <Badge variant="blue" dot>OPEN</Badge>;
    case 'ESCALATED':
      return <Badge variant="amber" dot>ESCALATED</Badge>;
    case 'EXHAUSTED':
      return <Badge variant="slate">EXHAUSTED</Badge>;
    default:
      return <Badge variant="slate">{state}</Badge>;
  }
};

export const ArmBadge: React.FC<{ arm: string }> = ({ arm }) => {
  if (arm.startsWith('RETRY')) {
    return <Badge variant="blue">{arm}</Badge>;
  }
  if (arm === 'PAYMENT_LINK' || arm === 'SEND_REMINDER') {
    return <Badge variant="purple">{arm}</Badge>;
  }
  if (arm === 'ESCALATE') {
    return <Badge variant="amber">{arm}</Badge>;
  }
  if (arm === 'STOP') {
    return <Badge variant="slate">{arm}</Badge>;
  }
  return <Badge variant="default">{arm}</Badge>;
};
