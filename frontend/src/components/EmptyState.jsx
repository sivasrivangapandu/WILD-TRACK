import { motion } from 'framer-motion';
import { FiInbox, FiSearch, FiFile, FiMessageSquare } from 'react-icons/fi';

const emptyStates = {
  inbox: {
    icon: FiInbox,
    title: 'No items here',
    description: 'Start by uploading an image or creating something new',
    color: 'blue',
  },
  search: {
    icon: FiSearch,
    title: 'No results found',
    description: 'Try adjusting your filters or search terms',
    color: 'purple',
  },
  history: {
    icon: FiFile,
    title: 'No history yet',
    description: 'Your activities will appear here',
    color: 'amber',
  },
  chat: {
    icon: FiMessageSquare,
    title: 'Start a conversation',
    description: 'Begin by sending a message or asking a question',
    color: 'green',
  },
};

export default function EmptyState({ type = 'inbox', action, actionLabel }) {
  const state = emptyStates[type];
  const Icon = state.icon;
  
  const colorMap = {
    blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-500', button: 'from-blue-500 to-cyan-500' },
    purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/30', text: 'text-purple-500', button: 'from-purple-500 to-pink-500' },
    amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-500', button: 'from-amber-500 to-orange-500' },
    green: { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-500', button: 'from-green-500 to-emerald-500' },
  };

  const colors = colorMap[state.color];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={`flex flex-col items-center justify-center p-12 rounded-2xl border ${colors.bg} ${colors.border}`}>
      {/* Icon */}
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
        className={`mb-6 p-4 rounded-full ${colors.bg} border ${colors.border}`}>
        <Icon size={40} className={colors.text} />
      </motion.div>

      {/* Text */}
      <h3 className="text-lg font-semibold mb-2 text-center">{state.title}</h3>
      <p className="text-sm text-gray-500 text-center mb-6 max-w-xs">{state.description}</p>

      {/* Action Button */}
      {action && actionLabel && (
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={action}
          className={`px-6 py-2.5 rounded-lg bg-gradient-to-r ${colors.button} text-white font-semibold text-sm hover:shadow-lg hover:shadow-${state.color}-500/20 transition`}>
          {actionLabel}
        </motion.button>
      )}
    </motion.div>
  );
}
