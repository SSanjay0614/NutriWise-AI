import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/supabase';
import { localDay } from '../lib/day';
import { useToast } from '../components/Toast';
import { Card, PriorityTag, Button, Spinner, fmt } from '../components/ui';
import FoodExchange from '../components/FoodExchange';

const VERDICT = {
  good: ['bg-emerald-100 text-emerald-700', 'Good to go'],
  ok: ['bg-amber-100 text-amber-700', 'OK in moderation'],
  caution: ['bg-rose-100 text-rose-700', 'Think twice'],
};

function MealCheck({ toast }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [cart, setCart] = useState([]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  const search = useCallback(async (query) => {
    if (!query.trim()) { setResults([]); return; }
    try { setResults((await api.get(`/api/foods?q=${encodeURIComponent(query)}&limit=8`)).foods); }
    catch (e) { /* ignore */ }
  }, []);
  useEffect(() => { const id = setTimeout(() => search(q), 180); return () => clearTimeout(id); }, [q, search]);

  const check = async () => {
    if (cart.length === 0) return;
    setBusy(true);
    try {
      setRes(await api.post('/api/meal-check', {
        items: cart.map((c) => ({ food_name: c, quantity: 1, unit: 'serving' })),
        day: localDay(),
      }));
    } catch (e) { toast(e.message, 'error'); }
    finally { setBusy(false); }
  };

  return (
    <Card title="“I'm going to eat… is it OK?”">
      <p className="mb-3 text-sm text-slate-500">Add what you're planning to eat and I'll check it against today's budget &amp; glucose.</p>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search a food to add…"
        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-brand-500" />
      {results.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {results.map((f) => (
            <button key={f.food_id} onClick={() => { setCart((c) => c.includes(f.food_name) ? c : [...c, f.food_name]); setQ(''); setResults([]); }}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 hover:bg-brand-50 hover:text-brand-700">
              + {f.food_name}
            </button>
          ))}
        </div>
      )}
      {cart.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {cart.map((c, i) => (
            <span key={i} className="flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-xs text-brand-700">
              {c}<button onClick={() => setCart((x) => x.filter((_, j) => j !== i))} className="text-brand-400 hover:text-rose-500">✕</button>
            </span>
          ))}
        </div>
      )}
      <Button onClick={check} disabled={busy || cart.length === 0} className="mt-3">Check it</Button>

      {res && (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <span className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${VERDICT[res.verdict]?.[0]}`}>
            {VERDICT[res.verdict]?.[1] || res.verdict}
          </span>
          <ul className="mt-3 space-y-1 text-sm text-slate-600">
            {res.reasons.map((r, i) => <li key={i} className="flex gap-2"><span className="text-slate-400">•</span>{r}</li>)}
          </ul>
          <div className="mt-2 text-xs text-slate-400">
            Adds ~{fmt(res.proposed_nutrition.carbohydrate_g)}g carbs · {fmt(res.proposed_nutrition.calories_kcal)} kcal · sugar {fmt(res.proposed_nutrition.sugar_g)}g
          </div>
          {(res.resolved || []).some((r) => r.source === 'llm') && (
            <p className="mt-1 text-xs text-indigo-600">Some items estimated by AI (not in the dataset).</p>
          )}
          {res.swaps.length > 0 && (
            <div className="mt-3 space-y-1">
              {res.swaps.map((s, i) => (
                <div key={i} className="text-sm text-slate-600">
                  Instead of <b>{s.instead_of}</b>, try: {s.try.join(', ')}
                </div>
              ))}
            </div>
          )}
          {res.unresolved.length > 0 && <p className="mt-2 text-xs text-amber-600">Not found: {res.unresolved.join(', ')}</p>}
        </div>
      )}
    </Card>
  );
}

export default function Recommendations() {
  const toast = useToast();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get(`/api/recommendations?day=${localDay()}`).then(setData).catch((e) => toast(e.message, 'error'));
  }, []);

  if (!data) return <Spinner label="Loading recommendations…" />;

  return (
    <div className="space-y-5 fade-in">
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Next-meal priorities">
          {data.recommendations.length === 0 ? (
            <p className="text-sm text-slate-400">Log meals to get recommendations.</p>
          ) : (
            <ul className="space-y-3">
              {data.recommendations.map((r, i) => (
                <li key={i} className="rounded-xl border border-slate-100 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-slate-700">{r.message}</span>
                    <PriorityTag p={r.priority} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{r.reason}</p>
                  {r.suggested_foods.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {r.suggested_foods.map((f, j) => <span key={j} className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700">{f}</span>)}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Best times to eat">
          <div className="space-y-2">
            {Object.entries(data.meal_windows).map(([meal, win]) => (
              <div key={meal} className="flex justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm">
                <span className="font-medium capitalize text-slate-600">{meal}</span>
                <span className="text-slate-500">{win}</span>
              </div>
            ))}
          </div>
          <ul className="mt-4 space-y-2 text-sm text-slate-600">
            {data.timing_tips.map((t, i) => <li key={i} className="flex gap-2"><span className="text-brand-500">→</span>{t}</li>)}
          </ul>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <FoodExchange toast={toast} />
        <MealCheck toast={toast} />
      </div>
    </div>
  );
}
