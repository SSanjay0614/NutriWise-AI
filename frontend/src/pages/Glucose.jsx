import React, { useState } from 'react';
import { api } from '../lib/supabase';
import { localDay } from '../lib/day';
import { useData } from '../context/DataContext';
import { useToast } from '../components/Toast';
import { Card, Button, fmt, GLUCOSE_BG } from '../components/ui';

export default function Glucose() {
  const { state, setState } = useData();
  const toast = useToast();
  const g = state?.glucose;
  const [value, setValue] = useState(g ? g.value_mg_dl : '');
  const [type, setType] = useState(g ? g.reading_type : 'fasting');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const v = Number(value);
    if (!v || v <= 0) { toast('Enter a reading in mg/dL', 'error'); return; }
    setBusy(true);
    try {
      const data = await api.post('/api/glucose', { value_mg_dl: v, reading_type: type, day: localDay() });
      setState(data.state);
      toast(`Logged: ${data.reading.category.toUpperCase()}`);
    } catch (e) { toast(e.message, 'error'); }
    finally { setBusy(false); }
  };

  const input = 'w-full rounded-xl border border-slate-200 px-4 py-2.5 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100';

  return (
    <div className="grid gap-5 fade-in lg:grid-cols-2">
      <Card title="Log blood glucose">
        <p className="mb-4 text-sm text-slate-500">Enter your reading in mg/dL. A fasting reading each morning gives the best daily guidance.</p>
        <label className="mb-1 block text-xs font-medium text-slate-500">Reading (mg/dL)</label>
        <input type="number" value={value} onChange={(e) => setValue(e.target.value)} placeholder="e.g. 110" className={`${input} mb-3 text-lg font-semibold`} />
        <label className="mb-1 block text-xs font-medium text-slate-500">Type</label>
        <div className="mb-4 flex gap-2">
          {['fasting', 'post_meal'].map((t) => (
            <button key={t} onClick={() => setType(t)}
              className={`flex-1 rounded-xl border px-3 py-2 text-sm font-medium ${type === t ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-slate-200 text-slate-500'}`}>
              {t === 'fasting' ? 'Fasting' : 'Post-meal (2h)'}
            </button>
          ))}
        </div>
        <Button onClick={submit} disabled={busy} className="w-full">Save reading</Button>
      </Card>

      <Card title="What this means">
        {g ? (
          <div>
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-extrabold text-slate-800">{fmt(g.value_mg_dl)}</span>
              <span className="text-sm text-slate-400">mg/dL · {g.reading_type}</span>
            </div>
            <span className={`mt-2 inline-block rounded-full px-3 py-1 text-sm font-semibold text-white ${GLUCOSE_BG[g.category]}`}>{g.category.toUpperCase()}</span>
            <p className="mt-3 text-sm text-slate-600">{state.glucose_message}</p>
          </div>
        ) : <p className="text-sm text-slate-400">No reading logged today.</p>}
        <div className="mt-5 space-y-2 border-t border-slate-100 pt-4 text-xs text-slate-500">
          <div className="flex items-center gap-2"><span className="h-3 w-3 rounded-full bg-emerald-500" /> Fasting &lt; 100 — normal</div>
          <div className="flex items-center gap-2"><span className="h-3 w-3 rounded-full bg-amber-500" /> 100–125 — elevated (carb budget ×0.9)</div>
          <div className="flex items-center gap-2"><span className="h-3 w-3 rounded-full bg-rose-500" /> ≥ 126 — high (carb budget ×0.8)</div>
        </div>
      </Card>
    </div>
  );
}
