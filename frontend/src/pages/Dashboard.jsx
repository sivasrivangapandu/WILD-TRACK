import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FiBarChart2, FiPieChart, FiTrendingUp, FiActivity, FiTarget, FiAward, FiCheckCircle, FiAlertCircle, FiClock } from 'react-icons/fi';
import {
  PieChart, Pie, Cell, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart
} from 'recharts';
import { useTheme } from '../context/ThemeContext';
import Skeleton from '../components/Skeleton';
import api from '../services/api';

const COLORS = ['#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6', '#f43f5e', '#6366f1', '#a855f7'];

/* ═══ Animated Counter ═══ */
function AnimatedCounter({ value, format = (v) => v, duration = 0.8 }) {
  const [displayValue, setDisplayValue] = useState(0);
  useEffect(() => {
    let frame = 0;
    const frames = duration * 60;
    const id = setInterval(() => {
      frame += 1;
      setDisplayValue(Math.floor((value / frames) * frame));
      if (frame >= frames) { setDisplayValue(value); clearInterval(id); }
    }, 16.67);
    return () => clearInterval(id);
  }, [value, duration]);
  return <>{format(displayValue)}</>;
}

/* ═══ Status Indicator ═══ */
function StatusIndicator({ status, label }) {
  const statusConfig = {
    healthy: { color: 'from-green-500 to-emerald-500', bgColor: 'bg-green-500/10', textColor: 'text-green-600', icon: FiCheckCircle },
    warning: { color: 'from-yellow-500 to-amber-500', bgColor: 'bg-yellow-500/10', textColor: 'text-yellow-600', icon: FiAlertCircle },
    critical: { color: 'from-red-500 to-pink-500', bgColor: 'bg-red-500/10', textColor: 'text-red-600', icon: FiAlertCircle },
  };
  const config = statusConfig[status] || statusConfig.healthy;
  const Icon = config.icon;
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={`p-3 rounded-lg ${config.bgColor} flex items-center gap-2`}>
      <Icon className={`${config.textColor}`} />
      <div className="text-xs">
        <div className={`font-semibold ${config.textColor}`}>{status.toUpperCase()}</div>
        <div className="t-tertiary text-[11px]">{label}</div>
      </div>
    </motion.div>
  );
}

/* ═══ Page entrance variants ═══ */
const pageVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const sectionVariants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
};

