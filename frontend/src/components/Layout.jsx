import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import Sidebar from './Sidebar';
import AnimatedBackground from './AnimatedBackground';
import { PageLoader } from './Loading';

/* Route transition variants */
const pageTransition = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.15 } },
};

export default function Layout({ children }) {
  const { theme } = useTheme();
  const { user, loading } = useAuth();
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';

  // While auth state is being resolved, show a neutral loader — prevents flash
  if (loading) {
    return (
      <div className="min-h-screen" style={{ backgroundColor: theme.bg, color: theme.text }}>
        <PageLoader />
      </div>
    );
  }

  if (isLoginPage || !user) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen transition-colors duration-500" style={{ backgroundColor: theme.bg, color: theme.text }}>
      <AnimatedBackground />
      <Sidebar />
      <main className="lg:ml-60 min-h-screen transition-all duration-300 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              variants={pageTransition}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
