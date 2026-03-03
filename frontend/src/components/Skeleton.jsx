/**
 * Skeleton shimmer loading placeholder.
 * Props: count (repeat), variant (line|circle|card|bar), className
 */
export default function Skeleton({ count = 1, variant = 'line', className = '' }) {
  const base = `animate-shimmer rounded ${className}`;

  const items = Array.from({ length: count }, (_, i) => {
    switch (variant) {
      case 'circle':
        return <div key={i} className={`${base} w-12 h-12 rounded-full`} style={{ background: 'var(--bg-surface-2)' }} />;
      case 'card':
        return <div key={i} className={`${base} h-32 w-full rounded-2xl`} style={{ background: 'var(--bg-surface-2)' }} />;
      case 'bar':
        return <div key={i} className={`${base} h-4 rounded-full`} style={{ background: 'var(--bg-surface-2)', width: `${60 + Math.random() * 40}%` }} />;
      default:
        return <div key={i} className={`${base} h-4 rounded-full`} style={{ background: 'var(--bg-surface-2)', width: `${40 + Math.random() * 50}%` }} />;
    }
  });

  return <div className="space-y-3">{items}</div>;
}
