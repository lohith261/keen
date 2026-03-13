import { createContext, useContext, useState, type ReactNode } from 'react';

export type AppView = 'landing' | 'dashboard';

interface ViewContextValue {
  view: AppView;
  setView: (v: AppView) => void;
  openEngagement: (id: string) => void;
  activeEngagementId: string | null;
}

const ViewContext = createContext<ViewContextValue | null>(null);

export function ViewProvider({ children }: { children: ReactNode }) {
  const [view, setView] = useState<AppView>('landing');
  const [activeEngagementId, setActiveEngagementId] = useState<string | null>(null);

  const openEngagement = (id: string) => {
    setActiveEngagementId(id);
    setView('dashboard');
  };

  return (
    <ViewContext.Provider value={{ view, setView, openEngagement, activeEngagementId }}>
      {children}
    </ViewContext.Provider>
  );
}

export function useView() {
  const ctx = useContext(ViewContext);
  if (!ctx) throw new Error('useView must be used within ViewProvider');
  return ctx;
}
