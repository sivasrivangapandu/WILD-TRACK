import { motion } from 'framer-motion';
import { FiAlertCircle, FiCheck } from 'react-icons/fi';

export function ValidatedInput({
  label,
  placeholder,
  type = 'text',
  value,
  onChange,
  error,
  success,
  required = false,
  minLength,
  pattern,
  disabled = false,
  ...props
}) {
  const handleChange = (e) => {
    onChange?.(e);
  };

  const validate = (val) => {
    if (required && !val) return 'This field is required';
    if (minLength && val.length < minLength) return `Minimum ${minLength} characters`;
    if (pattern && !pattern.test(val)) return 'Invalid format';
    return null;
  };

  const validationError = error || validate(value);

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <div className="relative">
        <input
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={`w-full px-4 py-2.5 rounded-lg border-2 transition-all focus:outline-none focus:ring-2 ${
            validationError
              ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20 bg-red-500/5'
              : success
                ? 'border-green-500/50 focus:border-green-500 focus:ring-green-500/20 bg-green-500/5'
                : 'border-gray-300 dark:border-gray-600 focus:border-orange-500 focus:ring-orange-500/20 dark:bg-gray-800 dark:text-white'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          {...props}
        />
        {validationError && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-red-500">
            <FiAlertCircle size={18} />
          </motion.div>
        )}
        {success && !validationError && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500">
            <FiCheck size={18} />
          </motion.div>
        )}
      </div>
      {validationError && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xs text-red-500 font-medium">
          {validationError}
        </motion.p>
      )}
    </div>
  );
}

export function ValidatedForm({ onSubmit, children, isLoading = false, submitLabel = 'Submit' }) {
  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit?.(e);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {children}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold hover:shadow-lg hover:shadow-orange-500/20 transition disabled:opacity-50 disabled:cursor-not-allowed">
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
            />
            Loading...
          </span>
        ) : (
          submitLabel
        )}
      </button>
    </form>
  );
}
