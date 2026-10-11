import React, { useState } from 'react';
import { api } from '../lib/supabase';
import { useData } from '../context/DataContext';
import { useToast } from '../components/Toast';
import { Card, Button, fmt } from '../components/ui';

const DEFAULTS = {
  name: 'User', age: 45, gender: 'male', weight_kg: 70, height_cm: 170,
  activity_level: 'sedentary', diabetes_type: 'type2', on_insulin: false,
  hba1c: '', conditions: [],
};

const PRESET_CONDITIONS = [
  'hypertension', 'kidney', 'high cholesterol', 'heart disease', 'obesity',
  'thyroid', 'PCOS', 'neuropathy', 'retinopathy', 'fatty liver', 'anemia', 'celiac',
];

export default function Profile() {
  const { state, setState } = useData();
  const toast = useToast();
  const [p, setP] = useState(() => ({ ...DEFAULTS, ...(state?.profile || {}) }));
  const [condInput, setCondInput] = useState('');
  const [busy, setBusy] = useState(false);
  const goals = state?.goals;
  const set = (k, v) => setP((prev) => ({ ...prev, [k]: v }));

  const toggleCond = (c) => setP((prev) => ({
    ...prev,
    conditions: prev.conditions.includes(c) ? prev.conditions.filter((x) => x !== c) : [...prev.conditions, c],
  }));
  const addCustomCond = () => {
    const c = condInput.trim();
    if (!c) return;
    if (!p.conditions.map((x) => x.toLowerCase()).includes(c.toLowerCase())) toggleCond(c);
    setCondInput('');
  };

  const submit = async () => {
    setBusy(true);
    try {
      const body = {
        ...p, age: Number(p.age), weight_kg: Number(p.weight_kg), height_cm: Number(p.height_cm),
        hba1c: p.hba1c === '' || p.hba1c == null ? null : Number(p.hba1c),
      };
      const data = await api.post('/api/profile', body);
      setState(data);
      toast('Profile saved — goals updated.');
    } catch (e) { toast(e.message, 'error'); }
    finally { setBusy(false); }
  };

  const inputCls = 'w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500';
  const field = (label, el) => (<div><label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>{el}</div>);

  return (
    <div className="grid gap-5 fade-in lg:grid-cols-3">
      <Card title="Your profile" className="lg:col-span-2">
        <div className="grid gap-4 sm:grid-cols-2">
          {field('Name', <input className={inputCls} value={p.name} onChange={(e) => set('name', e.target.value)} />)}
          {field('Age', <input type="number" className={inputCls} value={p.age} onChange={(e) => set('age', e.target.value)} />)}
          {field('Gender', (
            <select className={inputCls} value={p.gender} onChange={(e) => set('gender', e.target.value)}>
              <option value="male">male</option><option value="female">female</option>
            </select>
          ))}
          {field('Weight (kg)', <input type="number" className={inputCls} value={p.weight_kg} onChange={(e) => set('weight_kg', e.target.value)} />)}
          {field('Height (cm)', <input type="number" className={inputCls} value={p.height_cm} onChange={(e) => set('height_cm', e.target.value)} />)}
          {field('Activity', (
            <select className={inputCls} value={p.activity_level} onChange={(e) => set('activity_level', e.target.value)}>
              {['sedentary', 'light', 'moderate', 'active', 'very_active'].map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          ))}
          {field('Diabetes type', (
            <select className={inputCls} value={p.diabetes_type} onChange={(e) => set('diabetes_type', e.target.value)}>
              {['type1', 'type2', 'prediabetes', 'gestational'].map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          ))}
          {field('Last HbA1c % (optional)', <input type="number" step="0.1" className={inputCls} value={p.hba1c ?? ''} onChange={(e) => set('hba1c', e.target.value)} />)}
        </div>

        <div className="mt-4">
          <label className="mb-2 flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={!!p.on_insulin} onChange={(e) => set('on_insulin', e.target.checked)} /> On insulin
          </label>
          <span className="mb-1 block text-xs font-medium text-slate-500">Conditions</span>
          <div className="flex flex-wrap gap-2">
            {PRESET_CONDITIONS.map((c) => (
              <button key={c} onClick={() => toggleCond(c)}
                className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ${p.conditions.includes(c) ? 'bg-brand-50 text-brand-700 ring-brand-200' : 'bg-slate-50 text-slate-500 ring-slate-200'}`}>
                {c}
              </button>
            ))}
            {/* custom conditions the user typed that aren't presets */}
            {p.conditions.filter((c) => !PRESET_CONDITIONS.includes(c)).map((c) => (
              <button key={c} onClick={() => toggleCond(c)}
                className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 ring-1 ring-indigo-200">
                {c} ✕
              </button>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            <input value={condInput} onChange={(e) => setCondInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomCond())}
              placeholder="Add another condition (e.g. thyroid, PCOS, neuropathy)…"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500" />
            <Button variant="soft" onClick={addCustomCond} className="shrink-0">Add</Button>
          </div>
        </div>

        <Button onClick={submit} disabled={busy} className="mt-5">Save profile & recompute goals</Button>
      </Card>

      <Card title="Your daily goals">
        {goals ? (
          <ul className="space-y-2 text-sm">
            {[
              ['Calories', `${fmt(goals.calories_kcal)} kcal`],
              ['Carb budget', `${fmt(goals.carbohydrate_g)} g`],
              ['Sugar ceiling', `${fmt(goals.sugar_max_g)} g`],
              ['Fiber minimum', `${fmt(goals.fiber_min_g)} g`],
              ['Protein', `${fmt(goals.protein_g)} g`],
              ['Fat', `${fmt(goals.fat_g)} g`],
              ['Sodium ceiling', `${fmt(goals.sodium_max_mg)} mg`],
            ].map(([k, v]) => (
              <li key={k} className="flex justify-between border-b border-slate-100 pb-1">
                <span className="text-slate-500">{k}</span><span className="font-semibold text-slate-700">{v}</span>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-slate-400">Save your profile to see goals.</p>}
        {state?.profile && <p className="mt-3 text-xs text-slate-400">BMI {fmt(state.profile.bmi, 1)}</p>}
        {goals && goals.notes.length > 0 && (
          <ul className="mt-3 space-y-1 text-xs text-slate-500">
            {goals.notes.map((n, i) => <li key={i}>• {n}</li>)}
          </ul>
        )}
      </Card>
    </div>
  );
}
