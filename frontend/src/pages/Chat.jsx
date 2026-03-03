import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiMessageCircle, FiSend, FiImage, FiX, FiUser, FiChevronDown, FiChevronUp, FiZap, FiBookOpen, FiBarChart2, FiHelpCircle, FiLayers, FiActivity, FiPlus, FiTrash2, FiMenu, FiCopy, FiCheck, FiDownload, FiAlertTriangle, FiRefreshCw } from 'react-icons/fi';
import { GiPawPrint } from 'react-icons/gi';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ToastContainer, useToast } from '../components/Toast';
import api from '../services/api';

/* ═══════════════════════════════════════════════════════════════════
   CHAT SESSION MANAGER WITH VALIDATION
   ═══════════════════════════════════════════════════════════════════ */
const STORAGE_KEY_BASE = 'wildtrack_chat_sessions';

// Session schema validation
function validateSession(session) {
  return session?.id &&
    typeof session.id === 'string' &&
    session?.title &&
    typeof session.title === 'string' &&
    Array.isArray(session?.messages) &&
    typeof session?.createdAt === 'number';
}

function validateMessage(msg) {
  return msg?.role &&
    (msg.role === 'user' || msg.role === 'assistant') &&
    msg?.text !== undefined &&
    typeof msg.timestamp === 'number';
}

function getStorageKey(userId) {
  return `${STORAGE_KEY_BASE}_${userId || 'guest'}`;
}

