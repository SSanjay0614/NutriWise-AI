import React, { createContext, useContext, useEffect, useState } from 'react';
import { getSupabase, getConfig } from '../lib/supabase';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);
  const [session, setSession] = useState(null);
  const [config, setConfig] = useState(null);

  useEffect(() => {
    let sub;
    (async () => {
      try {
        const cfg = await getConfig();
        setConfig(cfg);
        if (!cfg.configured) { setReady(true); return; }
        const sb = await getSupabase();
        const { data } = await sb.auth.getSession();
        setSession(data.session);
        sub = sb.auth.onAuthStateChange((_e, s) => setSession(s)).data.subscription;
      } catch (e) {
        setError(e.message);
      } finally {
        setReady(true);
      }
    })();
    return () => sub && sub.unsubscribe();
  }, []);

  const signIn = async (email, password) => {
    const sb = await getSupabase();
    const { error } = await sb.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };
  const signUp = async (email, password) => {
    const sb = await getSupabase();
    const { data, error } = await sb.auth.signUp({ email, password });
    if (error) throw error;
    // If email confirmation is disabled, a session is returned immediately.
    return data.session != null;
  };
  const signOut = async () => {
    const sb = await getSupabase();
    await sb.auth.signOut();
  };

  const value = {
    ready, error, config,
    session, user: session?.user || null,
    signIn, signUp, signOut,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
