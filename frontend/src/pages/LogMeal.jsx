import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/supabase';
import { localDay, combineDayTime, nowHHMM } from '../lib/day';
import { useData } from '../context/DataContext';
import { useToast } from '../components/Toast';
import { Card, RatingChip, GiChip, Button, fmt } from '../components/ui';

const UNITS = ['serving', 'piece', 'g', 'bowl', 'cup', 'plate', 'glass'];

export default function LogMeal() {
  const { setState, refresh } = useData();
  const toast = useToast();
  const [params] = useSearchParams();
  const [q, setQ] = useState('');
  const [ratingFilter, setRatingFilter] = useState('');
  const [results, setResults] = useState([]);
  const [cart, setCart] = useState([]);
  const [mealType, setMealType] = useState(params.get('meal') || 'breakfast');
  const [day, setDay] = useState(params.get('day') || localDay());
  const [mealTime, setMealTime] = useState(nowHHMM());
  const [parseText, setParseText] = useState('');
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(null); // { existing } when meal type already logged

  const search = useCallback(async (query, rating) => {
    try {
      const data = await api.get(`/api/foods?q=${encodeURIComponent(query)}&rating=${rating}&limit=40`);
      setResults(data.foods);
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => {
    const id = setTimeout(() => search(q, ratingFilter), 180);
    return () => clearTimeout(id);
  }, [q, ratingFilter, search]);

  const addToCart = (food) => setCart((c) => {
    if (c.find((x) => x.food_name === food.food_name)) return c;
    const unit = food.category === 'Fruit' || food.serving_size_g <= 60 ? 'piece' : 'serving';
    return [...c, { food_name: food.food_name, quantity: 1, unit }];
  });
  const addCustom = (name) => setCart((c) => {
    const n = name.trim();
    if (!n || c.find((x) => x.food_name.toLowerCase() === n.toLowerCase())) return c;
    return [...c, { food_name: n, quantity: 1, unit: 'serving', custom: true }];
  });
  const updateCart = (i, patch) => setCart((c) => c.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  const removeCart = (i) => setCart((c) => c.filter((_, j) => j !== i));

  const submit = async (mode) => {
    if (cart.length === 0) return;
    setBusy(true);
    try {
      const data = await api.post('/api/meal', {
        meal_type: mealType,
        items: cart.map((c) => ({ food_name: c.food_name, quantity: Number(c.quantity) || 1, unit: c.unit })),
        day,
        eaten_at: combineDayTime(day, mealTime),
        mode: mode || undefined,
      });
      if (data.status === 'exists') { setPending({ existing: data.existing }); setBusy(false); return; }
      if (day === localDay()) setState(data.state); else refresh();
      setCart([]);
      setPending(null);
      const skipped = (data.unresolved && data.unresolved.length) ? ` (couldn't identify: ${data.unresolved.join(', ')})` : '';
      toast(`Logged ${mealType} for ${day}${skipped}`);
    } catch (e) { toast(e.message, 'error'); }
    finally { setBusy(false); }
  };

  const doParse = async () => {
    if (!parseText.trim()) return;
    setBusy(true);
    try {
      const data = await api.post('/api/meal/parse', { text: parseText });
      if (!data.ok) { toast(data.reason, 'error'); return; }
      setCart((c) => {
        const names = new Set(c.map((x) => x.food_name.toLowerCase()));
        const added = data.items.filter((it) => !names.has(it.food_name.toLowerCase()))
          .map((it) => ({ food_name: it.food_name, quantity: it.quantity, unit: it.unit }));
        return [...c, ...added];
      });
      toast('Parsed — review items, then log.');
    } catch (e) { toast(e.message, 'error'); }
    finally { setBusy(false); }
  };

  const input = 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-brand-500';

  return (
    <div className="grid gap-5 fade-in lg:grid-cols-5">
      <div className="space-y-4 lg:col-span-3">
        <Card title="Find foods">
          <div className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search dishes, fruits, drinks…" className={input} />
            <select value={ratingFilter} onChange={(e) => setRatingFilter(e.target.value)} className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-brand-500">
              <option value="">All</option><option value="good">Good</option><option value="moderate">Moderate</option><option value="limit">Limit</option>
            </select>
          </div>
          <div className="mt-4 max-h-[460px] space-y-2 overflow-y-auto pr-1">
            {q.trim() && !results.some((f) => f.food_name.toLowerCase() === q.trim().toLowerCase()) && (
              <button onClick={() => { addCustom(q); setQ(''); setResults([]); }}
                className="flex w-full items-center justify-between rounded-xl border border-dashed border-brand-300 bg-brand-50/50 p-3 text-left hover:bg-brand-50">
                <span className="text-sm text-slate-600">Add <b>"{q.trim()}"</b> as a custom food</span>
                <span className="text-xs font-semibold text-brand-700">+ Add (AI will estimate)</span>
              </button>
            )}
            {results.map((f) => (
              <div key={f.food_id} className="flex items-center justify-between rounded-xl border border-slate-100 p-3 hover:bg-slate-50">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium text-slate-700">{f.food_name}</span>
                    <RatingChip rating={f.diabetes_rating} />
                    <GiChip gi={f.glycemic_index} cat={f.gi_category} />
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    {f.category} · {fmt(f.serving_size_g)}g · {fmt(f.calories_kcal)} kcal · carbs {fmt(f.carbohydrate_g)}g
                  </div>
                </div>
                <Button variant="soft" onClick={() => addToCart(f)} className="ml-3 px-3 py-1.5">Add</Button>
              </div>
            ))}
            {results.length === 0 && !q.trim() && <p className="py-6 text-center text-sm text-slate-400">Search to find foods, or type anything and add it as custom.</p>}
          </div>
        </Card>

        <Card title="Or describe your meal (AI)">
          <div className="flex gap-2">
            <input value={parseText} onChange={(e) => setParseText(e.target.value)} placeholder='e.g. "2 idlis and a cup of sambar"' className={input} />
            <Button variant="dark" onClick={doParse} disabled={busy} className="shrink-0">Parse</Button>
          </div>
        </Card>
      </div>

      <div className="lg:col-span-2">
        <Card title="This meal" className="sticky top-5">
          <div className="mb-3 grid grid-cols-2 gap-2">
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-500">Date {day !== localDay() && <span className="text-amber-600">(back-dated)</span>}</label>
              <input type="date" max={localDay()} value={day} onChange={(e) => setDay(e.target.value)} className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Meal type</label>
              <select value={mealType} onChange={(e) => setMealType(e.target.value)} className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500">
                {['breakfast', 'lunch', 'dinner', 'snack'].map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Time eaten</label>
              <input type="time" value={mealTime} onChange={(e) => setMealTime(e.target.value)} className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500" />
            </div>
          </div>
          {cart.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-400">Add foods to build your meal.</p>
          ) : (
            <ul className="space-y-2">
              {cart.map((c, i) => (
                <li key={i} className="rounded-xl bg-slate-50 p-2.5">
                  <div className="flex items-center justify-between">
                    <span className="truncate text-sm font-medium text-slate-700">{c.food_name}</span>
                    <button onClick={() => removeCart(i)} className="text-slate-400 hover:text-rose-500">✕</button>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <input type="number" min="0" step="0.5" value={c.quantity} onChange={(e) => updateCart(i, { quantity: e.target.value })} className="w-20 rounded-lg border border-slate-200 px-2 py-1 text-sm" />
                    <select value={c.unit} onChange={(e) => updateCart(i, { unit: e.target.value })} className="flex-1 rounded-lg border border-slate-200 px-2 py-1 text-sm">
                      {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {pending ? (
            <div className="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
              You already logged <b>{mealType}</b> today
              {' '}({fmt(pending.existing.nutrition.carbohydrate_g)}g carbs).
              Did you eat this <i>as well</i>, or is this a correction?
              <div className="mt-3 flex gap-2">
                <Button variant="soft" onClick={() => submit('merge')} disabled={busy} className="flex-1">Add to it</Button>
                <Button variant="dark" onClick={() => submit('replace')} disabled={busy} className="flex-1">Replace</Button>
                <Button variant="ghost" onClick={() => setPending(null)} className="px-3">Cancel</Button>
              </div>
            </div>
          ) : (
            <Button onClick={() => submit()} disabled={busy || cart.length === 0} className="mt-4 w-full">Log this meal</Button>
          )}
        </Card>
      </div>
    </div>
  );
}
