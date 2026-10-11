import React from 'react';

export const fmt = (n, d = 0) => (n == null || isNaN(n) ? '—' : Number(n).toFixed(d));

const RATING = {
  good: 'bg-emerald-100 text-emerald-700 ring-emerald-200',
  moderate: 'bg-amber-100 text-amber-700 ring-amber-200',
  limit: 'bg-rose-100 text-rose-700 ring-rose-200',
};
const GI = {
  low: 'bg-emerald-50 text-emerald-700',
  medium: 'bg-amber-50 text-amber-700',
  high: 'bg-rose-50 text-rose-700',
};
export const GLUCOSE_BG = {
  normal: 'bg-emerald-500', elevated: 'bg-amber-500', high: 'bg-rose-500', unknown: 'bg-slate-400',
};

export function Card({ title, right, children, className = '' }) {
  return (
    <div className={`rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex items-center justify-between gap-2">
          {title && <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h3>}
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

export function RatingChip({ rating }) {
  if (!rating) return null;
  return <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${RATING[rating] || ''}`}>{rating}</span>;
}

export function GiChip({ gi, cat }) {
  if (gi == null) return null;
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${GI[cat] || 'bg-slate-100 text-slate-600'}`}>GI {gi}</span>;
}

export function PriorityTag({ p }) {
  const s = { high: 'bg-rose-100 text-rose-700', medium: 'bg-amber-100 text-amber-700', low: 'bg-emerald-100 text-emerald-700' };
  return <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${s[p] || ''}`}>{p}</span>;
}

export function Progress({ label, value, target, unit, mode }) {
  const pct = target > 0 ? Math.min(100, (value / target) * 100) : 0;
  let color = 'bg-brand-500';
  if (mode === 'budget') color = value > target ? 'bg-rose-500' : pct >= 80 ? 'bg-amber-500' : 'bg-emerald-500';
  else if (mode === 'min') color = value >= target ? 'bg-emerald-500' : 'bg-amber-500';
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium text-slate-600">{label}</span>
        <span className="tabular-nums text-slate-500">{fmt(value)} / {fmt(target)} {unit}</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex h-full min-h-[40vh] items-center justify-center gap-3 text-slate-400">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
      {label}
    </div>
  );
}

export function Button({ children, variant = 'primary', className = '', ...props }) {
  const styles = {
    primary: 'bg-brand-600 text-white hover:bg-brand-700',
    soft: 'bg-brand-50 text-brand-700 hover:bg-brand-100',
    dark: 'bg-slate-800 text-white hover:bg-slate-700',
    ghost: 'text-slate-500 hover:bg-slate-100',
    danger: 'bg-rose-50 text-rose-600 hover:bg-rose-100',
  };
  return (
    <button className={`rounded-xl px-4 py-2 text-sm font-semibold transition disabled:opacity-50 ${styles[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

const MICROS = [
  ['calcium_mg', 'Calcium', 'mg'], ['iron_mg', 'Iron', 'mg'],
  ['magnesium_mg', 'Magnesium', 'mg'], ['zinc_mg', 'Zinc', 'mg'],
  ['potassium_mg', 'Potassium', 'mg'], ['vitamin_a_mcg', 'Vitamin A', 'mcg'],
  ['vitamin_c_mg', 'Vitamin C', 'mg'], ['vitamin_d_mcg', 'Vitamin D', 'mcg'],
  ['vitamin_b12_mcg', 'Vitamin B12', 'mcg'], ['folate_mcg', 'Folate', 'mcg'],
];

export function MicroGrid({ totals, targets }) {
  totals = totals || {};
  targets = targets || {};
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {MICROS.map(([key, label, unit]) => {
        const val = totals[key] || 0;
        const tgt = targets[key] || 0;
        const pct = tgt > 0 ? Math.min(100, (val / tgt) * 100) : 0;
        const met = tgt > 0 && val >= tgt;
        return (
          <div key={key} className="rounded-xl bg-slate-50 p-2.5">
            <div className="flex justify-between text-xs">
              <span className="font-medium text-slate-600">{label}</span>
              <span className="tabular-nums text-slate-400">{fmt(val, val < 10 ? 1 : 0)}{tgt ? `/${fmt(tgt)}` : ''}</span>
            </div>
            {tgt > 0 && (
              <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div className={`h-full rounded-full ${met ? 'bg-emerald-500' : 'bg-brand-400'}`} style={{ width: `${pct}%` }} />
              </div>
            )}
            <div className="mt-0.5 text-[10px] text-slate-400">{unit}</div>
          </div>
        );
      })}
    </div>
  );
}
