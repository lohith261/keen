import { useRef, useEffect, type ReactNode, type CSSProperties } from 'react';
import gsap from 'gsap';

interface ParallaxSectionProps {
  children: ReactNode;
  speed?: number;
  maxOffset?: number;
  className?: string;
  style?: CSSProperties;
}

export default function ParallaxSection({
  children,
  speed = 0.3,
  maxOffset = 40,
  className = '',
  style,
}: ParallaxSectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const yRef = useRef(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let raf: number;

    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const centerOffset = rect.top + rect.height / 2 - window.innerHeight / 2;
        const raw = centerOffset * speed * -1;
        const clamped = Math.max(-maxOffset, Math.min(maxOffset, raw));
        yRef.current += (clamped - yRef.current) * 0.1;
        gsap.set(el, { y: yRef.current });
      });
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    return () => {
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(raf);
    };
  }, [speed, maxOffset]);

  return (
    <div ref={ref} className={className} style={{ willChange: 'transform', ...style }}>
      {children}
    </div>
  );
}