function loadSessions(userId) {
  try {
    const storageKey = getStorageKey(userId);
    const stored = localStorage.getItem(storageKey);
    if (!stored) return [];

    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) {
      console.warn('Invalid sessions data structure, resetting');
      return [];
    }

    // Validate and migrate sessions
    const validated = parsed.filter(session => {
      if (!validateSession(session)) {
        console.warn('Corrupted session removed:', session?.id);
        return false;
      }
      // Migrate messages without timestamps
      session.messages = session.messages.map(msg => ({
        ...msg,
        timestamp: msg.timestamp || Date.now(),
        id: msg.id || `msg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
      }));
      return true;
    });

    if (validated.length !== parsed.length) {
      console.warn(`Removed ${parsed.length - validated.length} corrupted sessions`);
      saveSessions(validated, userId);
    }

    return validated;
  } catch (e) {
    console.error('Failed to load sessions, resetting:', e);
    return [];
  }
}

function saveSessions(sessions, userId) {
  try {
    const storageKey = getStorageKey(userId);
    localStorage.setItem(storageKey, JSON.stringify(sessions));
  } catch (e) {
    console.error('Failed to save sessions:', e);
    // Could show toast here
  }
}

function generateSessionId() {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function generateMessageId() {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
}

function generateTitle(firstUserMessage) {
  if (!firstUserMessage) return 'New Chat';
  const cleaned = firstUserMessage.replace(/\[Uploaded:.*\]/, '').trim();
  const words = cleaned.split(' ').slice(0, 5).join(' ');
  return words.length > 30 ? words.slice(0, 30) + '...' : (words || 'New Chat');
}

function defaultWelcomeSession() {
  return {
    id: generateSessionId(),
    title: 'Welcome',
    createdAt: Date.now(),
    messages: [{
      id: generateMessageId(),
      role: 'assistant',
      text: "### Welcome to WildTrackAI\n\nUpload a footprint image or ask a tracking question to begin.",
      showActions: true,
      timestamp: Date.now(),
    }]
  };
}

function mapDbMessageToUi(message) {
  return {
    id: message.id,
    role: message.role,
    text: message.content,
    timestamp: new Date(message.created_at).getTime(),
    showActions: message.role === 'assistant',
  };
}

function mapDbSessionToUi(session) {
  return {
    id: session.id,
    title: session.title || 'New Chat',
    createdAt: new Date(session.created_at).getTime(),
    messages: (session.messages || []).map(mapDbMessageToUi),
  };
}

// Export session as JSON
function exportSessionAsJSON(session) {
  const data = {
    title: session.title,
    createdAt: new Date(session.createdAt).toISOString(),
    messages: session.messages.map(m => ({
      role: m.role,
      text: m.text,
      timestamp: new Date(m.timestamp).toISOString(),
      ...(m.prediction && { prediction: m.prediction })
    }))
  };
  return JSON.stringify(data, null, 2);
}

// Export session as Markdown
function exportSessionAsMarkdown(session) {
  let md = `# ${session.title}\n\n`;
  md += `**Created:** ${new Date(session.createdAt).toLocaleString()}\n\n`;
  md += `---\n\n`;

  session.messages.forEach(msg => {
    const time = new Date(msg.timestamp).toLocaleTimeString();
    md += `### ${msg.role === 'user' ? 'User' : 'Assistant'} (${time})\n\n`;
    md += `${msg.text}\n\n`;
    if (msg.prediction) {
      md += `**Prediction:** ${msg.prediction.predicted_class} (${(msg.prediction.confidence * 100).toFixed(1)}%)\n\n`;
    }
    md += `---\n\n`;
  });

  return md;
}

/* ─── Typewriter Hook ────────────────────────────────────────────── */
function useTypewriter(text, speed = 20, enabled = true) {
  const [displayed, setDisplayed] = useState(enabled ? '' : text);
  const [done, setDone] = useState(!enabled);
  useEffect(() => {
    if (!enabled) { setDisplayed(text); setDone(true); return; }
    setDisplayed(''); setDone(false);
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      if (i >= text.length) { setDisplayed(text); setDone(true); clearInterval(id); }
      else setDisplayed(text.slice(0, i));
    }, speed);
    return () => clearInterval(id);
  }, [text, speed, enabled]);
  return { displayed, done };
}

/* ─── Calm Thinking Indicator ─────────────────────────────────────── */
function WaveformThinking({ dark }) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-orange-500/80 to-amber-500/80 flex items-center justify-center shrink-0">
        <GiPawPrint className="text-white text-sm" />
      </div>
      <div className="px-5 py-3 rounded-2xl rounded-tl-md backdrop-blur" style={{ background: 'var(--bg-surface-2)' }}>
        <span className="text-sm font-medium t-secondary">Analyzing track...</span>
      </div>
    </div>
  );
}

/* ─── Code Block with Copy Button ─────────────────────────────────── */
function CodeBlock({ code, language, dark }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-3">
      <div className={`absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity z-10`}>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-all surface-inset t-secondary"
        >
          {copied ? <><FiCheck size={12} /> Copied!</> : <><FiCopy size={12} /> Copy</>}
        </motion.button>
      </div>
      <SyntaxHighlighter
        language={language || 'javascript'}
        style={dark ? vscDarkPlus : vs}
        customStyle={{
          margin: 0,
          borderRadius: '0.75rem',
          fontSize: '0.813rem',
          padding: '1rem',
        }}
        showLineNumbers
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

/* ─── Rich Markdown Renderer with Code Blocks ─────────────────────── */
function RichText({ text }) {
  const { dark } = useTheme();
  const rendered = useMemo(() => {
    if (!text) return null;
    const lines = text.split('\n');
    const elements = [];
    let inTable = false;
    let inCodeBlock = false;
    let codeLines = [];
    let codeLanguage = '';
    let tableRows = [];

    const flushTable = () => {
      if (tableRows.length === 0) return;
      elements.push(
        <div key={`tbl-${elements.length}`} className="overflow-x-auto my-2">
          <table className="text-xs w-full border-collapse t-secondary">
            <thead>
              <tr>{tableRows[0].map((h, i) => (
                <th key={i} className="px-2 py-1 text-left font-semibold border-b b-primary">{inlineMd(h.trim())}</th>
              ))}</tr>
            </thead>
            <tbody>
              {tableRows.slice(2).map((row, ri) => (
                <tr key={ri}>{row.map((c, ci) => (
                  <td key={ci} className="px-2 py-1 border-b b-subtle">{inlineMd(c.trim())}</td>
                ))}</tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
    };

    const flushCodeBlock = () => {
      if (codeLines.length === 0) return;
      elements.push(
        <CodeBlock
          key={`code-${elements.length}`}
          code={codeLines.join('\n')}
          language={codeLanguage}
          dark={dark}
        />
      );
      codeLines = [];
      codeLanguage = '';
    };

    lines.forEach((line, idx) => {
      // Handle code blocks
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          flushCodeBlock();
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
          codeLanguage = line.trim().slice(3).trim();
        }
        return;
      }

      if (inCodeBlock) {
        codeLines.push(line);
        return;
      }

      // Handle tables
      if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
        const cells = line.split('|').filter(Boolean);
        tableRows.push(cells);
        inTable = true;
        return;
      } else if (inTable) { flushTable(); inTable = false; }

      if (line.startsWith('### ')) elements.push(<h3 key={idx} className="font-bold text-sm mt-3 mb-1">{inlineMd(line.slice(4))}</h3>);
      else if (line.startsWith('## ')) elements.push(<h2 key={idx} className="font-bold text-base mt-3 mb-1">{inlineMd(line.slice(3))}</h2>);
      else if (/^[•\-*] /.test(line)) elements.push(<div key={idx} className="pl-3 flex gap-1.5 items-start text-[13px] leading-relaxed"><span className="text-orange-500 mt-0.5">•</span><span>{inlineMd(line.slice(2))}</span></div>);
      else if (/^\d+\.\s/.test(line)) {
        const n = line.match(/^(\d+)\./)[1];
        elements.push(<div key={idx} className="pl-3 flex gap-1.5 items-start text-[13px] leading-relaxed"><span className="text-orange-500 font-bold mt-0.5">{n}.</span><span>{inlineMd(line.replace(/^\d+\.\s/, ''))}</span></div>);
      }
      else if (line.startsWith('---')) elements.push(<hr key={idx} className="my-2 b-primary" />);
      else if (line.trim() === '') elements.push(<div key={idx} className="h-1.5" />);
      else elements.push(<p key={idx} className={`text-[13px] leading-relaxed ${line.startsWith('  ') ? 'pl-6' : ''}`}>{inlineMd(line)}</p>);
    });
    if (inTable) flushTable();
    if (inCodeBlock) flushCodeBlock();
    return elements;
  }, [text, dark]);
  return <div className="space-y-0.5">{rendered}</div>;
}

function inlineMd(text) {
  return text.split(/(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)/).map((p, j) => {
    if (p.startsWith('**') && p.endsWith('**')) return <strong key={j} className="font-semibold">{p.slice(2, -2)}</strong>;
    if (p.startsWith('_') && p.endsWith('_')) return <em key={j} className="italic opacity-80">{p.slice(1, -1)}</em>;
    if (p.startsWith('`') && p.endsWith('`')) return <code key={j} className="px-1 py-0.5 rounded bg-black/10 dark:bg-white/10 text-xs font-mono">{p.slice(1, -1)}</code>;
    return <span key={j}>{p}</span>;
  });
}

/* ─── Message Content Renderer ───────────────────────────────────── */
function TypewriterText({ text, researchMode, msgIdx, expandedSections, toggleSection, dark, isNew }) {
  // Streaming already delivers tokens incrementally — no extra typewriter needed.
  // Only render markdown once the text is stable (no double-animation).
  return (
    <div>
      {researchMode
        ? <RichText text={text} />
        : <SimpleOrExpandable text={text} msgIdx={msgIdx} expandedSections={expandedSections} toggleSection={toggleSection} dark={dark} />}
    </div>
  );
}

/* ─── Confidence Bar ─────────────────────────────────────────────── */
function ConfidenceBar({ species, confidence, delta, isTop, dark }) {
  const pct = (confidence * 100).toFixed(1);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`w-16 capitalize truncate font-medium ${isTop ? 'text-orange-500' : 't-secondary'}`}>{species}</span>
      <div className="flex-1 h-2.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-2)' }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 1, ease: [0.25, 0.46, 0.45, 0.94] }}
          className={`h-full rounded-full ${isTop ? 'bg-gradient-to-r from-orange-500 to-amber-400 animate-gradient' : ''}`}
          style={isTop ? {} : { background: 'var(--text-dim)' }} />
      </div>
      <span className={`w-12 text-right font-mono ${isTop ? 'font-bold text-orange-500' : 't-tertiary'}`}>{pct}%</span>
      {delta > 0 && <span className="text-[10px] font-mono t-dim">-{(delta * 100).toFixed(1)}</span>}
    </div>
  );
}

/* ─── Entropy Gauge (Research Mode) ──────────────────────────────── */
function EntropyGauge({ entropy, entropyRatio, maxEntropy, temperature, dark }) {
  const pct = (entropyRatio * 100).toFixed(0);
  const level = entropyRatio > 0.85 ? 'High' : entropyRatio > 0.5 ? 'Moderate' : 'Low';
  const color = entropyRatio > 0.85 ? 'text-red-500' : entropyRatio > 0.5 ? 'text-yellow-500' : 'text-green-500';
  return (
    <div className="mt-2 pt-2 border-t text-[11px] space-y-1 b-primary">
      <div className="flex justify-between">
        <span className="text-gray-500 uppercase tracking-wider font-semibold">Uncertainty</span>
        <span className={`font-bold ${color}`}>{level} ({pct}%)</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-2)' }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8 }}
          className={`h-full rounded-full ${entropyRatio > 0.85 ? 'bg-red-500' : entropyRatio > 0.5 ? 'bg-yellow-500' : 'bg-green-500'}`} />
      </div>
      <div className="flex gap-3 text-gray-500">
        <span>H={entropy.toFixed(2)} bits</span>
        <span>H_max={maxEntropy.toFixed(2)}</span>
        <span>T={temperature}</span>
      </div>
    </div>
  );
}

