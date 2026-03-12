interface ScrollProgressBarProps {
  progress: number;
}

export default function ScrollProgressBar({ progress }: ScrollProgressBarProps) {
  return (
    <div className="fixed top-0 left-0 w-full h-[2px] z-[60]">
      <div
        className="h-full bg-gradient-to-r from-orange-600 via-orange-500 to-amber-400 transition-none"
        style={{
          width: `${progress * 100}%`,
          boxShadow: '0 0 10px rgba(234, 88, 12, 0.5), 0 0 20px rgba(234, 88, 12, 0.2)',
        }}
      />
    </div>
  );
}
