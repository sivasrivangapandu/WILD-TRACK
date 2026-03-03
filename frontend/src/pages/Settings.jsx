import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiUser, FiLock, FiBell, FiShield, FiSliders,
  FiCamera, FiSave, FiTrash2, FiDownload, FiEye, FiEyeOff,
  FiCheck, FiAlertTriangle
} from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useToast, ToastContainer } from '../components/Toast';
import api from '../services/api';

/* ═══ Tabs ═══ */
const TABS = [
  { id: 'profile', label: 'Profile', icon: FiUser },
  { id: 'security', label: 'Security', icon: FiLock },
  { id: 'notifications', label: 'Notifications', icon: FiBell },
  { id: 'behavior', label: 'Behavior', icon: FiSliders },
  { id: 'privacy', label: 'Privacy', icon: FiShield },
];

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const { dark } = useTheme();
  const { toasts, addToast, removeToast } = useToast();
  const avatarRef = useRef(null);

  const [activeTab, setActiveTab] = useState('profile');
  const [saving, setSaving] = useState(false);

  /* ── Profile state ── */
  const [profileData, setProfileData] = useState({
    name: user?.name || '',
    email: user?.email || '',
  });
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [avatarFile, setAvatarFile] = useState(null);

  /* ── Security state ── */
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });

  /* ── Notifications state ── */
  const [notifications, setNotifications] = useState({
    email_alerts: true,
    prediction_complete: true,
    weekly_summary: false,
    marketing: false,
  });

  /* ── Behavior state ── */
  const [behaviorSettings, setBehaviorSettings] = useState({
    confidenceThreshold: 0.4,
    animationsEnabled: true,
    notificationStyle: 'toast',
    predictionMode: 'standard',
    autoSaveResults: true,
  });

  const cardClass = 'surface-card-lg glass-glow';

  /* ═══ Handlers ═══ */

  const handleAvatarChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    const reader = new FileReader();
    reader.onloadend = () => setAvatarPreview(reader.result);
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await api.updateProfile(profileData);
      if (avatarFile) {
        await api.uploadAvatar(avatarFile);
        setAvatarFile(null);
      }
      await refreshUser();
      addToast('Profile updated successfully', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to update profile', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (passwordData.new_password !== passwordData.confirm_password) {
      addToast('New passwords do not match', 'error');
      return;
    }
    if (passwordData.new_password.length < 6) {
      addToast('Password must be at least 6 characters', 'error');
      return;
    }
    setSaving(true);
    try {
      await api.changePassword(passwordData.current_password, passwordData.new_password);
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
      addToast('Password changed successfully', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to change password', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotifications = async () => {
    setSaving(true);
    try {
      await api.updateNotifications(notifications);
      addToast('Notification preferences saved', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to save notifications', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) return;
    try {
      await api.deleteAccount();
      addToast('Account deleted', 'info');
      window.location.href = '/login';
    } catch (err) {
      addToast(err.message || 'Failed to delete account', 'error');
    }
  };

  const handleExportData = () => {
    const blob = new Blob([JSON.stringify({ user, behaviorSettings, notifications }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'wildtrack_data_export.json';
    a.click();
    URL.revokeObjectURL(url);
    addToast('Data exported successfully', 'success');
  };

  /* ═══ Tab content renderers ═══ */

  const renderProfile = () => (
    <div className="space-y-6">
      {/* Avatar */}
      <div className="flex items-center gap-6">
        <div className="relative group">
          <div className="w-20 h-20 rounded-full overflow-hidden bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center text-white text-2xl font-bold shadow-lg">
            {avatarPreview || user?.avatar ? (
              <img src={avatarPreview || user?.avatar} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              (user?.name?.[0] || 'U').toUpperCase()
            )}
          </div>
          <button
            onClick={() => avatarRef.current?.click()}
            className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center"
          >
            <FiCamera className="text-white text-lg" />
          </button>
          <input ref={avatarRef} type="file" accept="image/*" className="hidden" onChange={handleAvatarChange} />
        </div>
        <div>
          <h3 className="font-semibold text-lg">{user?.name || 'User'}</h3>
          <p className="text-sm t-tertiary">{user?.email}</p>
        </div>
      </div>

      {/* Name */}
      <div>
        <label className="block text-sm font-medium mb-1.5">Name</label>
        <input
          type="text"
          value={profileData.name}
          onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
          className="w-full px-4 py-2.5 rounded-lg border transition focus:outline-none focus:ring-2 focus:ring-orange-500/40"
          style={{ background: 'var(--bg-surface-2)', borderColor: 'var(--border-color)' }}
        />
      </div>

      {/* Email */}
      <div>
        <label className="block text-sm font-medium mb-1.5">Email</label>
        <input
          type="email"
          value={profileData.email}
          onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
          className="w-full px-4 py-2.5 rounded-lg border transition focus:outline-none focus:ring-2 focus:ring-orange-500/40"
          style={{ background: 'var(--bg-surface-2)', borderColor: 'var(--border-color)' }}
        />
      </div>

      <button onClick={handleSaveProfile} disabled={saving} className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold hover:opacity-90 transition disabled:opacity-50">
        <FiSave size={16} /> {saving ? 'Saving...' : 'Save Profile'}
      </button>
    </div>
  );

  const renderSecurity = () => (
    <div className="space-y-6">
      <h3 className="font-semibold text-lg">Change Password</h3>

      {['current_password', 'new_password', 'confirm_password'].map((field) => {
        const label = field.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        const showKey = field === 'current_password' ? 'current' : field === 'new_password' ? 'new' : 'confirm';
        return (
          <div key={field}>
            <label className="block text-sm font-medium mb-1.5">{label}</label>
            <div className="relative">
              <input
                type={showPasswords[showKey] ? 'text' : 'password'}
                value={passwordData[field]}
                onChange={(e) => setPasswordData({ ...passwordData, [field]: e.target.value })}
                className="w-full px-4 py-2.5 rounded-lg border transition focus:outline-none focus:ring-2 focus:ring-orange-500/40 pr-10"
                style={{ background: 'var(--bg-surface-2)', borderColor: 'var(--border-color)' }}
                placeholder={`Enter ${label.toLowerCase()}`}
              />
              <button
                type="button"
                onClick={() => setShowPasswords({ ...showPasswords, [showKey]: !showPasswords[showKey] })}
                className="absolute right-3 top-1/2 -translate-y-1/2 t-tertiary hover:opacity-70 transition"
              >
                {showPasswords[showKey] ? <FiEyeOff size={16} /> : <FiEye size={16} />}
              </button>
            </div>
          </div>
        );
      })}

      <button onClick={handleChangePassword} disabled={saving} className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold hover:opacity-90 transition disabled:opacity-50">
        <FiLock size={16} /> {saving ? 'Changing...' : 'Change Password'}
      </button>

      {/* Active Sessions */}
      <div className="pt-4 border-t" style={{ borderColor: 'var(--border-color)' }}>
        <h3 className="font-semibold text-lg mb-3">Active Sessions</h3>
        <div className="p-4 rounded-lg flex items-center gap-3" style={{ background: 'var(--bg-surface-2)' }}>
          <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
            <FiCheck className="text-green-500" size={16} />
          </div>
          <div>
            <div className="text-sm font-medium">Current Session</div>
            <div className="text-xs t-tertiary">This device &middot; Active now</div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderNotifications = () => {
    const toggles = [
      { key: 'email_alerts', label: 'Email Alerts', desc: 'Receive important updates via email' },
      { key: 'prediction_complete', label: 'Prediction Notifications', desc: 'Get notified when predictions are complete' },
      { key: 'weekly_summary', label: 'Weekly Summary', desc: 'Receive a weekly activity summary' },
      { key: 'marketing', label: 'Product Updates', desc: 'News about features and improvements' },
    ];

    return (
      <div className="space-y-4">
        {toggles.map(({ key, label, desc }) => (
          <div key={key} className="flex items-center justify-between p-4 rounded-lg" style={{ background: 'var(--bg-surface-2)' }}>
            <div>
              <div className="text-sm font-medium">{label}</div>
              <div className="text-xs t-tertiary">{desc}</div>
            </div>
            <button
              onClick={() => setNotifications({ ...notifications, [key]: !notifications[key] })}
              className={`relative w-11 h-6 rounded-full transition-colors ${notifications[key] ? 'bg-orange-500' : 'bg-gray-500/30'}`}
              role="switch"
              aria-checked={notifications[key]}
            >
              <motion.div
                layout
                className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow"
                animate={{ left: notifications[key] ? '22px' : '2px' }}
                transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              />
            </button>
          </div>
        ))}

        <button onClick={handleSaveNotifications} disabled={saving} className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold hover:opacity-90 transition disabled:opacity-50 mt-4">
          <FiSave size={16} /> {saving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    );
  };

  const renderBehavior = () => (
    <div className="space-y-6">
      {/* Confidence Threshold */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Confidence Threshold: <span className="text-orange-500 font-mono">{(behaviorSettings.confidenceThreshold * 100).toFixed(0)}%</span>
        </label>
        <input
          type="range"
          min="0.3"
          max="0.95"
          step="0.05"
          value={behaviorSettings.confidenceThreshold}
          onChange={(e) => setBehaviorSettings({ ...behaviorSettings, confidenceThreshold: parseFloat(e.target.value) })}
          className="w-full accent-orange-500"
        />
        <div className="flex justify-between text-xs t-tertiary mt-1">
          <span>30%</span>
          <span>95%</span>
        </div>
      </div>

      {/* Prediction Mode */}
      <div>
        <label className="block text-sm font-medium mb-2">Prediction Mode</label>
        <div className="space-y-2">
          {[
            { value: 'standard', label: 'Standard', desc: 'Balanced accuracy & speed' },
            { value: 'accuracy', label: 'Accuracy Mode', desc: 'Prioritize confidence' },
            { value: 'fast', label: 'Fast Mode', desc: 'Speed optimized' },
          ].map(({ value, label, desc }) => (
            <label
              key={value}
              className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition ${
                behaviorSettings.predictionMode === value
                  ? 'border-orange-500/50 bg-orange-500/10'
                  : 'border-transparent'
              }`}
              style={{ background: behaviorSettings.predictionMode === value ? undefined : 'var(--bg-surface-2)' }}
            >
              <input
                type="radio"
                name="predictionMode"
                value={value}
                checked={behaviorSettings.predictionMode === value}
                onChange={(e) => setBehaviorSettings({ ...behaviorSettings, predictionMode: e.target.value })}
                className="accent-orange-500"
              />
              <div>
                <div className="text-sm font-medium">{label}</div>
                <div className="text-xs t-tertiary">{desc}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Notification Style */}
      <div>
        <label className="block text-sm font-medium mb-2">Notification Style</label>
        <div className="space-y-2">
          {[
            { value: 'toast', label: 'Toast', desc: 'Non-intrusive pop-ups' },
            { value: 'modal', label: 'Modal', desc: 'Detailed dialog' },
            { value: 'banner', label: 'Banner', desc: 'Prominent top banner' },
          ].map(({ value, label, desc }) => (
            <label
              key={value}
              className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition ${
                behaviorSettings.notificationStyle === value
                  ? 'border-orange-500/50 bg-orange-500/10'
                  : 'border-transparent'
              }`}
              style={{ background: behaviorSettings.notificationStyle === value ? undefined : 'var(--bg-surface-2)' }}
            >
              <input
                type="radio"
                name="notificationStyle"
                value={value}
                checked={behaviorSettings.notificationStyle === value}
                onChange={(e) => setBehaviorSettings({ ...behaviorSettings, notificationStyle: e.target.value })}
                className="accent-orange-500"
              />
              <div>
                <div className="text-sm font-medium">{label}</div>
                <div className="text-xs t-tertiary">{desc}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Toggle Controls */}
      <div className="space-y-3">
        {[
          { key: 'animationsEnabled', label: 'Enable Animations', desc: 'Smooth UI transitions and effects' },
          { key: 'autoSaveResults', label: 'Auto-Save Results', desc: 'Automatically save predictions to history' },
        ].map(({ key, label, desc }) => (
          <div key={key} className="flex items-center justify-between p-4 rounded-lg" style={{ background: 'var(--bg-surface-2)' }}>
            <div>
              <div className="text-sm font-medium">{label}</div>
              <div className="text-xs t-tertiary">{desc}</div>
            </div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={behaviorSettings[key]}
                onChange={(e) => setBehaviorSettings({ ...behaviorSettings, [key]: e.target.checked })}
                className="accent-orange-500 w-4 h-4"
              />
            </label>
          </div>
        ))}
      </div>
    </div>
  );

  const renderPrivacy = () => (
    <div className="space-y-6">
      {/* Data Export */}
      <div className="p-4 rounded-lg" style={{ background: 'var(--bg-surface-2)' }}>
        <h3 className="font-semibold mb-1">Export Your Data</h3>
        <p className="text-sm t-tertiary mb-3">Download a copy of your data in JSON format.</p>
        <button onClick={handleExportData} className="flex items-center gap-2 px-4 py-2 rounded-lg border border-orange-500/30 text-orange-500 text-sm font-medium hover:bg-orange-500/10 transition">
          <FiDownload size={16} /> Export Data
        </button>
      </div>

      {/* Danger Zone */}
      <div className="p-4 rounded-lg border border-red-500/20 bg-red-500/5">
        <div className="flex items-center gap-2 mb-2">
          <FiAlertTriangle className="text-red-500" />
          <h3 className="font-semibold text-red-500">Danger Zone</h3>
        </div>
        <p className="text-sm t-tertiary mb-3">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>
        <button onClick={handleDeleteAccount} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm font-medium hover:bg-red-500/20 transition">
          <FiTrash2 size={16} /> Delete Account
        </button>
      </div>
    </div>
  );

  const tabContent = {
    profile: renderProfile,
    security: renderSecurity,
    notifications: renderNotifications,
    behavior: renderBehavior,
    privacy: renderPrivacy,
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <motion.div whileHover={{ rotate: 10 }} className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
          <FiSliders className="text-white text-lg" />
        </motion.div>
        <div>
          <h1 className="text-2xl font-bold neon-heading">Settings</h1>
          <p className="text-sm t-tertiary">Manage your account and preferences</p>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Side tabs */}
        <div className={`${cardClass} p-2 md:w-52 shrink-0`}>
          <nav className="flex md:flex-col gap-1">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition w-full text-left ${
                    active
                      ? 'bg-orange-500/15 text-orange-500'
                      : 't-secondary hover:bg-white/5'
                  }`}
                >
                  <Icon size={16} />
                  <span className="hidden md:inline">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className={`${cardClass} p-6 flex-1 min-h-[400px]`}>
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {tabContent[activeTab]?.()}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </div>
  );
}
