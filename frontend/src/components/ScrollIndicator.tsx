import { useEffect, useState } from 'react';

export default function ScrollIndicator() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const onScroll = () => {
      setVisible(window.scrollY < 100);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div
      className={`fixed bottom-8 left-1/2 -translate-x-1/2 z-40 flex flex-col items-center gap-3 transition-all duration-700 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
      }`}
    >
      <span className="text-[10px] font-mono tracking-[0.3em] text-theme-text-muted uppercase">
        Scroll to explore
      </span>
      <div className="w-[1px] h-12 relative overflow-hidden">
        <div className="absolute inset-0 w-full bg-gradient-to-b from-orange-500 to-transparent scroll-line" />
      </div>
    </div>
  );
}
