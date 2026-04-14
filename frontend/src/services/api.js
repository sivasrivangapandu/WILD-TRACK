/**
 * WildTrackAI - API Service Layer
 * ================================
 * Centralized HTTP client with:
 *  - Automatic retry + exponential back-off
 *  - Cold-start warm-up (Render free-tier)
 *  - Normalized error objects
 */
import axios from 'axios';

// Smart fallback for unconfigured deployments to prevent mixed-content Network Errors
const fallbackUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:8000'
  : 'https://wildtrack-backend-j9n8.onrender.com';

export const API_BASE = import.meta.env.VITE_API_URL || fallbackUrl;

// ── Timeout & Retry Configuration ─────────────────────────────────
const DEFAULT_TIMEOUT_MS = 120_000;     // 2 min for general requests
const PREDICT_TIMEOUT_MS = 300_000;     // 5 min for predict (TF on CPU is slow)
const PREDICT_RETRY_COUNT = 3;          // 3 retries = 4 total attempts
const PREDICT_RETRY_DELAY_MS = 2_500;
const AUTH_TIMEOUT_MS = 60_000;         // 1 min for auth
const AUTH_RETRY_COUNT = 4;             // Increased - server startup can be slow
const AUTH_RETRY_DELAY_MS = 1_500;      // Shorter between retries
const GET_RETRY_COUNT = 2;

const api = axios.create({
  baseURL: API_BASE,
  timeout: DEFAULT_TIMEOUT_MS,
});

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// ── Retry Eligibility ─────────────────────────────────────────────
const isRetryableError = (err) => {
  if (!err) return false;
  if (err.isTimeout) return true;
  if (err.code === 'ECONNABORTED') return true;
  if (err.code === 'ECONNREFUSED') return true;  // Connection refused = server not running
  const status = err.status || err.response?.status;
  if ([0, 502, 503, 504].includes(status)) return true;  // Server errors and connection issues
  if (status === 429) return true;  // Rate limit
  const msg = String(err.message || '').toLowerCase();
  return msg.includes('timeout') || msg.includes('network') || msg.includes('failed to fetch');
};

// ── Warm-up Helpers ───────────────────────────────────────────────
let _lastHealthCheck = 0;
let _serverAlive = false;

const warmupBackend = async () => {
  try {
    const res = await api.get('/health', { timeout: 8_000 });
    _serverAlive = res.status === 200;
    _lastHealthCheck = Date.now();
    console.log('[WildTrack] ✓ Backend warmup OK', res.data?.model_loaded ? '(model ready)' : '(model loading)');
  } catch (e) {
    _serverAlive = false;
    console.log('[WildTrack] Warmup failed:', e.message);
  }
};

/**
 * Ensure backend server is alive (responds to requests).
 * Separate from model readiness - just needs HTTP response.
 */
const ensureBackendAlive = async (maxWaitMs = 60_000) => {
  if (_serverAlive && (Date.now() - _lastHealthCheck) < 10_000) {
    return true;
  }
  
  const start = Date.now();
  let attempts = 0;
  
  while (Date.now() - start < maxWaitMs && attempts < 20) {
    try {
      const res = await api.get('/health', { timeout: 8_000 });
      if (res.status === 200) {
        _serverAlive = true;
        console.log('[WildTrack] ✓ Server is alive');
        return true;
      }
    } catch (e) {
      console.log(`[WildTrack] Server starting... (attempt ${attempts + 1}/20)`);
    }
    attempts++;
    await sleep(3_000);
  }
  
  return true;  // Timeout - proceed anyway
};

/**
 * Wait until backend model is loaded (handles slow model initialization).
 */
let _backendReady = false;
let _lastModelCheck = 0;

const ensureModelReady = async (maxWaitMs = 120_000) => {
  if (_backendReady && (Date.now() - _lastModelCheck) < 30_000) {
    return true;
  }
  
  const start = Date.now();
  let attempts = 0;
  
  while (Date.now() - start < maxWaitMs && attempts < 40) {
    try {
      const res = await api.get('/health', { timeout: 8_000 });
      _lastModelCheck = Date.now();
      
      if (res.data?.model_loaded) {
        _backendReady = true;
        console.log('[WildTrack] ✓ Model is ready');
        return true;
      }
      const elapsed = Math.round((Date.now() - start) / 1000);
      console.log(`[WildTrack] Model loading (${elapsed}s, attempt ${attempts + 1}/40)...`);
    } catch (e) {
      // Silent
    }
    attempts++;
    await sleep(3_000);
  }
  
  return true;
};

