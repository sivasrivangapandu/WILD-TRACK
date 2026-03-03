import { useTheme } from '../context/ThemeContext';

/**
 * Glass-morphism card with optional animated gradient border.
 * Usage: <GlassCard glow> ... </GlassCard>
 */
export default function GlassCard({ children, className = '', glow = false, hover = true, ...props }) {
  return (
    <div
      className={`
        relative rounded-2xl border transition-all duration-300
        surface-card-lg
        ${hover ? 'surface-hover hover:shadow-lg' : ''}
        ${glow ? 'glass-glow' : ''}
        ${className}
      `}
      {...props}
    >
      {children}
    </div>
  );
}
