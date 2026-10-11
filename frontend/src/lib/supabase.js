import { createClient } from '@supabase/supabase-js';

let _client = null;
let _config = null;

// Fetch public bootstrap config (Supabase URL + anon key) from the backend,
// so the user only configures secrets in one place (the backend .env).
export async function getConfig() {
  if (_config) return _config;
  const r = await fetch('/api/config');
  if (!r.ok) throw new Error('Could not load /api/config');
  _config = await r.json();
  return _config;
}

export async function getSupabase() {
  if (_client) return _client;
  const cfg = await getConfig();
  if (!cfg.configured) {
    throw new Error('Backend not configured: ' + (cfg.missing || []).join(', '));
  }
  _client = createClient(cfg.supabase_url, cfg.supabase_anon_key, {
    auth: { persistSession: true, autoRefreshToken: true },
  });
  return _client;
}

// Authenticated fetch helpers — attach the current Supabase access token.
async function authHeader() {
  const sb = await getSupabase();
  const { data } = await sb.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const api = {
  async get(path) {
    const r = await fetch(path, { headers: { ...(await authHeader()) } });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeader()) },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    return r.json();
  },
  async del(path) {
    const r = await fetch(path, { method: 'DELETE', headers: { ...(await authHeader()) } });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    return r.json();
  },
};
