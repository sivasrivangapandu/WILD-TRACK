import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { FiMail, FiLock, FiUser, FiEye, FiEyeOff, FiArrowRight } from 'react-icons/fi';
import { GiPawPrint } from 'react-icons/gi';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, login, register } = useAuth();
  const { theme } = useTheme();
  
  const [mode, setMode] = useState('login');
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [user, navigate, location]);

  // Lightweight particles — 8 instead of 30
  const particles = useMemo(() =>
    Array.from({ length: 8 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 3 + 1.5,
      duration: Math.random() * 14 + 12,
      delay: Math.random() * 4,
    })),
  []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'login') {
        await login(formData.email, formData.password);
      } else {
        await register(formData.name, formData.email, formData.password);
      }
      
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: '🚀', text: 'Lightning Fast' },
    { icon: '🔒', text: 'Secure & Private' },
    { icon: '🎨', text: 'Beautiful UI' },
  ];

  return (
    <div className="min-h-screen flex items-center justify-center overflow-hidden relative" style={{ backgroundColor: theme.bg }}>
      {/* Animated Particles */}
      {particles.map((particle) => (
        <motion.div
          key={particle.id}
          className="absolute rounded-full opacity-30"
          style={{
            left: `${particle.x}%`,
            top: `${particle.y}%`,
            width: particle.size,
            height: particle.size,
            background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
          }}
          animate={{
            y: [0, -30, 0],
            x: [0, Math.random() * 20 - 10, 0],
            opacity: [0.2, 0.5, 0.2],
          }}
          transition={{
            duration: particle.duration,
            delay: particle.delay,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}

      {/* Soft Gradient Orbs */}
      <div className="absolute top-0 left-0 w-80 h-80 rounded-full blur-3xl opacity-10" 
           style={{ background: `radial-gradient(circle, ${theme.primary}, transparent)` }} />
      <div className="absolute bottom-0 right-0 w-80 h-80 rounded-full blur-3xl opacity-10" 
           style={{ background: `radial-gradient(circle, ${theme.secondary}, transparent)` }} />

      {/* Main Container */}
      <div className="relative z-10 w-full max-w-5xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
        
        {/* Left Side - Branding */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="hidden lg:block text-white"
        >
          {/* Logo — static, no infinite rotation */}
          <div
            className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${theme.gradient} flex items-center justify-center mb-8 shadow-lg`}
          >
            <GiPawPrint className="text-white text-3xl" />
          </div>

          <h1 className="text-4xl font-bold mb-3 tracking-tight text-white">
            WildTrackAI
          </h1>
          <p className="text-base text-gray-400 mb-10 leading-relaxed max-w-md">
            Identify wildlife species instantly with cutting-edge AI. 
            Upload a photo and get accurate predictions in seconds.
          </p>

          {/* Features */}
          <div className="space-y-3">
            {features.map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.08 }}
                className="flex items-center gap-3"
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
                     style={{ backgroundColor: theme.primary + '18' }}>
                  {feature.icon}
                </div>
                <span className="text-gray-300 text-sm">{feature.text}</span>
              </motion.div>
            ))}
          </div>

          {/* Stats */}
          <div className="flex gap-8 mt-10">
            {[
              { value: '5+', label: 'Species' },
              { value: 'AI', label: 'Powered' },
              { value: '24/7', label: 'Available' },
            ].map((s, i) => (
              <div key={i}>
                <div className="text-xl font-bold" style={{ color: theme.primary }}>{s.value}</div>
                <div className="text-gray-500 text-xs mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Right Side - Form */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <div className="relative">
            {/* Glass Card — clean, no infinite glow */}
            <div className="relative bg-white/[0.04] backdrop-blur-xl rounded-2xl p-8 border border-white/[0.08] shadow-2xl"
                 style={{ boxShadow: `0 0 80px ${theme.primary}08` }}>

              {/* Mode Toggle */}
              <div className="flex gap-1 mb-7 p-1 bg-white/[0.04] rounded-xl border border-white/[0.06]">
                {['login', 'register'].map((m) => (
                  <button
                    key={m}
                    onClick={() => { setMode(m); setError(''); }}
                    className="relative flex-1 py-2.5 rounded-lg font-medium text-sm transition-all"
                  >
                    {mode === m && (
                      <motion.div
                        layoutId="mode-bg"
                        className={`absolute inset-0 bg-gradient-to-r ${theme.gradient} rounded-lg`}
                        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                      />
                    )}
                    <span className={`relative z-10 ${mode === m ? 'text-white' : 'text-gray-500'}`}>
                      {m === 'login' ? 'Sign In' : 'Create Account'}
                    </span>
                  </button>
                ))}
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Name (Register only) */}
                <AnimatePresence mode="wait">
                  {mode === 'register' && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="relative">
                        <FiUser className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                        <input
                          type="text"
                          placeholder="Full Name"
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-white/30 transition-all"
                          required={mode === 'register'}
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Email */}
                <div className="relative">
                  <FiMail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type="email"
                    placeholder="Email Address"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-white/30 transition-all"
                    required
                  />
                </div>

                {/* Password */}
                <div className="relative">
                  <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full pl-12 pr-12 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-white/30 transition-all"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition"
                  >
                    {showPassword ? <FiEyeOff size={18} /> : <FiEye size={18} />}
                  </button>
                </div>

                {/* Error Message */}
                <AnimatePresence>
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm"
                    >
                      {error}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Submit Button */}
                <motion.button
                  type="submit"
                  disabled={loading}
                  whileHover={{ scale: loading ? 1 : 1.02 }}
                  whileTap={{ scale: loading ? 1 : 0.98 }}
                  className={`w-full py-4 rounded-xl font-bold text-white bg-gradient-to-r ${theme.gradient} ${theme.glow} shadow-xl hover:shadow-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 overflow-hidden relative`}
                >
                  {loading ? (
                    <>
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                      />
                      <span>Processing...</span>
                      {/* Loading Bar */}
                      <motion.div
                        initial={{ x: '-100%' }}
                        animate={{ x: '100%' }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                      />
                    </>
                  ) : (
                    <>
                      <span>{mode === 'login' ? 'Sign In' : 'Create Account'}</span>
                      <FiArrowRight size={18} />
                    </>
                  )}
                </motion.button>
              </form>

              {/* Footer */}
              <div className="mt-6 text-center text-gray-400 text-sm">
                {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
                <button
                  onClick={() => {
                    setMode(mode === 'login' ? 'register' : 'login');
                    setError('');
                  }}
                  className={`font-semibold bg-gradient-to-r ${theme.gradient} bg-clip-text text-transparent hover:underline`}
                >
                  {mode === 'login' ? 'Sign up' : 'Sign in'}
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Mobile Logo */}
      <div className="lg:hidden absolute top-8 left-1/2 -translate-x-1/2">
        <div
          className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${theme.gradient} flex items-center justify-center shadow-lg`}
        >
          <GiPawPrint className="text-white text-2xl" />
        </div>
      </div>
    </div>
  );
}
