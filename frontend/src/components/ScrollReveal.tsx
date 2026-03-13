import { useRef, useEffect, type ReactNode, type CSSProperties } from 'react';
import gsap from 'gsap';

type AnimationType = 'fadeUp' | 'fadeDown' | 'fadeLeft' | 'fadeRight' | 'scale' | 'fade' | 'clipReveal';

interface ScrollRevealProps {
  children: ReactNode;
  animation?: AnimationType;
  delay?: number;
  duration?: number;
  distance?: number;
  className?: string;
  style?: CSSProperties;
  stagger?: number;
  threshold?: number;
}

const initialStates: Record<AnimationType, gsap.TweenVars> = {
  fadeUp: { opacity: 0, y: 30 },
  fadeDown: { opacity: 0, y: -30 },
  fadeLeft: { opacity: 0, x: -40 },
  fadeRight: { opacity: 0, x: 40 },
  scale: { opacity: 0, scale: 0.92 },
  fade: { opacity: 0 },
  clipReveal: { opacity: 0, clipPath: 'inset(100% 0% 0% 0%)' },
};

const animatedStates: Record<AnimationType, gsap.TweenVars> = {
  fadeUp: { opacity: 1, y: 0 },
  fadeDown: { opacity: 1, y: 0 },
  fadeLeft: { opacity: 1, x: 0 },
  fadeRight: { opacity: 1, x: 0 },
  scale: { opacity: 1, scale: 1 },
  fade: { opacity: 1 },
  clipReveal: { opacity: 1, clipPath: 'inset(0% 0% 0% 0%)' },
};

export default function ScrollReveal({
  children,
  animation = 'fadeUp',
  delay = 0,
  duration = 1,
  className = '',
  style,
  stagger = 0,
  threshold = 0.15,
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    gsap.set(el, initialStates[animation]);

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          const targets = stagger > 0 ? el.children : el;
          gsap.to(targets, {
            ...animatedStates[animation],
            duration,
            delay,
            stagger: stagger > 0 ? stagger : undefined,
            ease: 'power3.out',
          });
          observer.unobserve(el);
        }
      },
      { threshold }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [animation, delay, duration, stagger, threshold]);

  return (
    <div ref={ref} className={className} style={style}>
      {children}
    </div>
  );
}
