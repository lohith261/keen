import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { DemoModeProvider } from './context/DemoModeContext';
import { AuthProvider } from './context/AuthContext';
import App from './App.tsx';
import Dashboard from './components/dashboard/Dashboard.tsx';
import { ProtectedRoute } from './components/ProtectedRoute.tsx';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <DemoModeProvider>
          <AuthProvider>
            <Routes>
              {/* Public landing page */}
              <Route path="/" element={<App />} />

              {/* Protected dashboard — requires auth or demo mode */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />

              {/* Catch-all → landing */}
              <Route path="*" element={<App />} />
            </Routes>
          </AuthProvider>
        </DemoModeProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
);
