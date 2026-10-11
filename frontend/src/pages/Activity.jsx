import React, { useState, useEffect } from 'react';
import { api } from '../lib/supabase';
import { localDay, combineDayTime, nowHHMM, fmtTime } from '../lib/day';
import { useData } from '../context/DataContext';
import { useToast } from '../components/Toast';
import { Card, Button, fmt } from '../components/ui';

export default function Activity() {
  const { state, setState } = useData();
  const toast = useToast();
  const [types, setTypes] = useState([]);
  const [type, setType] = useState('walking');
  const [duration, setDuration] = useState(30);
  const [time, setTime] = useState(nowHHMM());
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get('/api/activity/types').then((d) => {
      setTypes(d.types); if (d.types?.length) setType(d.types[0]);
    }).catch(() => {});
  }, []);

  const log = async () => {
    const dur = Number(duration);
    if (!dur || dur <= 0) { toast('Enter a duration in minutes', 'error'); return; }
    setBusy(true);
    try {
      const data = await api.post('/api/activity', {
        activity_type: type, duration_min: dur, day: localDay(),
        performed_at: combineDayTime(localDay(), time), note,
      });
      setState(data.state);
      toast(`Logged ${type} · +${fmt(data.calories_burned)} kcal budget`);
      setNote('');
    } catch (e) { toast(e.message, 'error'); }
    finally { setBusy(false); }
  };

  const remove = async (id) => {
    try { setState(await api.del(`/api/activity/${id}?day=${localDay()}`)); }
    catch (e) { toast(e.message, 'error'); }
  };

  const acts = state?.activities || [];
  const bonus = state?.goals?.activity_bonus_kcal || 0;
  const inputCls = 'w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500';

  return (
    <div className="grid gap-5 fade-in lg:grid-cols-2">
      <Card title="Log activity">
        <p className="mb-4 text-sm text-slate-500">Exercise raises today's calorie &amp; carb budget. Values are estimates (MET-based).</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Activity</label>
            <select value={type} onChange={(e) => setType(e.target.value)} className={inputCls}>
              {types.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Duration (min)</label>
            <input type="number" min="1" value={duration} onChange={(e) => setDuration(e.target.value)} className={inputCls} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Time</label>
            <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className={inputCls} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Note (optional)</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} className={inputCls} placeholder="e.g. evening walk" />
          </div>
        </div>
        <Button onClick={log} disabled={busy} className="mt-4 w-full">Log activity</Button>
      </Card>

      <Card title="Today's activity" right={bonus > 0 ? <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">+{fmt(bonus)} kcal</span> : null}>
        {acts.length === 0 ? (
          <p className="text-sm text-slate-400">Nothing logged yet today.</p>
        ) : (
          <ul className="space-y-2">
            {acts.map((a) => (
              <li key={a.id} className="flex items-center justify-between rounded-xl bg-slate-50 p-3">
                <div>
                  <div className="text-sm font-medium capitalize text-slate-700">
                    {a.activity_type} · {fmt(a.duration_min)} min
                    {a.performed_at && <span className="ml-2 text-xs font-normal text-slate-400">{fmtTime(a.performed_at)}</span>}
                  </div>
                  {a.note && <div className="text-xs text-slate-400">{a.note}</div>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-emerald-600">+{fmt(a.calories_burned)} kcal</span>
                  <button onClick={() => remove(a.id)} className="text-slate-300 hover:text-rose-500">✕</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
