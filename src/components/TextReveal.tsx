import { useRef, useEffect, type CSSProperties } from 'react';
import gsap from 'gsap';

interface TextRevealProps {
  text: string;
  tag?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span';
  className?: string;
  style?: CSSProperties;
  delay?: number;
  stagger?: number;
  type?: 'chars' | 'words' | 'lines';
}

export default function TextReveal({
  text,
  tag: Tag = 'h2',
  className = '',
  style,
  delay = 0,
  stagger = 0.03,
  type = 'words',
}: TextRevealProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = ref.current;
    if (!container) return;

    const el = container.querySelector('[data-text]');
    if (!el) return;

    let items: string[];
    if (type === 'chars') {
      items = text.split('');
    } else if (type === 'words') {
      items = text.split(' ');
    } else {
      items = [text];
    }

    el.innerHTML = items
      .map(
        (item) =>
          `<span style="display:inline-block;overflow:hidden;vertical-align:top;"><span class="text-item" style="display:inline-block;transform:translateY(110%)">${item}</span></span>`
      )
      .join(type === 'chars' ? '' : '&nbsp;');

    const spans = el.querySelectorAll('.text-item');

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          gsap.to(spans, {
            y: '0%',
            duration: 0.9,
            stagger,
            delay,
            ease: 'power3.out',
          });
          observer.unobserve(container);
        }
      },
      { threshold: 0.2 }
    );

    observer.observe(container);
    return () => observer.disconnect();
  }, [text, delay, stagger, type]);

  return (
    <div ref={ref}>
      <Tag className={className} style={style} data-text>
        {text}
      </Tag>
    </div>
  );
}
