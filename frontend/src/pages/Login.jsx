import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import { Button } from '../components/ui';

export default function Login() {
  const { signIn, signUp, config } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === 'login') {
        await signIn(email, password);
        navigate('/dashboard');
      } else {
        const hasSession = await signUp(email, password);
        if (hasSession) { navigate('/dashboard'); }
        else { toast('Account created. Check your email to confirm, then log in.'); setMode('login'); }
      }
    } catch (err) {
      toast(err.message || 'Authentication failed', 'error');
    } finally { setBusy(false); }
  };

  const tryDemo = async () => {
    if (!config?.demo_email) return;
    setBusy(true);
    try {
      await signIn(config.demo_email, config.demo_password);
      navigate('/dashboard');
    } catch (err) {
      toast('Demo account not ready. Run: python -m backend.seed_demo', 'error');
    } finally { setBusy(false); }
  };

  const input = 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100';

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 via-slate-50 to-slate-100 p-4">
      <div className="w-full max-w-md fade-in">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-xl font-black text-white">N</div>
          <div>
            <h1 className="text-2xl font-extrabold text-slate-800">NutriWise</h1>
            <p className="text-xs text-slate-400">Diabetes Diet Assistant</p>
          </div>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <div className="mb-5 flex rounded-xl bg-slate-100 p-1">
            {['login', 'register'].map((m) => (
              <button key={m} onClick={() => setMode(m)}
                className={`flex-1 rounded-lg py-2 text-sm font-semibold capitalize transition ${mode === m ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-500'}`}>
                {m === 'login' ? 'Sign in' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Email</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={input} placeholder="you@example.com" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Password</label>
              <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} className={input} placeholder="••••••••" />
            </div>
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
            </Button>
          </form>

          {config?.demo_email && (
            <>
              <div className="my-4 flex items-center gap-3 text-xs text-slate-400">
                <div className="h-px flex-1 bg-slate-200" /> or <div className="h-px flex-1 bg-slate-200" />
              </div>
              <Button variant="soft" onClick={tryDemo} disabled={busy} className="w-full">
                Try the demo account
              </Button>
            </>
          )}
        </div>
        <p className="mt-4 text-center text-xs text-slate-400">
          Educational prototype — diet information only, not medical advice.
        </p>
      </div>
    </div>
  );
}
