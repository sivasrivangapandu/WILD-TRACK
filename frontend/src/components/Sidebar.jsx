import { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import ThemeSelector from './ThemeSelector';
import {
  FiHome, FiUpload, FiBarChart2, FiSearch, FiLayers,
  FiClock, FiMenu, FiX,
  FiGitBranch, FiInfo, FiMessageCircle,
  FiSettings, FiLogOut, FiMap, FiActivity
} from 'react-icons/fi';
import { GiPawPrint } from 'react-icons/gi';

const navItems = [
  { path: '/', icon: FiHome, label: 'Home' },
  { path: '/map', icon: FiMap, label: 'Global Map' },
  { path: '/upload', icon: FiUpload, label: 'Upload' },
  { path: '/chat', icon: FiMessageCircle, label: 'AI Chat' },
  { path: '/dashboard', icon: FiBarChart2, label: 'Dashboard' },
  { path: '/mlops', icon: FiActivity, label: 'MLOps Lab' },
  { path: '/species', icon: FiSearch, label: 'Species' },
  { path: '/compare', icon: FiGitBranch, label: 'Compare' },
  { path: '/batch', icon: FiLayers, label: 'Batch' },
  { path: '/history', icon: FiClock, label: 'History' },
];

const secondaryItems = [
  { path: '/settings', icon: FiSettings, label: 'Settings' },
  { path: '/about', icon: FiInfo, label: 'About' },
];

export default function Sidebar() {
  const { theme, dark } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const handleLogout = () => { logout(); navigate('/login'); };

  const renderNavItem = ({ path, icon: Icon, label }) => {
    const isActive = path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);
    return (
      <NavLink
        key={path}
        to={path}
        end={path === '/'}
        onClick={() => setMobileOpen(false)}
        className={`relative flex items-center gap-3 px-3 py-2.5 sm:py-2 rounded-lg text-sm sm:text-[13px] transition-colors duration-150 ${isActive
          ? 'font-medium'
          : 't-secondary hover:t-primary surface-hover'
          }`}
      >
        {isActive && (
          <motion.div
            layoutId="sidebar-pill"
            className="absolute inset-0 rounded-lg"
            style={{ backgroundColor: theme.primary + '18' }}
            transition={{ type: 'spring', stiffness: 380, damping: 28 }}
          />
        )}
        <Icon size={16} className="relative z-10 flex-shrink-0" />
        {!collapsed && <span className="relative z-10">{label}</span>}
      </NavLink>
    );
  };

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2.5 rounded-lg transition-colors"
        style={{
          backgroundColor: 'var(--bg-surface-2)',
          border: '1px solid var(--border-primary)',
        }}
      >
        {mobileOpen ? <FiX size={20} /> : <FiMenu size={20} />}
      </button>

      {/* Backdrop for mobile */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-full z-40 w-72 sm:w-60 flex flex-col transition-transform duration-300 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0`}
        style={{
          backgroundColor: 'var(--bg-primary)',
          backdropFilter: 'blur(20px) saturate(1.4)',
          borderRight: '1px solid var(--border-primary)',
        }}
      >
      {/* ── Brand ── */}
      <div className="px-4 py-5 sm:py-4 flex items-center gap-3">
        <motion.div
          className={`w-8 h-8 rounded-lg bg-gradient-to-br ${theme.gradient} flex items-center justify-center flex-shrink-0 animate-logo-breathe`}
          animate={{
            boxShadow: [
              `0 0 0px ${theme.primary}00`,
              `0 0 12px ${theme.primary}40`,
              `0 0 0px ${theme.primary}00`,
            ]
          }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
          <GiPawPrint className="text-white text-sm" />
        </motion.div>
        {!collapsed && (
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight t-primary">
              WildTrack
            </span>
            <span className="text-[9px] font-bold uppercase tracking-widest text-orange-500/70">
              AI v4
            </span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`ml-auto p-1.5 rounded-md transition-colors t-tertiary surface-hover hidden lg:block`}
        >
          {collapsed ? <FiMenu size={15} /> : <FiX size={15} />}
        </button>
      </div>

      {/* ── Primary nav ── */}
      <nav className="flex-1 px-3 py-1 space-y-0.5 overflow-y-auto sidebar-scroll">
        {navItems.map(renderNavItem)}

        <div className="my-3 mx-1 h-px" style={{ backgroundColor: 'var(--border-subtle)' }} />

        {secondaryItems.map(renderNavItem)}
      </nav>

      {/* ── Footer ── */}
      <div className="px-3 py-3 space-y-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
        <ThemeSelector />
        {user && (
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 sm:py-1.5 rounded-lg text-sm sm:text-xs font-medium t-secondary hover:text-red-400 hover:bg-red-500/[0.06] transition-colors"
          >
            <FiLogOut size={14} className="sm:w-[13px] sm:h-[13px]" />
            {!collapsed && 'Logout'}
          </button>
        )}
      </div>
    </aside>
    </>
  );
}
