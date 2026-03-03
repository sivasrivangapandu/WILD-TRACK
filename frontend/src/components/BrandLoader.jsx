import { motion } from 'framer-motion';
import { GiPawPrint } from 'react-icons/gi';
import { useTheme } from '../context/ThemeContext';

export default function BrandLoader({ text = 'Loading...' }) {
  const { theme } = useTheme();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center min-h-screen bg-gray-900"
      style={{ backgroundColor: `${theme.bg}` }}
    >
      {/* Container */}
      <div className="relative flex flex-col items-center">
        {/* Rotating ring background */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          className="absolute w-32 h-32 rounded-full border-2"
          style={{
            borderColor: `${theme.primary}25`,
            top: '-16px',
            left: '-16px',
          }}
        />

        {/* Pulsing outer circle */}
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute w-28 h-28 rounded-full"
          style={{
            backgroundColor: `${theme.primary}10`,
            top: '-8px',
            left: '-8px',
          }}
        />

        {/* Main logo container */}
        <motion.div
          animate={{
            y: [0, -8, 0],
          }}
          transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
          className="relative z-10 w-20 h-20 rounded-2xl flex items-center justify-center shadow-lg"
          style={{
            background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
            boxShadow: `0 20px 40px ${theme.primary}15, 0 0 40px ${theme.primary}20`,
          }}
        >
          {/* Rotating shine overlay */}
          <motion.div
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
            className="absolute inset-0 rounded-2xl bg-gradient-to-r from-white/0 via-white/20 to-white/0"
          />

          {/* Paw icon */}
          <GiPawPrint className="text-white text-2xl relative z-10" />
        </motion.div>

        {/* Loading text */}
        <motion.p
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="mt-8 text-sm font-medium"
          style={{ color: theme.secondary }}
        >
          {text}
        </motion.p>

        {/* Dots animation */}
        <div className="mt-2 flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: i * 0.2,
              }}
              className="w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: theme.primary }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}
