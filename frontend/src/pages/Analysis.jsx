import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/supabase';
import { localDay } from '../lib/day';
import { useToast } from '../components/Toast';
import { Card, Spinner, Button, fmt } from '../components/ui';

function Stat({ label, value, unit }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 text-center">
      <div className="text-2xl font-extrabold text-slate-800">{value ?? '—'}</div>
      <div className="text-[11px] text-slate-400">{label}{unit ? ` (${unit})` : ''}</div>
    </div>
  );
}

function AnalysisCard({ a, onDelete, onNarrate, generating }) {
  const s = a.stats || {};
  const when = (a.created_at || '').replace('T', ' ').slice(0, 16);
  return (
    <Card
      title={a.label || a.period}
      right={<div className="flex items-center gap-2">
        <span className="text-[11px] text-slate-400">{when}</span>
        {onDelete && <button onClick={() => onDelete(a.id)} className="text-slate-300 hover:text-rose-500">✕</button>}
      </div>}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Days tracked" value={s.days_tracked} />
        <Stat label="Avg fasting glucose" value={s.avg_fasting_glucose} unit="mg/dL" />
        <Stat label="Days in range" value={s.days_in_range} />
        <Stat label="Avg carbs" value={s.avg_carbs_g} unit="g" />
        <Stat label="Avg fiber" value={s.avg_fiber_g} unit="g" />
        <Stat label="Avg sugar" value={s.avg_sugar_g} unit="g" />
        <Stat label="Over carb budget" value={s.days_over_carb_budget} unit="days" />
        <Stat label="Activity" value={s.total_activity_min} unit="min" />
      </div>

      {(a.narrative || generating) && (
        <div className="mt-4 rounded-xl bg-brand-50 p-3">
          {generating ? (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
              Rewriting with AI…
            </div>
          ) : (
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">{a.narrative}</p>
          )}
          {onNarrate && !generating && (
            <button onClick={() => onNarrate(a.id)} className="mt-2 text-xs font-semibold text-brand-700 hover:underline">
              ✨ Rewrite with AI
            </button>
          )}
        </div>
      )}

      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-xs font-semibold uppercase text-slate-400">Insights</div>
          <ul className="space-y-1.5 text-sm text-slate-600">
            {(a.insights || []).map((o, i) => <li key={i} className="flex gap-2"><span className="text-slate-400">•</span>{o}</li>)}
          </ul>
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase text-slate-400">Plan for next week</div>
          <ul className="space-y-1.5 text-sm text-slate-600">
            {(a.next_week_plan || []).map((p, i) => <li key={i} className="flex gap-2"><span className="text-brand-500">✓</span>{p}</li>)}
          </ul>
        </div>
      </div>
    </Card>
  );
}

export default function Analysis() {
  const toast = useToast();
  const [list, setList] = useState(null);
  const [busy, setBusy] = useState(false);
  const [latest, setLatest] = useState(null);
  const [narrating, setNarrating] = useState(null); // id currently generating a summary
  const [showRange, setShowRange] = useState(false);
  const [from, setFrom] = useState('');
  const [to, setTo] = useState(localDay());

  const load = useCallback(async () => {
    try { setList((await api.get('/api/analyses')).analyses); }
    catch (e) { setList([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const genNarrative = async (id) => {
    setNarrating(id);
    try {
      const n = await api.post(`/api/analysis/${id}/narrative`, {});
      if (n.narrative) {
        setLatest((cur) => (cur && cur.id === id ? { ...cur, narrative: n.narrative } : cur));
        await load();
      }
      if (n.ai === false && n.reason) toast(n.reason);
    } catch (e) { toast(e.message, 'error'); }
    finally { setNarrating(null); }
  };

  const run = async (period, range_from, range_to) => {
    setBusy(true);
    try {
      const res = await api.post('/api/analysis/run', { period, range_from, range_to });
      setLatest(res.analysis || res.computed);
      await load();
    } catch (e) { toast(e.message, 'error'); }
    finally { setBusy(false); }
  };

  const del = async (id) => {
    try { setList((await api.del(`/api/analysis/${id}`)).analyses); }
    catch (e) { toast(e.message, 'error'); }
  };

  if (!list) return <Spinner label="Loading analyses…" />;

  return (
    <div className="space-y-5 fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-slate-700">Analysis</h2>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="soft" onClick={() => run('week')} disabled={busy}>New: this week</Button>
          <Button variant="soft" onClick={() => run('all')} disabled={busy}>New: all time</Button>
          <Button variant="ghost" onClick={() => setShowRange((v) => !v)}>Custom range</Button>
        </div>
      </div>

      {showRange && (
        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">From</label>
              <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">To</label>
              <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
            </div>
            <Button onClick={() => (from && to ? run('custom', from, to) : toast('Pick both dates', 'error'))} disabled={busy}>
              Run analysis
            </Button>
          </div>
        </Card>
      )}

      {busy && <Spinner label="Analyzing…" />}

      {latest && (
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand-600">Latest</div>
          <AnalysisCard a={latest} onNarrate={genNarrative} generating={narrating === latest.id} />
        </div>
      )}

      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Previous analyses</div>
        {list.length === 0 ? (
          <Card><p className="text-sm text-slate-400">No saved analyses yet. Run one with the buttons above.</p></Card>
        ) : (
          <div className="space-y-4">
            {list.filter((a) => !latest || a.id !== latest.id).map((a) => <AnalysisCard key={a.id} a={a} onDelete={del} onNarrate={genNarrative} generating={narrating === a.id} />)}
          </div>
        )}
      </div>

      <p className="text-center text-xs text-slate-400">Rules-based analysis with an optional AI summary. Educational only.</p>
    </div>
  );
}
