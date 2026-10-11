import React, { createContext, useContext, useCallback, useState } from 'react';

const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const show = useCallback((msg, kind = 'info') => {
    setToast({ msg, kind, id: Date.now() });
    setTimeout(() => setToast((t) => (t && t.msg === msg ? null : t)), 3400);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast && (
        <div className={`fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl px-4 py-2 text-sm text-white shadow-lg fade-in ${toast.kind === 'error' ? 'bg-rose-600' : 'bg-slate-800'}`}>
          {toast.msg}
        </div>
      )}
    </ToastContext.Provider>
  );
}
