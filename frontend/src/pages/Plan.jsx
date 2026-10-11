import React, { useState, useEffect } from 'react';
import { api } from '../lib/supabase';
import { localDay } from '../lib/day';
import { useToast } from '../components/Toast';
import { Card, Button, Spinner, fmt } from '../components/ui';
import FoodExchange from '../components/FoodExchange';

export default function Plan() {
  const toast = useToast();
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);

  const generate = async () => {
    setBusy(true);
    try { setPlan(await api.get(`/api/plan?day=${localDay()}`)); }
    catch (e) { toast(e.message, 'error'); }
    finally { setBusy(false); }
  };
  useEffect(() => { generate(); }, []);

  return (
    <div className="space-y-5 fade-in">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">A full day sized to your carb budget, built from low-GI foods.</p>
        <Button onClick={generate} disabled={busy}>{busy ? 'Generating…' : 'Regenerate'}</Button>
      </div>
      {!plan && busy && <Spinner label="Building your plan…" />}
      {plan && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {plan.meals.map((m, i) => (
              <Card key={i} title={m.meal_type}>
                <div className="mb-2 text-xs text-slate-400">
                  carb budget ~{fmt(m.carb_budget_g)}g{m.time_hint ? ` · ${m.time_hint}` : ''}
                </div>
                <ul className="space-y-1 text-sm text-slate-600">
                  {m.foods.length ? m.foods.map((f, j) => <li key={j}>• {f}</li>) : <li className="text-slate-400">—</li>}
                </ul>
                <div className="mt-3 border-t border-slate-100 pt-2 text-xs text-slate-500">
                  {fmt(m.nutrition.calories_kcal)} kcal · carbs {fmt(m.nutrition.carbohydrate_g)}g · fiber {fmt(m.nutrition.fiber_g)}g
                </div>
              </Card>
            ))}
          </div>
          <Card title="Day total">
            <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm text-slate-600">
              <span><b>{fmt(plan.total_nutrition.calories_kcal)}</b> kcal</span>
              <span>carbs <b>{fmt(plan.total_nutrition.carbohydrate_g)}</b>g</span>
              <span>protein <b>{fmt(plan.total_nutrition.protein_g)}</b>g</span>
              <span>fiber <b>{fmt(plan.total_nutrition.fiber_g)}</b>g</span>
              <span>sugar <b>{fmt(plan.total_nutrition.sugar_g)}</b>g</span>
            </div>
            {plan.notes.length > 0 && (
              <ul className="mt-3 space-y-1 text-xs text-slate-500">
                {plan.notes.map((n, i) => <li key={i}>• {n}</li>)}
              </ul>
            )}
          </Card>
        </>
      )}
      <FoodExchange toast={toast} />
    </div>
  );
}
