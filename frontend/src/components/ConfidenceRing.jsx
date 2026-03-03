import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

/**
 * Animated circular confidence gauge with color-coded glow.
 * 
 * Props:
 *   confidence  – 0..1
 *   size        – px (default 120)
 *   strokeWidth – px (default 8)
 *   isUnknown   – bool
 *   label       – optional center label override
 */
export default function ConfidenceRing({
  confidence = 0,
  size = 120,
  strokeWidth = 8,
  isUnknown = false,
  label,
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const pct = Math.round(confidence * 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - confidence);

  // Color tiers
  const getColor = () => {
    if (isUnknown) return { main: '#f59e0b', glow: 'rgba(245,158,11,0.45)', tier: 'amber' };
    if (pct >= 80) return { main: '#22c55e', glow: 'rgba(34,197,94,0.45)', tier: 'green' };
    if (pct >= 60) return { main: '#3b82f6', glow: 'rgba(59,130,246,0.40)', tier: 'blue' };
    if (pct >= 50) return { main: '#f97316', glow: 'rgba(249,115,22,0.40)', tier: 'orange' };
    return { main: '#ef4444', glow: 'rgba(239,68,68,0.40)', tier: 'red' };
  };

  const color = getColor();

  // Gradient IDs unique per instance
  const gradId = `conf-grad-${size}-${pct}`;
  const glowId = `conf-glow-${size}-${pct}`;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      {/* Outer glow pulse */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: `radial-gradient(circle, ${color.glow} 0%, transparent 70%)`,
        }}
        animate={mounted ? { scale: [1, 1.15, 1], opacity: [0.6, 0.3, 0.6] } : {}}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      />

      <svg width={size} height={size} className="transform -rotate-90">
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color.main} />
            <stop offset="100%" stopColor={color.main} stopOpacity="0.6" />
          </linearGradient>
          <filter id={glowId}>
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          className="text-gray-200 dark:text-gray-700/50"
          strokeWidth={strokeWidth}
        />

        {/* Progress arc */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={mounted ? { strokeDashoffset: offset } : {}}
          transition={{ duration: 1.4, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.2 }}
          filter={`url(#${glowId})`}
        />

        {/* Tip dot */}
        {pct > 0 && (
          <motion.circle
            cx={size / 2 + radius * Math.cos(2 * Math.PI * confidence - Math.PI / 2)}
            cy={size / 2 + radius * Math.sin(2 * Math.PI * confidence - Math.PI / 2)}
            r={strokeWidth / 2 + 1}
            fill={color.main}
            initial={{ scale: 0 }}
            animate={mounted ? { scale: 1 } : {}}
            transition={{ delay: 1.5, type: 'spring', stiffness: 300 }}
          />
        )}
      </svg>

      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="font-mono font-extrabold leading-none"
          style={{ fontSize: size * 0.26, color: color.main }}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={mounted ? { opacity: 1, scale: 1 } : {}}
          transition={{ delay: 0.6, type: 'spring', stiffness: 200 }}
        >
          {pct}%
        </motion.span>
        <motion.span
          className="text-[10px] uppercase tracking-widest font-semibold text-gray-400 dark:text-gray-500 mt-0.5"
          initial={{ opacity: 0, y: 4 }}
          animate={mounted ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.9 }}
        >
          {label || (isUnknown ? 'Unknown' : pct >= 80 ? 'High' : pct >= 60 ? 'Good' : pct >= 50 ? 'Fair' : 'Low')}
        </motion.span>
      </div>
    </div>
  );
}
