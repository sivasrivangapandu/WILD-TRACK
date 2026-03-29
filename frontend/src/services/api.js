/**
 * WildTrackAI - API Service Layer
 */
import axios from 'axios';

// Smart fallback for unconfigured deployments to prevent mixed-content Network Errors
const fallbackUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:8000'
  : 'https://wildtrack-backend-j9n8.onrender.com';

export const API_BASE = import.meta.env.VITE_API_URL || fallbackUrl;

const DEFAULT_TIMEOUT_MS = 120000;
const PREDICT_TIMEOUT_MS = 300000;
const PREDICT_RETRY_COUNT = 1;
const PREDICT_RETRY_DELAY_MS = 1500;
const AUTH_TIMEOUT_MS = 45000;
const AUTH_RETRY_COUNT = 1;
const AUTH_RETRY_DELAY_MS = 1200;

const api = axios.create({
  baseURL: API_BASE,
  timeout: DEFAULT_TIMEOUT_MS,
});

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const isRetryablePredictError = (err) => {
  if (!err) return false;
  if (err.isTimeout) return true;
  if (err.code === 'ECONNABORTED') return true;
  if (err.status === 503 || err.status === 504) return true;
  const msg = String(err.message || '').toLowerCase();
  return msg.includes('timeout') || msg.includes('network error');
};

const isRetryableAuthError = (err) => {
  if (!err) return false;
  if (err.isTimeout) return true;
  if (err.code === 'ECONNABORTED') return true;
  if (err.status === 502 || err.status === 503 || err.status === 504) return true;
  if (err.status === 429) return true;
  const msg = String(err.message || '').toLowerCase();
  return msg.includes('network error') || msg.includes('timeout') || msg.includes('failed to fetch');
};

const warmupBackend = async () => {
  try {
    await api.get('/health', { timeout: 15000 });
  } catch {
    // Best-effort warmup only.
  }
};

const postWithRetry = async (url, body, options = {}) => {
  const timeoutMs = options.timeoutMs || AUTH_TIMEOUT_MS;
  const maxRetries = Number.isInteger(options.retries) ? options.retries : AUTH_RETRY_COUNT;
  const retryDelayMs = Number.isInteger(options.retryDelayMs) ? options.retryDelayMs : AUTH_RETRY_DELAY_MS;

  let attempt = 0;
  while (true) {
    try {
      return await api.post(url, body, { timeout: timeoutMs });
    } catch (err) {
      if (attempt >= maxRetries || !isRetryableAuthError(err)) {
        throw err;
      }
      attempt += 1;
      await warmupBackend();
      await sleep(retryDelayMs);
    }
  }
};

// ── Attach JWT token to every request ─────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('wildtrack_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Network error';
    console.error('[API Error]', message);
    // Auto-logout on 401
    if (error.response?.status === 401) {
      localStorage.removeItem('wildtrack_token');
      localStorage.removeItem('wildtrack_user');
    }

    const normalizedError = new Error(message);
    normalizedError.status = error.response?.status;
    normalizedError.code = error.code;
    normalizedError.isTimeout = error.code === 'ECONNABORTED' || /timeout/i.test(String(message));
    throw normalizedError;
  }
);

// Helper: get token query param for auth endpoints
const _tokenParam = () => {
  const t = localStorage.getItem('wildtrack_token');
  return t ? { token: t } : {};
};

const apiService = {
  health: () => api.get('/health'),

  // ── Auth ────────────────────────────────────────────────────────
  register: (name, email, password) =>
    postWithRetry('/api/auth/register', { name, email, password }),

  login: (email, password) =>
    postWithRetry('/api/auth/login', { email, password }),

  getMe: () =>
    api.get('/api/auth/me', { params: _tokenParam() }),

  updateProfile: (data) =>
    api.put('/api/auth/profile', data, { params: _tokenParam() }),

  changePassword: (current_password, new_password) =>
    api.put('/api/auth/password', { current_password, new_password }, { params: _tokenParam() }),

  uploadAvatar: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/auth/avatar', formData, {
      params: _tokenParam(),
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  updateNotifications: (prefs) =>
    api.put('/api/auth/notifications', prefs, { params: _tokenParam() }),

  deleteAccount: () =>
    api.delete('/api/auth/account', { params: _tokenParam() }),

  // ── Predictions ─────────────────────────────────────────────────
  predict: async (file, location = null, options = {}) => {
    const timeoutMs = options.timeoutMs || PREDICT_TIMEOUT_MS;
    const maxRetries = Number.isInteger(options.retries) ? options.retries : PREDICT_RETRY_COUNT;
    const retryDelayMs = Number.isInteger(options.retryDelayMs) ? options.retryDelayMs : PREDICT_RETRY_DELAY_MS;

    const formData = new FormData();
    formData.append('file', file);
    if (location) {
      if (location.lat) formData.append('latitude', location.lat);
      if (location.lng) formData.append('longitude', location.lng);
    }

    let attempt = 0;
    while (true) {
      try {
        return await api.post('/predict', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: timeoutMs,
        });
      } catch (err) {
        if (attempt >= maxRetries || !isRetryablePredictError(err)) {
          throw err;
        }
        attempt += 1;
        await sleep(retryDelayMs);
      }
    }
  },

  predictBatch: (files) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return api.post('/predict/batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getSpecies: () => api.get('/species'),
  getSpeciesDetail: (name) => api.get(`/species/${name}`),

  // Gemini-powered species search
  searchSpecies: (query) => api.post('/species-search', { query }),

  getHistory: (limit = 50, offset = 0, species = null) => {
    const params = { limit, offset };
    if (species) params.species = species;
    return api.get('/history', { params });
  },

  getAnalytics: () => api.get('/analytics'),
  getModelMetrics: () => api.get('/model-metrics'),

  getSystemStatus: () => api.get('/api/system/status'),

  // Legacy chat endpoint
  chat: (message, file = null, sessionId = 'default') => {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('session_id', sessionId);
    if (file) formData.append('file', file);
    return api.post('/chat', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // Streaming + DB-backed chat session endpoints
  streamChat: (payload, signal) => fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  }),

  saveStreamedChat: (payload) => api.post('/api/chat/save', payload),
  createChatSession: (payload) => api.post('/api/chat/sessions', payload),
  listChatSessions: (userId) => api.get('/api/chat/sessions', { params: { user_id: String(userId) } }),
  getChatSession: (sessionId) => api.get(`/api/chat/sessions/${sessionId}`),
  deleteChatSession: (sessionId) => api.delete(`/api/chat/sessions/${sessionId}`),

  generateReport(file) {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/report', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob',
    });
  },

  // Wildlife knowledge base
  getAnimalInfo: (name) =>
    api.get('/api/animal-info', { params: { name } }),

  // ── MLOps & Active Learning ─────────────────────────────────────
  getReviewQueue: (limit = 50, offset = 0) =>
    api.get('/mlops/review-queue', { params: { limit, offset } }),

  submitReview: (predId, action, correctedSpecies = null) =>
    api.post(`/mlops/review/${predId}`, {
      action,
      corrected_species: correctedSpecies,
    }),

  getMlopsAnalytics: () => api.get('/mlops/analytics'),
};

export default apiService;