/* ─── Action Buttons ─────────────────────────────────────────────── */
function ActionButtons({ onAction, dark, lastPrediction }) {
  const buttons = lastPrediction
    ? [
      { label: 'Why not other?', icon: <FiHelpCircle size={13} />, msg: `Why not ${lastPrediction.top3?.[1]?.class || 'leopard'}?` },
      { label: 'More details', icon: <FiBookOpen size={13} />, msg: 'Tell me more about this species' },
      { label: 'How confident?', icon: <FiBarChart2 size={13} />, msg: 'How confident is this prediction?' },
      { label: 'Compare', icon: <FiLayers size={13} />, nav: '/compare' },
    ]
    : [
      { label: 'About tigers', icon: <GiPawPrint size={13} />, msg: 'Tell me about tigers' },
      { label: 'Model info', icon: <FiZap size={13} />, msg: 'What model do you use?' },
      { label: 'Grad-CAM explained', icon: <FiBarChart2 size={13} />, msg: 'Explain Grad-CAM heatmaps' },
      { label: 'Conservation', icon: <FiBookOpen size={13} />, msg: 'Tell me about wildlife conservation' },
    ];

  return (
    <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="flex flex-wrap gap-1.5 mt-2">
      {buttons.map((b, i) => (
        <motion.button key={i} whileHover={{ scale: 1.02, y: -1 }} whileTap={{ scale: 0.98 }}
          onClick={() => b.nav ? onAction(null, b.nav) : onAction(b.msg)}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all t-secondary hover:text-orange-500 hover:shadow-sm"
          style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-subtle)' }}
        >{b.icon} {b.label}</motion.button>
      ))}
    </motion.div>
  );
}