// ── Generic Retry Wrappers ────────────────────────────────────────
const postWithRetry = async (url, body, options = {}) => {
  const timeoutMs = options.timeoutMs || AUTH_TIMEOUT_MS;
  const maxRetries = Number.isInteger(options.retries) ? options.retries : AUTH_RETRY_COUNT;
  const retryDelayMs = Number.isInteger(options.retryDelayMs) ? options.retryDelayMs : AUTH_RETRY_DELAY_MS;

  // Pre-flight: ensure backend is alive
  await ensureBackendAlive(30_000);

  let attempt = 0;
  while (attempt <= maxRetries) {
    try {
      const result = await api.post(url, body, { timeout: timeoutMs });
      if (attempt > 0) {
        console.log(`[WildTrack] ✓ POST ${url} succeeded on retry ${attempt}`);
      }
      return result;
    } catch (err) {
      if (!isRetryableError(err) || attempt >= maxRetries) {
        console.error(`[WildTrack] POST ${url} failed after ${attempt + 1} attempt(s)`);
        throw err;
      }
      
      attempt += 1;
      const backoffMs = retryDelayMs * Math.pow(1.5, attempt);
      console.warn(`[WildTrack] POST ${url} failed - retry ${attempt}/${maxRetries} in ${backoffMs}ms`);
      
      await warmupBackend();
      await sleep(backoffMs);
    }
  }
};

const getWithRetry = async (url, config = {}, maxRetries = GET_RETRY_COUNT) => {
  let attempt = 0;
  while (true) {
    try {
      return await api.get(url, { timeout: DEFAULT_TIMEOUT_MS, ...config });
    } catch (err) {
      const status = err.status || err.response?.status;
      // Don't retry client errors (4xx) except rate limiting (429)
      if (attempt >= maxRetries || (status && status >= 400 && status < 500 && status !== 429)) {
        throw err;
      }
      attempt += 1;
      console.warn(`[WildTrack] GET ${url} attempt ${attempt}/${maxRetries} failed, retrying...`);
      await sleep(2_000 * attempt);
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
    const status = error.response?.status;
    
    // Smart error logging with context
    if (status === 503) {
      console.warn('[API 503] Service unavailable - model may still be loading');
    } else if (status === 502 || error.code === 'ECONNREFUSED') {
      console.warn('[API] Connection refused - backend may not be running');
    } else if (error.isTimeout || error.code === 'ECONNABORTED') {
      console.warn('[API] Request timeout - backend may be slow');
    } else if (status >= 500) {
      console.error('[API', status + ']', message);
    } else if (status) {
      console.error('[API', status + ']', message);
    } else {
      console.error('[API Network]', error.code || 'Unknown error');
    }
    
    // Auto-logout on 401
    if (status === 401) {
      localStorage.removeItem('wildtrack_token');
      localStorage.removeItem('wildtrack_user');
    }

    const normalizedError = new Error(message);
    normalizedError.status = status;
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
  ensureBackendAlive,
  ensureModelReady,
  warmupBackend,

  // ── Auth ────────────────────────────────────────────────────────
  register: (name, email, password) =>
    postWithRetry('/api/auth/register', { name, email, password }),

  login: (email, password) =>
    postWithRetry('/api/auth/login', { email, password }),

  getMe: () =>
    getWithRetry('/api/auth/me', { params: _tokenParam() }),

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

    // Ensure both server and model are ready
    await ensureBackendAlive(30_000);
    await ensureModelReady(120_000);

    const formData = new FormData();
    formData.append('file', file);
    if (location) {
      if (location.lat) formData.append('latitude', location.lat);
      if (location.lng) formData.append('longitude', location.lng);
    }

    let attempt = 0;
    while (attempt <= maxRetries) {
      try {
        return await api.post('/predict', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: timeoutMs,
        });
      } catch (err) {
        if (!isRetryableError(err) || attempt >= maxRetries) {
          throw err;
        }
        attempt += 1;
        const backoffMs = retryDelayMs * Math.pow(1.5, attempt);
        console.warn(`[WildTrack] Predict attempt ${attempt}/${maxRetries} failed - retry in ${backoffMs}ms`);
        // Invalidate readiness cache
        _backendReady = false;
        await ensureModelReady(60_000);
        await sleep(backoffMs);
      }
    }
  },

  predictBatch: (files) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return api.post('/predict/batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: PREDICT_TIMEOUT_MS,
    });
  },

  getSpecies: () => getWithRetry('/species'),
  getSpeciesDetail: (name) => getWithRetry(`/species/${name}`),

  // Gemini-powered species search
  searchSpecies: (query) => postWithRetry('/species-search', { query }),

  getHistory: (limit = 50, offset = 0, species = null) => {
    const params = { limit, offset };
    if (species) params.species = species;
    return getWithRetry('/history', { params });
  },

  getAnalytics: () => getWithRetry('/analytics'),
  getModelMetrics: () => getWithRetry('/model-metrics'),

  getSystemStatus: () => getWithRetry('/api/system/status'),

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
  listChatSessions: (userId) => getWithRetry('/api/chat/sessions', { params: { user_id: String(userId) } }),
  getChatSession: (sessionId) => getWithRetry(`/api/chat/sessions/${sessionId}`),
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
    getWithRetry('/api/animal-info', { params: { name } }),

  // ── MLOps & Active Learning ─────────────────────────────────────
  getReviewQueue: (limit = 50, offset = 0) =>
    getWithRetry('/mlops/review-queue', { params: { limit, offset } }),

  submitReview: (predId, action, correctedSpecies = null) =>
    postWithRetry(`/mlops/review/${predId}`, {
      action,
      corrected_species: correctedSpecies,
    }),

  getMlopsAnalytics: () => getWithRetry('/mlops/analytics'),
};

export default apiService;
