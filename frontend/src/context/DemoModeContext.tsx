import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

export type DataMode = 'demo' | 'live';

const STORAGE_KEY = 'keen-data-mode';

interface DemoModeContextValue {
  mode: DataMode;
  isDemoMode: boolean;
  toggleMode: () => void;
  setMode: (mode: DataMode) => void;
}

const DemoModeContext = createContext<DemoModeContextValue | null>(null);

export function DemoModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<DataMode>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === 'demo' ? 'demo' : 'live'; // default: live
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const setMode = (next: DataMode) => setModeState(next);
  const toggleMode = () => setModeState((prev) => (prev === 'demo' ? 'live' : 'demo'));

  return (
    <DemoModeContext.Provider value={{ mode, isDemoMode: mode === 'demo', toggleMode, setMode }}>
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode() {
  const ctx = useContext(DemoModeContext);
  if (!ctx) throw new Error('useDemoMode must be used within DemoModeProvider');
  return ctx;
}

/** Read demo mode outside of React (e.g. in apiClient.ts). */
export function getDemoModeFromStorage(): boolean {
  return localStorage.getItem(STORAGE_KEY) !== 'live';
}
