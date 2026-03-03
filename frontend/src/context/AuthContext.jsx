import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Initialize from cache so UI doesn't flicker/lose avatar on reload
  const [user, setUser] = useState(() => {
    const cached = localStorage.getItem('wildtrack_user');
    return cached ? JSON.parse(cached) : null;
  });
  const [loading, setLoading] = useState(true);

  // Resolve avatar URL (relative → absolute)
  const resolveAvatar = (u) => {
    if (!u) return u;
    if (u.avatar && u.avatar.startsWith('/uploads')) {
      const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      return { ...u, avatar: `${base}${u.avatar}` };
    }
    return u;
  };

  // On mount: validate stored token against backend
  useEffect(() => {
    const token = localStorage.getItem('wildtrack_token');
    if (!token) {
      localStorage.removeItem('wildtrack_user');
      setUser(null);
      setLoading(false);
      return;
    }
    api.getMe()
      .then((res) => {
        const u = resolveAvatar(res.data.user);
        setUser(u);
        localStorage.setItem('wildtrack_user', JSON.stringify(u));
      })
      .catch(() => {
        // Token invalid/expired — clean up
        localStorage.removeItem('wildtrack_token');
        localStorage.removeItem('wildtrack_user');
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.login(email, password);
    const { token, user: userData } = res.data;
    localStorage.setItem('wildtrack_token', token);
    const u = resolveAvatar(userData);
    setUser(u);
    localStorage.setItem('wildtrack_user', JSON.stringify(u));
    return u;
  }, []);

  const register = useCallback(async (name, email, password) => {
    const res = await api.register(name, email, password);
    const { token, user: userData } = res.data;
    localStorage.setItem('wildtrack_token', token);
    const u = resolveAvatar(userData);
    setUser(u);
    localStorage.setItem('wildtrack_user', JSON.stringify(u));
    return u;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('wildtrack_token');
    localStorage.removeItem('wildtrack_user');
  }, []);

  // Refresh user object (after profile update, avatar change, etc.)
  const refreshUser = useCallback(async () => {
    try {
      const res = await api.getMe();
      const u = resolveAvatar(res.data.user);
      setUser(u);
      localStorage.setItem('wildtrack_user', JSON.stringify(u));
      return u;
    } catch {
      return user;
    }
  }, [user]);

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
