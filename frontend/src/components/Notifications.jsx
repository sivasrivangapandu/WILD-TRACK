import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiCheckCircle, FiAlertCircle, FiInfo, FiXCircle, FiX } from 'react-icons/fi';

export function useNotifications() {
  const [notifications, setNotifications] = useState([]);

  const addNotification = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);
    
    if (duration > 0) {
      setTimeout(() => removeNotification(id), duration);
    }
    
    return id;
  }, []);

  const removeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  return { notifications, addNotification, removeNotification };
}

const notificationStyles = {
  success: {
    bg: 'bg-green-500/10 border-green-500/30',
    icon: FiCheckCircle,
    text: 'text-green-700 dark:text-green-400',
    iconColor: 'text-green-500',
  },
  error: {
    bg: 'bg-red-500/10 border-red-500/30',
    icon: FiXCircle,
    text: 'text-red-700 dark:text-red-400',
    iconColor: 'text-red-500',
  },
  warning: {
    bg: 'bg-yellow-500/10 border-yellow-500/30',
    icon: FiAlertCircle,
    text: 'text-yellow-700 dark:text-yellow-400',
    iconColor: 'text-yellow-500',
  },
  info: {
    bg: 'bg-blue-500/10 border-blue-500/30',
    icon: FiInfo,
    text: 'text-blue-700 dark:text-blue-400',
    iconColor: 'text-blue-500',
  },
};

function Notification({ notification, onClose }) {
  const style = notificationStyles[notification.type];
  const Icon = style.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 100, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      className={`${style.bg} border rounded-xl backdrop-blur-sm px-4 py-3 flex items-center gap-3 shadow-lg max-w-sm`}>
      <Icon size={18} className={style.iconColor} />
      <span className={`text-sm font-medium flex-1 ${style.text}`}>{notification.message}</span>
      <button
        onClick={() => onClose(notification.id)}
        className="p-1 hover:opacity-60 transition">
        <FiX size={16} />
      </button>
    </motion.div>
  );
}

export function NotificationContainer({ notifications, removeNotification }) {
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      <AnimatePresence mode="popLayout">
        {notifications.map((notification) => (
          <Notification
            key={notification.id}
            notification={notification}
            onClose={removeNotification}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
