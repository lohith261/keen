import { useRef, useEffect, type ReactNode } from 'react';
import gsap from 'gsap';

interface SmoothScrollProps {
  children: ReactNode;
}

export default function SmoothScroll({ children }: SmoothScrollProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef({ current: 0, target: 0 });

  useEffect(() => {
    const content = contentRef.current;
    if (!content) return;

    const isMobile = window.innerWidth < 768;
    if (isMobile) return;

    let raf: number;
    const lerp = (start: number, end: number, factor: number) =>
      start + (end - start) * factor;

    const update = () => {
      scrollRef.current.target = window.scrollY;
      scrollRef.current.current = lerp(
        scrollRef.current.current,
        scrollRef.current.target,
        0.08
      );

      const diff = Math.abs(scrollRef.current.current - scrollRef.current.target);
      if (diff > 0.5) {
        gsap.set(content, { y: -scrollRef.current.current });
      }

      raf = requestAnimationFrame(update);
    };

    const setBodyHeight = () => {
      document.body.style.height = `${content.scrollHeight}px`;
    };

    const onResize = () => {
      setBodyHeight();
    };

    gsap.set(content, { position: 'fixed', top: 0, left: 0, width: '100%' });
    setBodyHeight();

    window.addEventListener('resize', onResize);
    raf = requestAnimationFrame(update);

    return () => {
      window.removeEventListener('resize', onResize);
      cancelAnimationFrame(raf);
      document.body.style.height = '';
      gsap.set(content, { clearProps: 'all' });
    };
  }, []);

  return <div ref={contentRef}>{children}</div>;
}
