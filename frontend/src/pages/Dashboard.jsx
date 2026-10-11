import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useData } from '../context/DataContext';
import { api } from '../lib/supabase';
import { localDay, fmtTime } from '../lib/day';
import { useToast } from '../components/Toast';
import { Card, Progress, PriorityTag, fmt, GLUCOSE_BG, Button, MicroGrid } from '../components/ui';

const MAIN_MEALS = ['breakfast', 'lunch', 'dinner'];
const WINDOW_END = { breakfast: 10.5, lunch: 15, dinner: 21.5 }; // local hour the meal is "due" by

function dayOffset(n) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return localDay(d);
}

function MealReminders() {
  const navigate = useNavigate();
  const [missed, setMissed] = useState([]);

  useEffect(() => {
    api.get('/api/history').then((d) => {
      const byDate = {};
      (d.days || []).forEach((x) => { byDate[x.date] = new Set(x.meal_types || []); });
      const today = localDay(), yest = dayOffset(-1);
      const nowH = new Date().getHours() + new Date().getMinutes() / 60;
      const list = [];
      MAIN_MEALS.forEach((m) => {
        if (!(byDate[yest]?.has(m))) list.push({ date: yest, meal: m, label: 'yesterday' });
        if (nowH > WINDOW_END[m] && !(byDate[today]?.has(m))) list.push({ date: today, meal: m, label: 'today' });
      });
      setMissed(list.filter((x) => {
        try { return localStorage.getItem(`rem:${x.date}:${x.meal}`) !== '1'; } catch { return true; }
      }));
    }).catch(() => {});
  }, []);

  const dismiss = (x) => {
    try { localStorage.setItem(`rem:${x.date}:${x.meal}`, '1'); } catch {}
    setMissed((m) => m.filter((y) => !(y.date === x.date && y.meal === x.meal)));
  };

  if (missed.length === 0) return null;
  return (
    <div className="rounded-2xl bg-amber-50 p-4 ring-1 ring-amber-200">
      <div className="mb-2 text-sm font-semibold text-amber-800">🔔 You have meals you didn't log</div>
      <div className="flex flex-wrap gap-2">
        {missed.map((x, i) => (
          <div key={i} className="flex items-center gap-2 rounded-xl bg-white px-3 py-1.5 text-sm shadow-sm ring-1 ring-amber-100">
            <span className="capitalize text-slate-600">{x.meal} · {x.label}</span>
            <button onClick={() => navigate(`/log?day=${x.date}&meal=${x.meal}`)} className="font-semibold text-brand-700 hover:underline">Log it</button>
            <button onClick={() => dismiss(x)} className="text-slate-300 hover:text-rose-500">✕</button>
          </div>
        ))}
      </div>
    </div>
  );
}


function GlucoseBanner({ state, navigate }) {
  const g = state.glucose;
  const cat = g ? g.category : 'unknown';
  return (
    <div className={`flex flex-col gap-3 rounded-2xl p-5 text-white shadow-sm sm:flex-row sm:items-center sm:justify-between ${GLUCOSE_BG[cat]}`}>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider opacity-80">Today's blood sugar</div>
        <div className="mt-1 text-2xl font-extrabold">
          {g ? `${fmt(g.value_mg_dl)} mg/dL` : 'Not logged yet'}
          {g && <span className="ml-2 text-base font-semibold uppercase opacity-90">· {cat}</span>}
        </div>
        <p className="mt-1 max-w-xl text-sm opacity-90">{state.glucose_message}</p>
      </div>
      <button onClick={() => navigate('/glucose')} className="shrink-0 rounded-xl bg-white/20 px-4 py-2 text-sm font-semibold backdrop-blur hover:bg-white/30">
        {g ? 'Update reading' : 'Log reading'}
      </button>
    </div>
  );
}