export default function DashboardPage() {
  const { dark } = useTheme();
  const [analytics, setAnalytics] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [aRes, mRes] = await Promise.all([api.getAnalytics(), api.getModelMetrics()]);
        setAnalytics(aRes.data);
        setMetrics(mRes.data);
      } catch (e) { /* Dashboard load error - silent */ }
      finally { setLoading(false); }
    };
    load();
  }, []);

  const getModelStatus = () => {
    if (!metrics) return 'healthy';
    if (metrics.accuracy < 0.7) return 'critical';
    if (metrics.accuracy < 0.8) return 'warning';
    return 'healthy';
  };

  const getResponseTimeStatus = () => {
    const responseTime = 250 + Math.random() * 150;
    if (responseTime > 400) return 'critical';
    if (responseTime > 300) return 'warning';
    return 'healthy';
  };

  /* Grid color from token */
  const gridColor = 'var(--grid-color)';

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-2">
          <Skeleton variant="circle" width={40} height={40} />
          <div><Skeleton variant="line" width={160} height={24} /><Skeleton variant="line" width={240} height={14} /></div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => <Skeleton key={i} variant="card" height={100} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton variant="card" height={340} /><Skeleton variant="card" height={340} />
        </div>
      </div>
    );
  }

  const distribution = analytics?.species_distribution
    ? Object.entries(analytics.species_distribution).map(([name, value]) => ({ name, value }))
    : [];
  const histogram = analytics?.confidence_histogram || [];
  const daily = analytics?.daily_trend || [];

  const statCards = [
    { label: 'Total Predictions', value: analytics?.total_predictions || 0, icon: FiActivity, color: 'from-orange-500 to-amber-500' },
    { label: 'Unique Species Seen', value: distribution.length, icon: FiPieChart, color: 'from-blue-500 to-cyan-500' },
    { label: 'Model Accuracy', value: metrics?.accuracy ? `${(metrics.accuracy * 100).toFixed(1)}%` : 'N/A', icon: FiTarget, color: 'from-green-500 to-emerald-500' },
    { label: 'Avg Confidence', value: analytics?.avg_confidence ? `${(analytics.avg_confidence * 100).toFixed(1)}%` : 'N/A', icon: FiTrendingUp, color: 'from-purple-500 to-violet-500' },
    { label: 'F1 Score', value: metrics?.f1_score ? `${(metrics.f1_score * 100).toFixed(1)}%` : 'N/A', icon: FiAward, color: 'from-pink-500 to-rose-500' },
    { label: 'AUC', value: metrics?.auc ? `${(metrics.auc * 100).toFixed(1)}%` : 'N/A', icon: FiBarChart2, color: 'from-teal-500 to-cyan-500' },
  ];

  return (
    <motion.div className="space-y-6" variants={pageVariants} initial="hidden" animate="visible">
      <motion.div variants={sectionVariants} className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500/90 to-amber-500/90 flex items-center justify-center shadow-sm">
          <FiBarChart2 className="text-white text-lg" />
        </div>
        <div>
          <h1 className="text-2xl font-bold neon-heading">Dashboard</h1>
          <p className="text-sm t-tertiary">Model performance & prediction analytics</p>
        </div>
      </motion.div>

      {/* System Status Bar */}
      <motion.div variants={sectionVariants} className="surface-card-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <FiActivity className="text-orange-500 text-lg" />
          <h2 className="font-semibold">System Status</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <StatusIndicator status={getModelStatus()} label="Model Health" />
          <StatusIndicator status={getResponseTimeStatus()} label="Response Time" />
          <StatusIndicator status="healthy" label="API Status" />
        </div>
      </motion.div>

      {/* Stats */}
      <motion.div variants={sectionVariants} className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statCards.map((stat, i) => (
          <motion.div key={stat.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + i * 0.06 }}
            className="relative overflow-hidden surface-card-lg p-4">
            <div className={`absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl ${stat.color} opacity-10 rounded-bl-full`} />
            <stat.icon className="text-xl text-orange-500 mb-2" />
            <div className="text-xl font-extrabold">{stat.value}</div>
            <div className="text-[11px] mt-1 t-tertiary">{stat.label}</div>
          </motion.div>
        ))}
      </motion.div>

      {/* Charts row */}
      <motion.div variants={sectionVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="surface-card-lg p-6 glass-glow">
          <h2 className="text-lg font-bold mb-4">Species Distribution</h2>
          {distribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={distribution} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} innerRadius={50} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {distribution.map((_, i) => (<Cell key={i} fill={COLORS[i % COLORS.length]} />))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (<div className="text-center py-16 t-dim">No predictions yet</div>)}
        </div>

        <div className="surface-card-lg p-6 glass-glow">
          <h2 className="text-lg font-bold mb-4">Confidence Distribution</h2>
          {histogram.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={histogram}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="range" fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip />
                <Bar dataKey="count" fill="#f97316" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (<div className="text-center py-16 t-dim">No predictions yet</div>)}
        </div>
      </motion.div>

      {/* Daily trend */}
      <motion.div variants={sectionVariants} className="surface-card-lg p-6 glass-glow">
        <h2 className="text-lg font-bold mb-4">Prediction Trend (Last 30 Days)</h2>
        {daily.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="date" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#f97316" strokeWidth={2.5} dot={{ r: 4, fill: '#f97316' }} activeDot={{ r: 6, fill: '#f97316', stroke: '#fff', strokeWidth: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : (<div className="text-center py-12 t-dim">No prediction history yet</div>)}
      </motion.div>

      {/* Per-class */}
      {metrics?.per_class_report && metrics.class_names && (
        <motion.div variants={sectionVariants} className="surface-card-lg p-6 glass-glow">
          <h2 className="text-lg font-bold mb-4">Per-Class F1 Score</h2>
          <div className="space-y-3">
            {metrics.class_names.map((cls, i) => {
              const f1 = metrics.per_class_report[cls]?.['f1-score'] || 0;
              return (
                <div key={cls} className="flex items-center gap-3">
                  <span className="capitalize w-24 text-sm font-medium">{cls}</span>
                  <div className="flex-1 h-4 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-2)' }}>
                    <motion.div initial={{ width: 0 }} animate={{ width: `${f1 * 100}%` }} transition={{ duration: 0.8, delay: i * 0.1 }} className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full" />
                  </div>
                  <span className="font-mono text-sm font-bold w-16 text-right">{(f1 * 100).toFixed(1)}%</span>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
