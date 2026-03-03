import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiCheck, FiAlertCircle, FiInfo, FiX } from 'react-icons/fi';

const toastStyles = {
  success: { bg: 'bg-green-500/10 border-green-500/30', text: 'text-green-700 dark:text-green-400', icon: 'text-green-500' },
  error: { bg: 'bg-red-500/10 border-red-500/30', text: 'text-red-700 dark:text-red-400', icon: 'text-red-500' },
  info: { bg: 'bg-blue-500/10 border-blue-500/30', text: 'text-blue-700 dark:text-blue-400', icon: 'text-blue-500' },
};

export function Toast({ message, type = 'info', onClose }) {
  const style = toastStyles[type];
  const icons = {
    success: FiCheck,
    error: FiAlertCircle,
    info: FiInfo,
  };
  const Icon = icons[type];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      className={`${style.bg} border rounded-lg backdrop-blur-sm px-4 py-3 flex items-center gap-3 shadow-lg`}>
      <Icon size={18} className={style.icon} />
      <span className={`text-sm font-medium flex-1 ${style.text}`}>{message}</span>
      <button onClick={onClose} className="p-1 hover:opacity-70 transition">
        <FiX size={16} />
      </button>
    </motion.div>
  );
}

export function ToastContainer({ toasts, removeToast }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

export function useToast() {
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'info', duration = 3000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration);
    }
    
    return id;
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return { toasts, addToast, removeToast };
}
