import React from 'react';
import { Routes, Route, Navigate, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { DataProvider, useData } from './context/DataContext';
import { Spinner } from './components/ui';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import LogMeal from './pages/LogMeal';
import Glucose from './pages/Glucose';
import Activity from './pages/Activity';
import Recommendations from './pages/Recommendations';
import Plan from './pages/Plan';
import History from './pages/History';
import Analysis from './pages/Analysis';
import Profile from './pages/Profile';

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/log', label: 'Log Meal', icon: '🍽️' },
  { to: '/glucose', label: 'Glucose', icon: '🩸' },
  { to: '/activity', label: 'Activity', icon: '🏃' },
  { to: '/recommendations', label: 'Recommendations', icon: '💡' },
  { to: '/plan', label: 'Meal Plan', icon: '🗓️' },
  { to: '/history', label: 'History', icon: '📒' },
  { to: '/analysis', label: 'Analysis', icon: '📈' },
  { to: '/profile', label: 'Profile', icon: '👤' },
];

function ConfigNeeded({ missing }) {
  return (
    <div className="mx-auto max-w-xl p-8 text-center">
      <h1 className="mb-2 text-2xl font-extrabold text-slate-800">Backend not configured</h1>
      <p className="text-slate-500">
        Add your Supabase keys to <code className="rounded bg-slate-200 px-1">.env</code> and restart the server.
      </p>
      {missing?.length > 0 && (
        <p className="mt-3 text-sm text-rose-600">Missing: {missing.join(', ')}</p>
      )}
    </div>
  );
}

function Sidebar() {
  const { user, signOut } = useAuth();
  const { state } = useData();
  return (
    <aside className="flex w-full shrink-0 flex-col gap-1 border-slate-200 bg-white p-3 sm:w-64 sm:border-r">
      <div className="mb-4 flex items-center gap-3 px-2 py-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-600 text-lg font-black text-white">N</div>
        <div>
          <div className="text-lg font-extrabold text-slate-800">NutriWise</div>
          <div className="text-[11px] text-slate-400">Diabetes Diet Assistant</div>
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto sm:flex-col sm:overflow-visible">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to}
            className={({ isActive }) =>
              `flex items-center gap-3 whitespace-nowrap rounded-xl px-3 py-2.5 text-sm font-semibold transition ${isActive ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
            <span>{n.icon}</span>{n.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto hidden border-t border-slate-100 pt-3 sm:block">
        <div className="truncate px-2 text-xs text-slate-400">{user?.email}</div>
        {state?.profile && (
          <div className="px-2 text-xs text-slate-400">{state.profile.diabetes_type} · BMI {Number(state.profile.bmi).toFixed(1)}</div>
        )}
        <button onClick={signOut} className="mt-2 w-full rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-500 hover:bg-slate-100">
          Sign out
        </button>
      </div>
    </aside>
  );
}

function Shell() {
  const { state, loading } = useData();
  const location = useLocation();
  const needsProfile = state && !state.has_profile;

  return (
    <div className="flex min-h-screen flex-col sm:flex-row">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-4 sm:p-8">
        <div className="mx-auto max-w-6xl">
          {needsProfile && location.pathname !== '/profile' && (
            <div className="mb-5 flex items-center justify-between rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
              <span>Finish setting up your profile to unlock your personalized goals.</span>
            </div>
          )}
          {loading && !state ? <Spinner /> : (
            <Routes>
              <Route path="/dashboard" element={needsProfile ? <Navigate to="/profile" /> : <Dashboard />} />
              <Route path="/log" element={needsProfile ? <Navigate to="/profile" /> : <LogMeal />} />
              <Route path="/glucose" element={<Glucose />} />
              <Route path="/activity" element={needsProfile ? <Navigate to="/profile" /> : <Activity />} />
              <Route path="/recommendations" element={needsProfile ? <Navigate to="/profile" /> : <Recommendations />} />
              <Route path="/plan" element={needsProfile ? <Navigate to="/profile" /> : <Plan />} />
              <Route path="/history" element={needsProfile ? <Navigate to="/profile" /> : <History />} />
              <Route path="/analysis" element={needsProfile ? <Navigate to="/profile" /> : <Analysis />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="*" element={<Navigate to="/dashboard" />} />
            </Routes>
          )}
          <footer className="mt-10 border-t border-slate-200 pt-4 text-center text-xs text-slate-400">
            Educational prototype — diet information only, not medical advice, and never insulin dosing.
          </footer>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const { ready, config, user, error } = useAuth();

  if (!ready) return <Spinner label="Starting NutriWise…" />;
  if (error) return <ConfigNeeded missing={[error]} />;
  if (config && !config.configured) return <ConfigNeeded missing={config.missing} />;

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    );
  }

  return (
    <DataProvider>
      <Shell />
    </DataProvider>
  );
}
