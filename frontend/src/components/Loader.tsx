import { useState, useEffect, useRef, useCallback } from 'react';

interface LoaderProps {
  onComplete: () => void;
}

export default function Loader({ onComplete }: LoaderProps) {
  const [phase, setPhase] = useState(0);
  const [progress, setProgress] = useState(0);
  const [exitPhase, setExitPhase] = useState(0);
  const progressRef = useRef(0);
  const rafRef = useRef<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 200);
    const t2 = setTimeout(() => setPhase(2), 900);
    const t3 = setTimeout(() => setPhase(3), 1400);

    return () => {
      [t1, t2, t3].forEach(clearTimeout);
    };
  }, []);

  useEffect(() => {
    if (phase < 3) return;

    const start = performance.now();
    const duration = 800;

    const tick = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      progressRef.current = eased * 100;
      setProgress(progressRef.current);

      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [phase]);

  const startExit = useCallback(() => {
    setExitPhase(1);

    setTimeout(() => {
      setExitPhase(2);
    }, 600);

    setTimeout(() => {
      setExitPhase(3);
    }, 1200);

    setTimeout(() => {
      onComplete();
    }, 1600);
  }, [onComplete]);

  useEffect(() => {
    if (phase < 3 || progress < 100 || exitPhase > 0) return;

    const timer = setTimeout(startExit, 200);
    return () => clearTimeout(timer);
  }, [phase, progress, exitPhase, startExit]);

  const letters = 'KEEN'.split('');

  const getLetterEntrance = (index: number) => {
    if (phase < 1) {
      return {
        opacity: 0,
        transform: 'perspective(800px) rotateX(90deg) translateY(60px) translateZ(-80px)',
      };
    }
    return {
      opacity: 1,
      transform: 'perspective(800px) rotateX(0deg) translateY(0px) translateZ(0px)',
    };
  };

  const getLetterExit = (index: number) => {
    if (exitPhase === 0) return {};

    if (exitPhase >= 2) {
      const offsets = [-120, -40, 40, 120];
      return {
        opacity: 0,
        transform: `perspective(800px) rotateX(-15deg) translateX(${offsets[index]}px) translateY(-30px) scale(1.1)`,
      };
    }

    if (exitPhase >= 1) {
      return {
        transform: 'perspective(800px) rotateX(0deg) translateY(0px) scale(1.05)',
        letterSpacing: '0.15em',
      };
    }

    return {};
  };

  const getSubtextStyle = () => {
    if (exitPhase >= 1) {
      return {
        opacity: 0,
        transform: 'translateY(-10px)',
        transition: 'opacity 400ms ease-in, transform 400ms ease-in',
      };
    }
    if (phase >= 2) {
      return {
        opacity: 1,
        transform: 'translateY(0)',
        transition: 'opacity 600ms ease-out 300ms, transform 600ms ease-out 300ms',
      };
    }
    return {
      opacity: 0,
      transform: 'translateY(8px)',
      transition: 'opacity 600ms ease-out, transform 600ms ease-out',
    };
  };

  const getProgressStyle = () => {
    if (exitPhase >= 1) {
      return {
        opacity: 0,
        transform: 'translateY(-8px)',
        transition: 'opacity 300ms ease-in, transform 300ms ease-in',
      };
    }
    if (phase >= 3) {
      return {
        opacity: 1,
        transform: 'translateY(0)',
        transition: 'opacity 500ms ease-out, transform 500ms ease-out',
      };
    }
    return {
      opacity: 0,
      transform: 'translateY(8px)',
    };
  };

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-[100] flex items-center justify-center"
      style={{
        pointerEvents: exitPhase >= 3 ? 'none' : 'auto',
      }}
    >
      <div
        className="absolute inset-0 bg-theme-bg"
        style={{
          opacity: exitPhase >= 2 ? 0 : 1,
          transition: exitPhase >= 2
            ? 'opacity 800ms cubic-bezier(0.25, 0.1, 0.25, 1)'
            : 'none',
        }}
      />

      <div className="relative z-10 flex flex-col items-center">
        <div
          className="flex items-center overflow-visible mb-4"
          style={{
            perspective: '800px',
          }}
        >
          {letters.map((letter, i) => {
            const entrance = getLetterEntrance(i);
            const exit = getLetterExit(i);
            const isExiting = exitPhase >= 1;

            const baseDelay = i * 100 + 50;
            const exitDelay = exitPhase >= 2 ? i * 60 : 0;

            return (
              <span
                key={i}
                className="inline-block text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight text-theme-text"
                style={{
                  ...entrance,
                  ...(isExiting ? exit : {}),
                  transformOrigin: 'center bottom',
                  transition: isExiting
                    ? `opacity 500ms cubic-bezier(0.4, 0, 0.2, 1) ${exitDelay}ms, transform 600ms cubic-bezier(0.4, 0, 0.2, 1) ${exitDelay}ms, letter-spacing 500ms cubic-bezier(0.4, 0, 0.2, 1)`
                    : `opacity 700ms cubic-bezier(0.16, 1, 0.3, 1) ${baseDelay}ms, transform 900ms cubic-bezier(0.16, 1, 0.3, 1) ${baseDelay}ms`,
                  willChange: 'transform, opacity',
                }}
              >
                {letter}
              </span>
            );
          })}
        </div>

        <div style={getSubtextStyle()}>
          <p className="text-[10px] md:text-xs font-mono text-theme-text-muted tracking-[0.3em] text-center">
            SHARPER JUDGMENT. FASTER EXECUTION.
          </p>
        </div>

        <div className="w-48 md:w-56 mt-8" style={getProgressStyle()}>
          <div className="w-full h-[1px] bg-theme-border overflow-hidden">
            <div
              className="h-full bg-orange-600"
              style={{
                width: `${progress}%`,
                transition: 'none',
              }}
            />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className="text-[9px] font-mono text-theme-text-faint">
              INITIALIZING
            </span>
            <span className="text-[9px] font-mono text-theme-text-muted tabular-nums">
              {Math.round(progress)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