/* ─── Simple-mode collapsible sections ───────────────────────────── */
function SimpleOrExpandable({ text, msgIdx, expandedSections, toggleSection, dark }) {
  const lines = text.split('\n');
  const sections = [];
  let cur = { title: null, content: [] };
  lines.forEach(l => {
    if (l.startsWith('### ')) {
      if (cur.title || cur.content.length) sections.push({ ...cur });
      cur = { title: l.slice(4), content: [] };
    } else cur.content.push(l);
  });
  if (cur.title || cur.content.length) sections.push(cur);
  if (sections.length <= 1 || lines.length < 8) return <RichText text={text} />;

  return (
    <div className="space-y-1">
      {sections.map((sec, si) => {
        const key = `${msgIdx}-${si}`;
        const isOpen = si === 0 || expandedSections[key];
        if (!sec.title) return <RichText key={si} text={sec.content.join('\n')} />;
        return (
          <div key={si}>
            <button onClick={(e) => { e.stopPropagation(); toggleSection(msgIdx, si); }}
              className={`flex items-center gap-1.5 w-full text-left py-1 text-sm font-bold transition ${si === 0 ? '' : 't-secondary hover:text-orange-500'}`}>
              {si > 0 && (isOpen ? <FiChevronUp size={12} /> : <FiChevronDown size={12} />)}
              {inlineMd(sec.title)}
            </button>
            <AnimatePresence>
              {isOpen && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
                  <RichText text={sec.content.join('\n')} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN CHAT PAGE WITH SESSIONS
   ═══════════════════════════════════════════════════════════════════ */
export default function ChatPage() {
  const { dark } = useTheme();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toasts, addToast, removeToast } = useToast();

  const [sessions, setSessions] = useState(() => {
    const loaded = loadSessions(user?.id);
    return loaded.length > 0 ? loaded : [defaultWelcomeSession()];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => sessions[0]?.id);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Chat state
  const [input, setInput] = useState('');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [abortController, setAbortController] = useState(null);
  const [researchMode, setResearchMode] = useState(false);
  const [lastPrediction, setLastPrediction] = useState(null);
  const [expandedSections, setExpandedSections] = useState({});
  const [newestMsgId, setNewestMsgId] = useState(null);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Get current session
  const currentSession = sessions.find(s => s.id === activeSessionId) || sessions[0];
  const messages = currentSession?.messages || [];

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [messages]);

  // Save sessions to localStorage whenever they change (fallback cache)
  useEffect(() => {
    saveSessions(sessions, user?.id);
  }, [sessions, user?.id]);

  // Backend is canonical source of truth; localStorage is fallback cache
  useEffect(() => {
    const loadFromBackend = async () => {
      if (!user?.id) return;

      try {
        const listRes = await api.listChatSessions(user.id);
        const summaries = listRes.data || [];

        if (summaries.length === 0) {
          const cached = loadSessions(user.id);
          if (cached.length > 0) {
            setSessions(cached);
            setActiveSessionId(cached[0]?.id);
          } else {
            const welcome = defaultWelcomeSession();
            setSessions([welcome]);
            setActiveSessionId(welcome.id);
          }
          return;
        }

        const detailResponses = await Promise.all(
          summaries.map((summary) => api.getChatSession(summary.id))
        );

        const mapped = detailResponses
          .map((res) => mapDbSessionToUi(res.data))
          .sort((a, b) => b.createdAt - a.createdAt);

        setSessions(mapped);
        setActiveSessionId((prev) => (mapped.some((s) => s.id === prev) ? prev : mapped[0]?.id));
      } catch (error) {
        const cached = loadSessions(user?.id);
        if (cached.length > 0) {
          setSessions(cached);
          setActiveSessionId(cached[0]?.id);
        }
      }
    };

    loadFromBackend();
  }, [user?.id]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl+K or Cmd+K: New chat
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        createNewSession();
      }
      // Ctrl+Shift+Backspace: Clear all chats
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'Backspace') {
        e.preventDefault();
        handleClearAllSessions();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const createNewSession = async () => {
    const newSession = {
      id: generateSessionId(),
      title: 'New Chat',
      createdAt: Date.now(),
      messages: [],
    };

    try {
      if (user?.id) {
        await api.createChatSession({
          id: newSession.id,
          user_id: String(user.id),
          title: newSession.title,
        });
      }
      setSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setLastPrediction(null);
      setSidebarOpen(false);
      addToast('New chat created', 'success', 2000);
    } catch (error) {
      addToast('Failed to create session', 'error', 2500);
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      await api.deleteChatSession(sessionId);
    } catch (error) {
      // Continue local cleanup to keep UI responsive
    }

    setSessions(prev => {
      const updated = prev.filter(s => s.id !== sessionId);
      if (updated.length === 0) return [defaultWelcomeSession()];
      return updated;
    });

    if (activeSessionId === sessionId) {
      const remaining = sessions.filter(s => s.id !== sessionId);
      setActiveSessionId(remaining[0]?.id || null);
    }

    addToast('Session deleted', 'info', 2000);
  };

  const handleClearAllSessions = async () => {
    if (!confirm('Clear all chat sessions? This cannot be undone.')) return;

    await Promise.all(
      sessions
        .filter((session) => session.id)
        .map((session) => api.deleteChatSession(session.id).catch(() => null))
    );

    const welcome = defaultWelcomeSession();
    setSessions([welcome]);
    setActiveSessionId(welcome.id);
    saveSessions([welcome], user?.id);
    addToast('All sessions cleared', 'success', 2000);
  };

  const switchSession = async (sessionId) => {
    setActiveSessionId(sessionId);
    setSidebarOpen(false);
    setLastPrediction(null);

    try {
      const res = await api.getChatSession(sessionId);
      const mapped = mapDbSessionToUi(res.data);
      setSessions(prev => prev.map(s => (s.id === sessionId ? mapped : s)));
    } catch (error) {
      // Fallback: keep currently cached session state
    }
  };

  const handleExportJSON = () => {
    const json = exportSessionAsJSON(currentSession);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentSession.title.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    addToast('Exported as JSON', 'success', 2000);
  };

  const handleExportMarkdown = () => {
    const md = exportSessionAsMarkdown(currentSession);
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentSession.title.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    addToast('Exported as Markdown', 'success', 2000);
  };

  const copyMessageText = (text) => {
    navigator.clipboard.writeText(text);
    addToast('Message copied!', 'success', 1500);
  };

  const updateSessionMessages = useCallback((updater) => {
    setSessions(prev => prev.map(s => {
      if (s.id === activeSessionId) {
        // Resolve new messages array whether it's a function or value
        const newMessages = typeof updater === 'function' ? updater(s.messages || []) : updater;

        // Auto-generate title from first user message
        let title = s.title;
        if (s.title === 'New Chat' && newMessages.length >= 2) {
          const firstUserMsg = newMessages.find(m => m.role === 'user');
          if (firstUserMsg) {
            title = generateTitle(firstUserMsg.text);
          }
        }
        return { ...s, messages: newMessages, title };
      }
      return s;
    }));
  }, [activeSessionId]);

  const handleFile = useCallback((f) => {
    if (!f) return;
    setFile(f);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }, []);

  const removeFile = () => { setFile(null); setPreview(null); };

  const toggleSection = (mi, si) => setExpandedSections(p => ({ ...p, [`${mi}-${si}`]: !p[`${mi}-${si}`] }));

  const retryMessage = async (messageData) => {
    setLoading(true);
    try {
      const [res] = await Promise.all([
        api.chat(messageData.message, messageData.file, activeSessionId),
        new Promise(r => setTimeout(r, 1200)),
      ]);
      const data = res.data;
      if (data.prediction) setLastPrediction(data.prediction);

      const newAssistantMessage = {
        id: generateMessageId(),
        role: 'assistant',
        text: data.response || 'I could not process that request.',
        heatmap: data.prediction?.heatmap || null,
        prediction: data.prediction || null,
        showActions: true,
        timestamp: Date.now(),
      };

      // Remove failed message and add new one
      const updatedMessages = messages.filter(m => !m.failed);
      updateSessionMessages([...updatedMessages, newAssistantMessage]);
      setNewestMsgId(newAssistantMessage.id);
      addToast('Message resent successfully', 'success', 2000);
    } catch (err) {
      addToast('Retry failed: ' + (err.message || 'Unknown error'), 'error', 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleAbort = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
      setStreaming(false);
      setLoading(false);
      addToast('Response stopped', 'info', 2000);
    }
  };

  const handleSend = async (overrideMsg = null, navTo = null) => {
    if (navTo) { navigate(navTo); return; }
    if (loading || streaming) return;

    const trimmed = (overrideMsg || input).trim();
    if (!trimmed && !file) return;

    const newUserMessage = {
      id: generateMessageId(),
      role: 'user',
      text: trimmed || (file ? `[Uploaded: ${file.name}]` : ''),
      image: preview || null,
      timestamp: Date.now(),
    };

    updateSessionMessages(prevMsgs => [...prevMsgs, newUserMessage]);
    setInput('');
    const currentFile = file;
    setFile(null); setPreview(null); setLoading(true);

    // Create assistant message placeholder for streaming
    const assistantMsgId = generateMessageId();
    const assistantPlaceholder = {
      id: assistantMsgId,
      role: 'assistant',
      text: '',
      heatmap: null,
      prediction: null,
      showActions: true,
      timestamp: Date.now(),
    };

    updateSessionMessages(prevMsgs => [...prevMsgs, assistantPlaceholder]);
    setNewestMsgId(assistantMsgId);  // track newest for animation

    // Initialize abort controller
    const controller = new AbortController();
    setAbortController(controller);
    setStreaming(true);

    try {
      // If user uploaded an image, run prediction first
      let predictionContext = lastPrediction || null;
      if (currentFile) {
        try {
          const predRes = await api.predict(currentFile);
          const pred = predRes.data;
          predictionContext = {
            predicted_class: pred.species,
            confidence: pred.confidence,
            top3: pred.top3 || [],
            is_unknown: pred.is_unknown || false,
            heatmap: pred.heatmap || null,
          };
          setLastPrediction(predictionContext);

          // Update assistant placeholder to show heatmap once available
          updateSessionMessages(prevMsgs =>
            prevMsgs.map(msg =>
              msg.id === assistantMsgId
                ? {
                  ...msg,
                  text: `Analyzing image... Detected **${pred.species}** (${(pred.confidence * 100).toFixed(1)}% confidence)\n\n`,
                  heatmap: pred.heatmap || null,
                  prediction: { top3: pred.top3 || [] }
                }
                : msg
            )
          );
        } catch (predErr) {
          console.warn('Image prediction failed, continuing with text-only:', predErr);
        }
      }

      // Start streaming
      const response = await api.streamChat({
        message: trimmed || 'Analyze this footprint',
        session_id: activeSessionId,
        context: {
          elevation: predictionContext?.elevation || 0,
          habitat: predictionContext?.habitat || 'unknown',
          prediction: predictionContext
        }
      }, controller.signal);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';
      const startTime = Date.now();
      let tokenCount = 0;
      let receivedComplete = false;
      let pendingUpdate = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim()) continue;

          try {
            const event = JSON.parse(line);

            if (event.type === 'token') {
              accumulatedText += event.content;
              tokenCount++;

              // Batch UI updates — render every 3 tokens to reduce re-renders
              if (!pendingUpdate) {
                pendingUpdate = true;
                requestAnimationFrame(() => {
                  pendingUpdate = false;
                  updateSessionMessages(prevMsgs =>
                    prevMsgs.map(msg =>
                      msg.id === assistantMsgId
                        ? {
                          ...msg,
                          text: accumulatedText,
                          heatmap: predictionContext?.heatmap || msg.heatmap,
                          prediction: predictionContext?.top3 ? { top3: predictionContext.top3 } : msg.prediction
                        }
                        : msg
                    )
                  );
                });
              }
            } else if (event.type === 'complete') {
              receivedComplete = true;

              // Stream complete - call deferred persistence
              const duration = Date.now() - startTime;

              try {
                await api.saveStreamedChat({
                  session_id: activeSessionId,
                  user_id: String(user?.id || 'guest'),
                  user_message: trimmed || 'Analyze this footprint',
                  assistant_response: accumulatedText,
                  token_count: tokenCount,
                  duration_ms: duration
                });
              } catch (saveErr) {
                console.warn('Failed to save chat session:', saveErr);
                // Non-critical - don't show error to user
              }

              addToast('Response complete', 'success', 1500);
            } else if (event.type === 'error') {
              throw new Error(event.message || 'Stream error');
            }
          } catch (parseErr) {
            console.error('Failed to parse NDJSON line:', line, parseErr);
          }
        }
      }

      // Detect incomplete stream (connection dropped without complete event)
      if (!receivedComplete) {
        console.warn('Stream ended without complete event - connection may have dropped');
        updateSessionMessages(prevMsgs =>
          prevMsgs.map(msg =>
            msg.id === assistantMsgId
              ? { ...msg, text: accumulatedText + '\n\n_[Connection interrupted - response incomplete]_', failed: true }
              : msg
          )
        );
        addToast('Stream interrupted', 'warning', 3000);
      } else {
        // Normal completion - ensure final text is saved with heatmap/prediction
        updateSessionMessages(prevMsgs =>
          prevMsgs.map(msg =>
            msg.id === assistantMsgId
              ? {
                ...msg,
                text: accumulatedText || 'No response generated.',
                heatmap: predictionContext?.heatmap || msg.heatmap,
                prediction: predictionContext?.top3 ? { top3: predictionContext.top3 } : msg.prediction
              }
              : msg
          )
        );
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        updateSessionMessages(prevMsgs =>
          prevMsgs.map(msg =>
            msg.id === assistantMsgId
              ? { ...msg, text: msg.text + '\n\n_[Response stopped by user]_' }
              : msg
          )
        );
      } else {
        console.error('Streaming error:', err);

        const errorMessage = {
          id: generateMessageId(),
          role: 'assistant',
          text: `### Connection Error\n\n${err.message || 'Failed to reach AI. Check your connection.'}\n\nThe server might be down or unreachable.`,
          failed: true,
          retryData: { message: trimmed, file: currentFile },
          timestamp: Date.now(),
        };
        // Remove the empty placeholder and insert error message
        updateSessionMessages(prevMsgs => {
          const filtered = prevMsgs.filter(m => m.id !== assistantMsgId);
          return [...filtered, errorMessage];
        });
        addToast('Failed to send message', 'error', 3000);
      }
    } finally {
      setLoading(false);
      setStreaming(false);
      setAbortController(null);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const cardClass = 'surface-card-lg backdrop-blur-xl';

  return (
    <>
      <ToastContainer toasts={toasts} removeToast={removeToast} />
      <div className="flex h-[calc(100vh-4rem)] max-w-7xl mx-auto gap-4">
        {/* Session Sidebar */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ x: -280, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -280, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className={`fixed lg:relative z-50 w-64 h-full ${cardClass} p-4 flex flex-col`}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold t-tertiary uppercase tracking-wider">Chat History</h2>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="lg:hidden p-1 rounded-lg surface-hover t-secondary"
                >
                  <FiX size={18} />
                </button>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={createNewSession}
                className="flex items-center gap-2 w-full px-4 py-3 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold text-sm mb-3 hover:shadow-md transition-all"
              >
                <FiPlus size={18} />
                New Chat
              </motion.button>

              {/* Export and Clear All Buttons */}
              <div className="flex gap-2 mb-4">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleExportJSON}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all surface-inset t-secondary"
                  title="Export as JSON"
                >
                  <FiDownload size={13} />
                  JSON
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleExportMarkdown}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all surface-inset t-secondary"
                  title="Export as Markdown"
                >
                  <FiDownload size={13} />
                  MD
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleClearAllSessions}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20"
                  title="Clear all sessions"
                >
                  <FiAlertTriangle size={13} />
                  Clear
                </motion.button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2">
                {sessions.map(session => (
                  <motion.div
                    key={session.id}
                    whileHover={{ scale: 1.02 }}
                    className={`group relative p-3 rounded-xl cursor-pointer transition-all ${session.id === activeSessionId
                        ? 'bg-orange-500/15 border border-orange-500/30'
                        : 'surface-inset surface-hover'
                      }`}
                    onClick={() => switchSession(session.id)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className={`text-sm font-semibold truncate ${session.id === activeSessionId ? 'text-orange-500' : 't-primary'
                          }`}>
                          {session.title}
                        </div>
                        <div className="text-xs t-dim mt-1">
                          {session.messages.length} messages
                        </div>
                      </div>
                      {sessions.length > 1 && (
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/20 text-red-400 transition-all"
                        >
                          <FiTrash2 size={14} />
                        </button>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main Chat Area */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2.5 rounded-xl transition-all t-secondary surface-hover"
              >
                <FiMenu size={20} />
              </button>
              <motion.div whileHover={{ rotate: 10 }} className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-md">
                <FiMessageCircle className="text-white text-lg" />
              </motion.div>
              <div>
                <h1 className="text-2xl font-bold t-primary">{currentSession?.title || 'AI Chat'}</h1>
                <p className="text-sm t-tertiary">Wildlife Intelligence • Session Management</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setResearchMode(r => !r)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${researchMode
                  ? 'bg-orange-500/15 text-orange-500 ring-1 ring-orange-500/30'
                  : 't-secondary'}`}
                style={researchMode ? {} : { background: 'var(--bg-surface-2)' }}>
                {researchMode ? <><FiBookOpen size={14} /> Research</> : <><FiZap size={14} /> Simple</>}
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className={`${cardClass} flex-1 overflow-y-auto p-5 space-y-4 mb-4`}>
            {messages.map((msg) => (
              <motion.div key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                layout={false}
                className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>

                {/* Avatar */}
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${msg.role === 'user'
                  ? 'bg-blue-500 shadow-sm'
                  : 'bg-gradient-to-br from-orange-500 to-amber-500 shadow-sm'}`}>
                  {msg.role === 'user' ? <FiUser className="text-white text-sm" /> : <GiPawPrint className="text-white text-sm" />}
                </div>

                {/* Bubble */}
                <div className={`max-w-[80%] ${msg.role === 'user' ? 'text-right' : ''}`}>
                  {/* Timestamp & Copy Button */}
                  <div className={`flex items-center gap-2 mb-1 text-[10px] ${msg.role === 'user' ? 'justify-end' : 'justify-start'} t-dim`}>
                    {msg.timestamp && (
                      <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    )}
                    {msg.role === 'assistant' && !msg.failed && (
                      <button
                        onClick={() => copyMessageText(msg.text)}
                        className="p-1 rounded transition surface-hover"
                        title="Copy message">
                        <FiCopy size={11} />
                      </button>
                    )}
                  </div>

                  <div
                    className={`inline-block px-4 py-3 rounded-2xl text-sm leading-relaxed ${msg.role === 'user'
                      ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-tr-md shadow-sm'
                      : msg.failed
                        ? 'bg-red-500/10 backdrop-blur text-red-500 border border-red-500/20 rounded-tl-md'
                        : 'backdrop-blur t-primary rounded-tl-md'}`}
                    style={msg.role !== 'user' && !msg.failed ? { background: 'var(--bg-surface-2)' } : undefined}>

                    {msg.image && (
                      <motion.img initial={{ opacity: 0, filter: 'blur(8px)' }} animate={{ opacity: 1, filter: 'blur(0px)' }} transition={{ duration: 0.5 }}
                        src={msg.image} alt="uploaded" className="rounded-xl max-h-48 mb-2 w-auto" />
                    )}

                    {msg.role === 'assistant'
                      ? <TypewriterText text={msg.text} researchMode={researchMode} msgIdx={msg.id}
                        expandedSections={expandedSections} toggleSection={toggleSection} dark={dark} isNew={msg.id === newestMsgId} />
                      : <div className="whitespace-pre-wrap">{msg.text}</div>}

                    {/* Confidence bars */}
                    {msg.prediction?.top3 && (
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
                        className={`mt-3 pt-3 space-y-1.5 border-t b-primary`}>
                        <div className="text-[11px] uppercase tracking-wider font-semibold text-gray-500 mb-1">Confidence Distribution</div>
                        {msg.prediction.top3.map((t, j) => (
                          <ConfidenceBar key={t.class} species={t.class} confidence={t.confidence} delta={t.delta || 0} isTop={j === 0} dark={dark} />
                        ))}
                      </motion.div>
                    )}

                    {/* Entropy display in research mode */}
                    {researchMode && msg.prediction?.entropy !== undefined && (
                      <EntropyGauge entropy={msg.prediction.entropy} entropyRatio={msg.prediction.entropy_ratio || 0}
                        maxEntropy={msg.prediction.max_entropy || 0} temperature={msg.prediction.temperature || 1} dark={dark} />
                    )}

                    {/* Heatmap */}
                    {msg.heatmap && (
                      <motion.div initial={{ opacity: 0, filter: 'blur(8px)' }} animate={{ opacity: 1, filter: 'blur(0px)' }} transition={{ duration: 0.6, delay: 0.3 }} className="mt-3">
                        <div className="text-xs mb-1 font-medium t-tertiary">Grad-CAM Heatmap:</div>
                        <img src={`data:image/png;base64,${msg.heatmap}`} alt="heatmap" className="rounded-xl max-h-48 w-auto" />
                      </motion.div>
                    )}
                  </div>

                  {/* Retry Button for Failed Messages */}
                  {msg.failed && msg.retryData && (
                    <motion.button
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => retryMessage(msg.retryData)}
                      disabled={loading}
                      className={`mt-2 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}>
                      <FiRefreshCw size={12} />
                      Retry Message
                    </motion.button>
                  )}

                  {msg.role === 'assistant' && msg.showActions && !loading && !msg.failed && (
                    <ActionButtons onAction={handleSend} dark={dark} lastPrediction={lastPrediction} />
                  )}
                </div>
              </motion.div>
            ))}

            {loading && <WaveformThinking dark={dark} />}
            <div ref={messagesEndRef} />
          </div>

          {/* File preview */}
          {preview && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`${cardClass} p-3 mb-3 flex items-center gap-3`}>
              <motion.img initial={{ filter: 'blur(4px)' }} animate={{ filter: 'blur(0px)' }}
                src={preview} alt="preview" className="w-16 h-16 rounded-xl object-cover" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold truncate">{file?.name}</div>
                <div className="text-xs t-tertiary">{(file?.size / 1024).toFixed(0)} KB</div>
              </div>
              <button onClick={removeFile} className="p-2 rounded-xl transition surface-hover"><FiX size={16} /></button>
            </motion.div>
          )}

          {/* Input */}
          <div className={`${cardClass} p-3 flex items-end gap-3`}>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={() => fileInputRef.current?.click()}
              className="p-3 rounded-xl transition shrink-0 t-secondary surface-hover">
              <FiImage size={20} />
            </motion.button>
            <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = ''; }} />

            <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
              placeholder={researchMode ? 'Research mode — ask detailed technical questions...' : 'Ask about footprints or upload an image...'}
              rows={1}
              disabled={loading || streaming}
              className="flex-1 resize-none py-3 px-4 rounded-xl border outline-none text-sm input-chat focus:ring-2 focus:ring-orange-500/20 transition disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ maxHeight: '120px' }}
              onInput={(e) => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'; }} />

            {streaming ? (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleAbort}
                className="p-3 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-all shadow-md hover:shadow-lg shrink-0"
                title="Stop generation"
              >
                <FiX size={18} />
              </motion.button>
            ) : (
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={() => handleSend()} disabled={loading || (!input.trim() && !file)}
                className="p-3 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-white transition-all shadow-md hover:shadow-lg disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none shrink-0">
                <FiSend size={18} />
              </motion.button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
