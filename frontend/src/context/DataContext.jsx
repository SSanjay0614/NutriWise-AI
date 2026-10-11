import React, { createContext, useContext, useCallback, useEffect, useState } from 'react';
import { api } from '../lib/supabase';
import { localDay } from '../lib/day';
import { useAuth } from './AuthContext';

const DataContext = createContext(null);
export const useData = () => useContext(DataContext);

export function DataProvider({ children }) {
  const { user } = useAuth();
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!user) return;
    try {
      const s = await api.get(`/api/state?day=${localDay()}`);
      setState(s);
    } catch (e) {
      // keep previous state; pages surface errors via toast
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { setLoading(true); refresh(); }, [refresh]);

  return (
    <DataContext.Provider value={{ state, setState, refresh, loading }}>
      {children}
    </DataContext.Provider>
  );
}
