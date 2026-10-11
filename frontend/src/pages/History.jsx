import React, { useState, useEffect } from 'react';
import { api } from '../lib/supabase';
import { fmtTime } from '../lib/day';
import { useToast } from '../components/Toast';
import { Card, Spinner, fmt, GLUCOSE_BG } from '../components/ui';

export default function History() {
  const toast = useToast();
  const [days, setDays] = useState(null);

  useEffect(() => {
    api.get('/api/history').then((d) => setDays(d.days)).catch((e) => toast(e.message, 'error'));
  }, []);

  if (!days) return <Spinner label="Loading your history…" />;

  return (
    <div className="space-y-5 fade-in">
      <h2 className="text-lg font-bold text-slate-700">Your daily history</h2>
      {days.length === 0 ? (
        <Card><p className="text-sm text-slate-400">Nothing logged yet. Start logging meals, glucose, and activity to build your history.</p></Card>
      ) : (
        days.map((d) => (
          <Card key={d.date}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <span className="text-base font-bold text-slate-800">{d.date}</span>
              <div className="flex items-center gap-2">
                {d.glucose_value != null && (
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold text-white ${GLUCOSE_BG[d.glucose_category] || 'bg-slate-400'}`}>
                    {fmt(d.glucose_value)} mg/dL · {d.glucose_category}
                  </span>
                )}
                {d.activity_min > 0 && (
                  <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">🏃 {fmt(d.activity_min)} min</span>
                )}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {d.meals.length === 0 ? (
                <p className="text-sm text-slate-400">No meals logged.</p>
              ) : d.meals.map((m, i) => (
                <div key={i} className="rounded-xl bg-slate-50 p-3">
                  <div className="flex justify-between">
                    <span className="text-sm font-semibold capitalize text-slate-700">
                      {m.meal_type}{m.eaten_at && <span className="ml-2 text-xs font-normal text-slate-400">{fmtTime(m.eaten_at)}</span>}
                    </span>
                    <span className="text-xs text-slate-500">{fmt((m.nutrition || {}).calories_kcal)} kcal</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{(m.foods || []).map((f) => f.food_name).join(', ') || '—'}</div>
                </div>
              ))}
            </div>

            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 border-t border-slate-100 pt-2 text-xs text-slate-500">
              <span>{fmt(d.totals.calories_kcal)} kcal</span>
              <span>carbs {fmt(d.totals.carbohydrate_g)}g</span>
              <span>sugar {fmt(d.totals.sugar_g)}g</span>
              <span>fiber {fmt(d.totals.fiber_g)}g</span>
              <span>protein {fmt(d.totals.protein_g)}g</span>
            </div>
          </Card>
        ))
      )}
    </div>
  );
}
