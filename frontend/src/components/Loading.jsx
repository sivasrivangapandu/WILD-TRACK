import { motion } from 'framer-motion';
import { GiPawPrint } from 'react-icons/gi';

export function Loading({ size = 'md', text = 'Loading...' }) {
  const sizeMap = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-[2.5px]',
    lg: 'w-12 h-12 border-3',
  };

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
        className={`${sizeMap[size]} border-orange-500/20 border-t-orange-500 rounded-full`}
      />
      {text && <p className="text-sm text-gray-500">{text}</p>}
    </div>
  );
}

export function SkeletonLoader({ count = 3, lines = 3 }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="space-y-2 animate-pulse">
          {Array.from({ length: lines }).map((_, j) => (
            <div
              key={j}
              className={`h-3 rounded-lg bg-white/[0.06] ${
                j === lines - 1 ? 'w-2/3' : 'w-full'
              }`}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-5">
      <motion.div
        animate={{ scale: [1, 1.06, 1] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
        className="w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20"
      >
        <GiPawPrint className="text-white text-3xl" />
      </motion.div>
      <div className="text-center">
        <h2 className="text-lg font-semibold tracking-tight">WildTrackAI</h2>
        <motion.p
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="text-gray-500 text-sm mt-1"
        >Loading…</motion.p>
      </div>
    </div>
  );
}
