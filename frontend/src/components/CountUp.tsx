import { useRef, useEffect, useState } from 'react';
import gsap from 'gsap';

interface CountUpProps {
  end: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  duration?: number;
  className?: string;
}

export default function CountUp({
  end,
  suffix = '',
  prefix = '',
  decimals = 0,
  duration = 2,
  className = '',
}: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const valueRef = useRef({ val: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasStarted) {
          setHasStarted(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.5 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [hasStarted]);

  useEffect(() => {
    if (!hasStarted || !ref.current) return;

    valueRef.current.val = 0;
    gsap.to(valueRef.current, {
      val: end,
      duration,
      ease: 'power2.out',
      onUpdate: () => {
        if (ref.current) {
          ref.current.textContent = `${prefix}${valueRef.current.val.toFixed(decimals)}${suffix}`;
        }
      },
    });
  }, [hasStarted, end, suffix, prefix, decimals, duration]);

  return (
    <span ref={ref} className={className}>
      {prefix}0{suffix}
    </span>
  );
}
