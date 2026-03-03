import { useTheme } from '../context/ThemeContext';

/**
 * Subtle animated background — soft gradient blobs and a gentle grid.
 * Lightweight: 2 blobs, 1 vignette, 1 grid. No film grain, no particles,
 * no aurora streaks. Respects prefers-reduced-motion.
 */
export default function AnimatedBackground() {
  const { dark, theme } = useTheme();

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none motion-reduce:hidden">
      {/* Subtle grid overlay */}
      <div
        className="absolute inset-0"
        style={{
          opacity: 0.03,
          backgroundImage: `linear-gradient(var(--text-primary) 1px, transparent 1px), linear-gradient(90deg, var(--text-primary) 1px, transparent 1px)`,
          backgroundSize: '60px 60px',
        }}
      />

      {/* Primary blob — themed colour, top-left */}
      <div
        className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full animate-blob blur-3xl"
        style={{
          background: `radial-gradient(circle, ${theme.primary}15 0%, transparent 70%)`,
        }}
      />

      {/* Secondary blob — accent colour, bottom-right */}
      <div
        className="absolute -bottom-40 -right-40 w-[550px] h-[550px] rounded-full animate-blob animation-delay-4000 blur-3xl"
        style={{
          background: `radial-gradient(circle, ${theme.accent}10 0%, transparent 70%)`,
        }}
      />

      {/* Vignette */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 60%, var(--bg-primary) 100%)',
        }}
      />
    </div>
  );
}
