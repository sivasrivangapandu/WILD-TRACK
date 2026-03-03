import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FiClock, FiFilter, FiChevronLeft, FiChevronRight, FiTrendingUp, FiBarChart2 } from 'react-icons/fi';
import { GiPawPrint } from 'react-icons/gi';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

/* ═══ Confidence Badge ═══ */
function ConfidenceBadge({ value }) {
  const getColor = (conf) => {
    if (conf >= 0.8) return { bg: 'bg-green-500/20 border border-green-500/30', text: 'text-green-500' };
    if (conf >= 0.5) return { bg: 'bg-yellow-500/20 border border-yellow-500/30', text: 'text-yellow-500' };
    return { bg: 'bg-red-500/20 border border-red-500/30', text: 'text-red-500' };
  };
  const color = getColor(value);
  return (
    <div className={`px-2.5 py-1 rounded-lg text-xs font-bold font-mono ${color.bg} ${color.text}`}>
      {(value * 100).toFixed(1)}%
    </div>
  );
}

export default function HistoryPage() {
  const { dark } = useTheme();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(0);
  const [stats, setStats] = useState(null);
  const PAGE_SIZE = 20;

  useEffect(() => { loadHistory(); }, [page, filter]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const res = await api.getHistory(PAGE_SIZE, page * PAGE_SIZE, filter || null);
      setHistory(res.data?.predictions || []);
      
      // Calculate statistics
      if (res.data?.predictions && res.data.predictions.length > 0) {
        const predictions = res.data.predictions;
        const avgConfidence = predictions.reduce((sum, p) => sum + (p.confidence || 0), 0) / predictions.length;
        const highConfidence = predictions.filter(p => (p.confidence || 0) >= 0.8).length;
        const speciesCount = new Set(predictions.map(p => p.species || p.predicted_species)).size;
        
        setStats({
          total: predictions.length,
          avgConfidence,
          highConfidence,
          speciesCount,
        });
      }
    } catch (e) { console.error('History load error:', e); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === 'ArrowLeft' && page > 0) setPage(page - 1);
      if (e.key === 'ArrowRight') setPage(page + 1);
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [page]);

  const cardClass = 'surface-card-lg glass-glow';
  const species = ['deer', 'elephant', 'leopard', 'tiger', 'wolf'];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <motion.div whileHover={{ rotate: 10 }} className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
          <FiClock className="text-white text-lg" />
        </motion.div>
        <div>
          <h1 className="text-2xl font-bold neon-heading">Prediction History</h1>
          <p className="text-sm t-tertiary">Browse past identification results</p>
        </div>
      </div>

      {/* Statistics Panel */}
      {stats && !loading && history.length > 0 && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className={`${cardClass} p-4 grid grid-cols-2 md:grid-cols-4 gap-3`}>
          <div className="flex flex-col">
            <div className={`text-2xl font-bold bg-gradient-to-r from-orange-500 to-amber-500 bg-clip-text text-transparent`}>{stats.total}</div>
            <div className="text-xs t-tertiary">{stats.total}</div>
          </div>
          <div className="flex flex-col">
            <div className={`text-2xl font-bold text-orange-500`}>{(stats.avgConfidence * 100).toFixed(0)}%</div>
            <div className="text-xs t-tertiary">Avg confidence</div>
          </div>
          <div className="flex flex-col">
            <div className={`text-2xl font-bold text-green-500`}>{stats.highConfidence}</div>
            <div className="text-xs t-tertiary">High confidence</div>
          </div>
          <div className="flex flex-col">
            <div className={`text-2xl font-bold text-blue-500`}>{stats.speciesCount}</div>
            <div className="text-xs t-tertiary">Species identified</div>
          </div>
        </motion.div>
      )}

      {/* Filter */}
      <div className={`${cardClass} p-4 flex flex-wrap items-center gap-2`}>
        <FiFilter className="text-gray-400 mr-1" />
        <button onClick={() => { setFilter(''); setPage(0); }} className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${filter === '' ? 'bg-orange-500 text-white shadow-sm' : 'surface-inset t-secondary'}`}>All</button>
        {species.map(s => (
          <button key={s} onClick={() => { setFilter(s); setPage(0); }} className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold capitalize transition-all ${filter === s ? 'bg-orange-500 text-white shadow-sm' : 'surface-inset t-secondary'}`}>{s}</button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center h-32"><div className="animate-spin w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full" /></div>
      ) : history.length === 0 ? (
        <div className={`${cardClass} p-16 text-center`}>
          <GiPawPrint className="text-5xl mx-auto mb-3 text-gray-400" />
          <p className="text-lg t-tertiary">No predictions found</p>
          <p className="text-sm mt-1 t-dim">Upload some footprint images to get started</p>
        </div>
      ) : (
        <div className="space-y-2">
          {history.map((item, i) => (
            <motion.div 
              key={item.id || i} 
              initial={{ opacity: 0, x: -15 }} 
              animate={{ opacity: 1, x: 0 }} 
              transition={{ delay: i * 0.03 }}
              whileHover={{ scale: 1.01, y: -2 }}
              className={`${cardClass} p-4 flex items-center gap-4 group cursor-pointer transition-all hover:shadow-lg`}>
              
              {/* Icon */}
              <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition" style={{ background: 'linear-gradient(135deg, rgba(249,115,22,0.15), rgba(245,158,11,0.15))' }}>
                <GiPawPrint className="text-orange-500 text-xl" />
              </div>
              
              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="font-bold capitalize text-sm">{item.species || item.predicted_species}</div>
                <div className="text-xs t-tertiary">{item.filename || 'Unknown file'}</div>
                <div className="text-[10px] mt-1 t-dim">
                  {item.timestamp ? `${new Date(item.timestamp).toLocaleDateString()} • ${new Date(item.timestamp).toLocaleTimeString()}` : ''}
                </div>
              </div>
              
              {/* Confidence Badge */}
              <div className="flex-shrink-0">
                <ConfidenceBadge value={item.confidence || 0} />
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Pagination */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-center items-center gap-3">
        <motion.button 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setPage(Math.max(0, page - 1))} 
          disabled={page === 0} 
          className={`px-5 py-2.5 rounded-xl flex items-center gap-1.5 text-sm font-medium disabled:opacity-30 transition surface-inset`}
          title="Keyboard shortcut: ←">
          <FiChevronLeft size={14} /> Previous
        </motion.button>
        
        <div className="px-6 py-2.5 rounded-xl text-sm font-bold surface-inset">
          Page <span className="text-orange-500">{page + 1}</span>
        </div>
        
        <motion.button 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setPage(page + 1)} 
          disabled={history.length < PAGE_SIZE} 
          className={`px-5 py-2.5 rounded-xl flex items-center gap-1.5 text-sm font-medium disabled:opacity-30 transition surface-inset`}
          title="Keyboard shortcut: →">
          Next <FiChevronRight size={14} />
        </motion.button>
      </motion.div>
      
      <div className="text-center text-xs t-dim">
        💡 Use arrow keys (← →) to navigate pages
      </div>
    </div>
  );
}
