import React, { useState } from 'react';
import { api } from '../lib/supabase';
import { Card, RatingChip, GiChip, Button } from './ui';

// Food-exchange / swap finder. Works from the dataset, and falls back to the
// LLM for foods that aren't in the dataset (always returns usable options).
export default function FoodExchange({ toast }) {
  const [food, setFood] = useState('');
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (!food.trim()) return;
    setBusy(true);
    try { setRes(await api.get(`/api/exchanges?food=${encodeURIComponent(food)}`)); }
    catch (e) { toast && toast(e.message, 'error'); }
    finally { setBusy(false); }
  };

  return (
    <Card title="Food exchange — what can I swap?">
      <div className="flex gap-2">
        <input value={food} onChange={(e) => setFood(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder='e.g. "White Rice", "Pepsi", "Gulab Jamun"'
          className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-brand-500" />
        <Button onClick={run} disabled={busy}>Find swaps</Button>
      </div>
      {res && (
        <div className="mt-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-semibold text-slate-700">{res.food_name}</span>
            {res.rating && <RatingChip rating={res.rating} />}
            {res.glycemic_index != null && <GiChip gi={res.glycemic_index} cat={res.rating === 'good' ? 'low' : res.rating === 'limit' ? 'high' : 'medium'} />}
            {res.source === 'llm' && <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">AI estimate</span>}
          </div>
          {res.note && <p className="mt-2 text-xs text-slate-500">{res.note}</p>}
          <div className="mt-2 flex flex-wrap gap-2">
            {res.alternatives.map((a, i) => (
              <span key={i} className="rounded-full bg-brand-50 px-3 py-1 text-xs text-brand-700">
                {a.food_name}{a.glycemic_index != null ? ` (GI ${a.glycemic_index})` : ''}
              </span>
            ))}
            {res.alternatives.length === 0 && <span className="text-xs text-slate-400">No clearly better option found.</span>}
          </div>
        </div>
      )}
    </Card>
  );
}