export default function Dashboard() {
  const { state, setState } = useData();
  const navigate = useNavigate();
  const toast = useToast();
  if (!state || !state.goals) return null;
  const { goals, totals: t, assessment: a } = state;
  const carbBudget = state.carb_budget_today ?? goals.carbohydrate_g;

  const deleteMeal = async (meal_type) => {
    try {
      const s = await api.del(`/api/meal?meal_type=${encodeURIComponent(meal_type)}&day=${localDay()}`);
      setState(s);
      toast(`Removed ${meal_type}`);
    } catch (e) { toast(e.message, 'error'); }
  };

  return (
    <div className="space-y-5 fade-in">
      <MealReminders />
      <GlucoseBanner state={state} navigate={navigate} />

      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Intake vs goals" className="lg:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            <Progress label="Calories" value={t.calories_kcal} target={goals.calories_kcal} unit="kcal" mode="budget" />
            <Progress label="Carbs (budget)" value={t.carbohydrate_g} target={carbBudget} unit="g" mode="budget" />
            <Progress label="Sugar (max)" value={t.sugar_g} target={goals.sugar_max_g} unit="g" mode="budget" />
            <Progress label="Fiber (min)" value={t.fiber_g} target={goals.fiber_min_g} unit="g" mode="min" />
            <Progress label="Protein" value={t.protein_g} target={goals.protein_g} unit="g" mode="min" />
            <Progress label="Sodium (max)" value={t.sodium_mg} target={goals.sodium_max_mg} unit="mg" mode="budget" />
          </div>
          {state.carb_budget_today != null && state.carb_budget_today < goals.carbohydrate_g && (
            <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
              Carb budget reduced from {fmt(goals.carbohydrate_g)}g to {fmt(carbBudget)}g today based on your glucose reading.
            </p>
          )}
        </Card>

        <Card title="Today's meals" right={<Button variant="soft" onClick={() => navigate('/log')} className="px-3 py-1 text-xs">+ Log</Button>}>
          {state.meals.length === 0 ? (
            <p className="text-sm text-slate-400">No meals logged yet today.</p>
          ) : (
            <ul className="space-y-3">
              {state.meals.map((m, i) => (
                <li key={i} className="rounded-xl bg-slate-50 p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold capitalize text-slate-700">
                      {m.meal_type}
                      {m.eaten_at && <span className="ml-2 text-xs font-normal text-slate-400">{fmtTime(m.eaten_at)}</span>}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">{fmt(m.nutrition.calories_kcal)} kcal</span>
                      <button onClick={() => deleteMeal(m.meal_type)} title="Remove"
                        className="text-slate-300 hover:text-rose-500">✕</button>
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{(m.foods || []).map((f) => f.food_name).join(', ') || '—'}</div>
                  <div className="mt-1 text-xs text-slate-400">
                    carbs {fmt(m.nutrition.carbohydrate_g)}g · sugar {fmt(m.nutrition.sugar_g)}g · fiber {fmt(m.nutrition.fiber_g)}g
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Assessment">
          {!a || a.observations.length === 0 ? (
            <p className="text-sm text-slate-400">Log a meal to see your assessment.</p>
          ) : (
            <>
              <ul className="space-y-2 text-sm text-slate-600">
                {a.observations.map((o, i) => <li key={i} className="flex gap-2"><span className="text-slate-400">•</span><span>{o}</span></li>)}
              </ul>
              {a.suggestions.length > 0 && (
                <div className="mt-4 border-t border-slate-100 pt-3">
                  <div className="mb-2 text-xs font-semibold uppercase text-slate-400">Suggestions</div>
                  <ul className="space-y-2 text-sm text-slate-600">
                    {a.suggestions.map((s, i) => <li key={i} className="flex gap-2"><span className="text-brand-500">→</span><span>{s}</span></li>)}
                  </ul>
                </div>
              )}
            </>
          )}
        </Card>

        <Card title="Next-meal recommendations">
          {state.recommendations.length === 0 ? (
            <p className="text-sm text-slate-400">Recommendations appear as you log meals.</p>
          ) : (
            <ul className="space-y-3">
              {state.recommendations.map((r, i) => (
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
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Micronutrients today" className="lg:col-span-2">
          <MicroGrid totals={t} targets={goals.micro_targets} />
          <p className="mt-3 text-[11px] text-slate-400">Micronutrient values are approximate dataset estimates.</p>
        </Card>
        <Card title="Activity today" right={<Button variant="soft" onClick={() => navigate('/activity')} className="px-3 py-1 text-xs">+ Log</Button>}>
          {(!state.activities || state.activities.length === 0) ? (
            <p className="text-sm text-slate-400">No activity logged. Logging exercise raises today's calorie &amp; carb budget.</p>
          ) : (
            <ul className="space-y-2">
              {state.activities.map((act, i) => (
                <li key={i} className="flex items-center justify-between rounded-xl bg-slate-50 p-2.5 text-sm">
                  <span className="capitalize text-slate-700">{act.activity_type} · {fmt(act.duration_min)}m</span>
                  <span className="text-xs text-slate-500">+{fmt(act.calories_burned)} kcal</span>
                </li>
              ))}
              {goals.activity_bonus_kcal > 0 && (
                <li className="pt-1 text-xs text-emerald-600">+{fmt(goals.activity_bonus_kcal)} kcal added to today's budget</li>
              )}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
