import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '../context/ThemeContext';
import { FiCheck, FiSun, FiMoon, FiChevronUp } from 'react-icons/fi';

export default function ThemeSelector() {
  const { currentTheme, theme, changeTheme, themes, dark, toggle } = useTheme();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="w-full flex flex-col gap-1.5">
      {/* Inline theme grid — expands in-place above the trigger */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="overflow-hidden"
          >
            <div className="pb-1.5">
              <div className="p-2 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                <div className="grid grid-cols-3 gap-1.5">
                  {Object.entries(themes).map(([key, td]) => {
                    const active = currentTheme === key;
                    return (
                      <button
                        key={key}
                        onClick={() => { changeTheme(key); setIsOpen(false); }}
                        className={`relative rounded-md p-2 text-[10px] font-semibold text-white transition-all duration-150 bg-gradient-to-br ${td.gradient} ${
                          active ? 'ring-1.5 ring-white/60 shadow-sm' : 'opacity-70 hover:opacity-100'
                        }`}
                      >
                        {td.name}
                        {active && (
                          <span className="absolute top-0.5 right-0.5 w-3.5 h-3.5 rounded-full bg-white flex items-center justify-center">
                            <FiCheck size={8} className="text-gray-900" strokeWidth={3} />
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Controls row */}
      <div className="flex items-center gap-1.5">
        {/* Dark / Light toggle */}
        <button
          onClick={toggle}
          className="p-2 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-gray-400 hover:text-white transition-colors flex-shrink-0"
          title={dark ? 'Light mode' : 'Dark mode'}
        >
          {dark ? <FiMoon size={15} /> : <FiSun size={15} />}
        </button>

        {/* Theme picker trigger */}
        <button
          onClick={() => setIsOpen(o => !o)}
          className={`flex-1 flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
            isOpen
              ? 'bg-white/[0.1] text-white'
              : 'bg-white/[0.06] hover:bg-white/[0.1] text-gray-400 hover:text-white'
          }`}
        >
          <span className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full bg-gradient-to-br ${theme.gradient} flex-shrink-0`} />
            {themes[currentTheme]?.name}
          </span>
          <FiChevronUp
            size={13}
            className={`transition-transform duration-200 ${isOpen ? '' : 'rotate-180'}`}
          />
        </button>
      </div>
    </div>
  );
}
