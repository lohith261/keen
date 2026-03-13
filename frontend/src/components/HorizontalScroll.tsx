import { type ReactNode } from 'react';

interface HorizontalScrollProps {
  children: ReactNode;
  className?: string;
}

export default function HorizontalScroll({ children, className = '' }: HorizontalScrollProps) {
  return (
    <div className={`overflow-x-auto scrollbar-hide ${className}`}>
      <div className="flex gap-4 md:gap-6 px-4 md:px-6 pb-4 min-w-min">
        {children}
      </div>
    </div>
  );
}
