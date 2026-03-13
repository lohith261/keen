import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isLight = theme === 'light';

  return (
    <button
      onClick={toggleTheme}
      aria-label={`Switch to ${isLight ? 'dark' : 'light'} mode`}
      className="relative w-9 h-9 flex items-center justify-center rounded-full border border-theme-border bg-theme-surface/60 backdrop-blur-sm hover:border-orange-600/50 transition-all duration-300 group"
    >
      <Sun
        className={`w-4 h-4 absolute transition-all duration-300 text-amber-500 ${
          isLight ? 'opacity-100 rotate-0 scale-100' : 'opacity-0 -rotate-90 scale-0'
        }`}
      />
      <Moon
        className={`w-4 h-4 absolute transition-all duration-300 text-neutral-400 ${
          isLight ? 'opacity-0 rotate-90 scale-0' : 'opacity-100 rotate-0 scale-100'
        }`}
      />
    </button>
  );
}
