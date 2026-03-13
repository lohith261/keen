import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider } from './context/ThemeContext';
import { DemoModeProvider } from './context/DemoModeContext';
import { ViewProvider } from './context/ViewContext';
import App from './App.tsx';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <DemoModeProvider>
        <ViewProvider>
          <App />
        </ViewProvider>
      </DemoModeProvider>
    </ThemeProvider>
  </StrictMode>
);
