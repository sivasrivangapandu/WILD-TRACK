import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FiActivity, FiAlertTriangle, FiCheckCircle, FiXCircle,
    FiEdit3, FiRefreshCw, FiTrendingUp, FiShield, FiDatabase,
    FiTarget, FiZap
} from 'react-icons/fi';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, RadarChart, PolarGrid, PolarAngleAxis,
    PolarRadiusAxis, Radar
} from 'recharts';
import { useTheme } from '../context/ThemeContext';
import Skeleton from '../components/Skeleton';
import api from '../services/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/* ═══ Page entrance variants ═══ */
const pageVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const sectionVariants = {
    hidden: { opacity: 0, y: 14 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
};

/* ═══ Review Card ═══ */
function ReviewCard({ item, classNames, onAction, actionLoading }) {
    const [correctedSpecies, setCorrectedSpecies] = useState('');
    const [showCorrect, setShowCorrect] = useState(false);

    const imgSrc = item.image_path ? `${API_BASE}${item.image_path}` : null;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, y: -10 }}
            transition={{ duration: 0.25 }}
            className="surface-card-lg overflow-hidden glass-glow"
        >
            {/* Image */}
            <div className="h-40 overflow-hidden relative" style={{ background: 'var(--bg-surface-2)' }}>
                {imgSrc ? (
                    <img
                        src={imgSrc}
                        alt={item.filename}
                        className="w-full h-full object-cover"
                        onError={(e) => { e.target.style.display = 'none'; }}
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center t-dim text-xs">No image</div>
                )}
                {/* Confidence badge */}
                <div className="absolute top-2 right-2">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${item.confidence < 0.3 ? 'bg-red-500/20 text-red-400'
                            : item.confidence < 0.5 ? 'bg-amber-500/20 text-amber-400'
                                : 'bg-orange-500/20 text-orange-400'
                        }`}>
                        {(item.confidence * 100).toFixed(1)}%
                    </span>
                </div>
            </div>

            {/* Info */}
            <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold capitalize">{item.predicted_species}</span>
                    <span className="text-[10px] t-dim">{item.id}</span>
                </div>
                <div className="text-[11px] t-tertiary mb-3 truncate">{item.filename}</div>

                {/* Actions */}
                <div className="flex gap-2">
                    <button
                        onClick={() => onAction(item.id, 'approve')}
                        disabled={actionLoading}
                        className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-[11px] font-medium bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors disabled:opacity-40"
                    >
                        <FiCheckCircle size={12} /> Approve
                    </button>
                    <button
                        onClick={() => onAction(item.id, 'reject')}
                        disabled={actionLoading}
                        className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-[11px] font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-40"
                    >
                        <FiXCircle size={12} /> Reject
                    </button>
                    <button
                        onClick={() => setShowCorrect(!showCorrect)}
                        disabled={actionLoading}
                        className="flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[11px] font-medium bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors disabled:opacity-40"
                    >
                        <FiEdit3 size={12} />
                    </button>
                </div>

                {/* Correct species input */}
                <AnimatePresence>
                    {showCorrect && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="mt-2 overflow-hidden"
                        >
                            <div className="flex gap-2">
                                <select
                                    value={correctedSpecies}
                                    onChange={(e) => setCorrectedSpecies(e.target.value)}
                                    className="flex-1 px-2 py-1.5 rounded-lg text-[11px] border"
                                    style={{ background: 'var(--bg-surface-2)', borderColor: 'var(--border-primary)', color: 'var(--text-primary)' }}
                                >
                                    <option value="">Select species...</option>
                                    {classNames.map(cls => (
                                        <option key={cls} value={cls}>{cls}</option>
                                    ))}
                                </select>
                                <button
                                    onClick={() => {
                                        if (correctedSpecies) {
                                            onAction(item.id, 'correct', correctedSpecies);
                                            setShowCorrect(false);
                                        }
                                    }}
                                    disabled={!correctedSpecies || actionLoading}
                                    className="px-3 py-1.5 rounded-lg text-[11px] font-medium bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors disabled:opacity-40"
                                >
                                    Save
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
}

/* ═══ Main Page ═══ */
export default function MLOpsPage() {
    const { dark } = useTheme();
    const [analytics, setAnalytics] = useState(null);
    const [reviewQueue, setReviewQueue] = useState(null);
    const [systemStatus, setSystemStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('overview');

    const loadData = useCallback(async () => {
        try {
            const [analyticsRes, reviewRes, statusRes] = await Promise.all([
                api.getMlopsAnalytics(),
                api.getReviewQueue(),
                api.getSystemStatus(),
            ]);
            setAnalytics(analyticsRes.data);
            setReviewQueue(reviewRes.data);
            setSystemStatus(statusRes.data);
        } catch (e) {
            console.error('MLOps data load error:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const handleReviewAction = async (predId, action, correctedSpecies = null) => {
        setActionLoading(true);
        try {
            await api.submitReview(predId, action, correctedSpecies);
            // Refresh data
            const [analyticsRes, reviewRes] = await Promise.all([
                api.getMlopsAnalytics(),
                api.getReviewQueue(),
            ]);
            setAnalytics(analyticsRes.data);
            setReviewQueue(reviewRes.data);
        } catch (e) {
            console.error('Review action error:', e);
        } finally {
            setActionLoading(false);
        }
    };

    const gridColor = 'var(--grid-color)';

    if (loading) {
        return (
            <div className="space-y-6">
                <div className="flex items-center gap-3 mb-2">
                    <Skeleton variant="circle" width={40} height={40} />
                    <div><Skeleton variant="line" width={200} height={24} /><Skeleton variant="line" width={280} height={14} /></div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => <Skeleton key={i} variant="card" height={100} />)}
                </div>
                <Skeleton variant="card" height={400} />
            </div>
        );
    }

    // Build per-species confidence chart data
    const confBySpecies = analytics?.average_confidence_by_species
        ? Object.entries(analytics.average_confidence_by_species).map(([name, conf]) => ({
            name,
            confidence: Math.round(conf * 100),
        }))
        : [];

    // Build radar chart data
    const radarData = confBySpecies.map(item => ({
        subject: item.name,
        A: item.confidence,
        fullMark: 100,
    }));

    const statCards = [
        {
            label: 'Total Predictions',
            value: analytics?.total_predictions || 0,
            icon: FiDatabase,
            color: 'from-orange-500 to-amber-500',
            bgTint: 'bg-orange-500/10',
        },
        {
            label: 'Needs Review',
            value: analytics?.total_needs_review || 0,
            icon: FiAlertTriangle,
            color: 'from-yellow-500 to-amber-500',
            bgTint: 'bg-yellow-500/10',
        },
        {
            label: 'Hard Negatives',
            value: analytics?.hard_negatives_mined || 0,
            icon: FiTarget,
            color: 'from-red-500 to-pink-500',
            bgTint: 'bg-red-500/10',
        },
        {
            label: 'Rejection Rate',
            value: `${analytics?.rejection_rate || 0}%`,
            icon: FiShield,
            color: 'from-purple-500 to-violet-500',
            bgTint: 'bg-purple-500/10',
        },
    ];

    const tabs = [
        { id: 'overview', label: 'Overview', icon: FiTrendingUp },
        { id: 'review', label: `Review Queue (${reviewQueue?.total || 0})`, icon: FiAlertTriangle },
        { id: 'pipeline', label: 'Pipeline Info', icon: FiZap },
    ];

    return (
        <motion.div className="space-y-6" variants={pageVariants} initial="hidden" animate="visible">
            {/* Header */}
            <motion.div variants={sectionVariants} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/90 to-purple-600/90 flex items-center justify-center shadow-sm">
                        <FiActivity className="text-white text-lg" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold neon-heading">MLOps Lab</h1>
                        <p className="text-sm t-tertiary">Active Learning · Human-in-the-Loop · Model Analytics</p>
                    </div>
                </div>
                <button
                    onClick={() => { setLoading(true); loadData(); }}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium surface-card-lg hover:bg-orange-500/10 transition-colors"
                >
                    <FiRefreshCw size={13} /> Refresh
                </button>
            </motion.div>

            {/* Stat Cards */}
            <motion.div variants={sectionVariants} className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {statCards.map((stat, i) => (
                    <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.15 + i * 0.06 }}
                        className="relative overflow-hidden surface-card-lg p-4"
                    >
                        <div className={`absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl ${stat.color} opacity-10 rounded-bl-full`} />
                        <div className={`w-8 h-8 rounded-lg ${stat.bgTint} flex items-center justify-center mb-2`}>
                            <stat.icon className="text-sm" style={{ color: 'var(--color-primary)' }} />
                        </div>
                        <div className="text-xl font-extrabold">{stat.value}</div>
                        <div className="text-[11px] mt-1 t-tertiary">{stat.label}</div>
                    </motion.div>
                ))}
            </motion.div>

            {/* Tabs */}
            <motion.div variants={sectionVariants} className="flex gap-1 p-1 rounded-xl surface-card-lg">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 ${activeTab === tab.id
                                ? 'bg-orange-500/15 text-orange-400'
                                : 't-tertiary hover:t-primary surface-hover'
                            }`}
                    >
                        <tab.icon size={13} />
                        {tab.label}
                    </button>
                ))}
            </motion.div>

            {/* Tab Content */}
            <AnimatePresence mode="wait">
                {activeTab === 'overview' && (
                    <motion.div
                        key="overview"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="space-y-6"
                    >
                        {/* Charts Row */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Bar chart: Avg confidence per species */}
                            <div className="surface-card-lg p-6 glass-glow">
                                <h2 className="text-lg font-bold mb-4">Avg Confidence by Species</h2>
                                {confBySpecies.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={280}>
                                        <BarChart data={confBySpecies}>
                                            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                                            <XAxis dataKey="name" fontSize={11} />
                                            <YAxis fontSize={11} domain={[0, 100]} />
                                            <Tooltip
                                                contentStyle={{
                                                    background: 'var(--bg-card)',
                                                    border: '1px solid var(--border-primary)',
                                                    borderRadius: '8px',
                                                    fontSize: '12px',
                                                }}
                                            />
                                            <Bar dataKey="confidence" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <div className="text-center py-16 t-dim text-sm">No prediction data yet</div>
                                )}
                            </div>

                            {/* Radar chart: Species confidence radar */}
                            <div className="surface-card-lg p-6 glass-glow">
                                <h2 className="text-lg font-bold mb-4">Species Confidence Radar</h2>
                                {radarData.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={280}>
                                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                                            <PolarGrid stroke="var(--border-primary)" />
                                            <PolarAngleAxis dataKey="subject" fontSize={11} />
                                            <PolarRadiusAxis angle={30} domain={[0, 100]} fontSize={10} />
                                            <Radar
                                                name="Confidence"
                                                dataKey="A"
                                                stroke="#f97316"
                                                fill="#f97316"
                                                fillOpacity={0.25}
                                            />
                                            <Tooltip
                                                contentStyle={{
                                                    background: 'var(--bg-card)',
                                                    border: '1px solid var(--border-primary)',
                                                    borderRadius: '8px',
                                                    fontSize: '12px',
                                                }}
                                            />
                                        </RadarChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <div className="text-center py-16 t-dim text-sm">No prediction data yet</div>
                                )}
                            </div>
                        </div>

                        {/* System Status */}
                        {systemStatus && (
                            <div className="surface-card-lg p-6 glass-glow">
                                <h2 className="text-lg font-bold mb-4">System Status</h2>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {[
                                        { label: 'Model Version', value: systemStatus.model_version || 'N/A' },
                                        { label: 'Architecture', value: systemStatus.architecture || 'N/A' },
                                        { label: 'Val Accuracy', value: systemStatus.validation_accuracy ? `${(systemStatus.validation_accuracy * 100).toFixed(1)}%` : 'N/A' },
                                        { label: 'Uptime', value: systemStatus.uptime || 'N/A' },
                                        { label: 'TTA', value: systemStatus.tta_enabled ? `Enabled (${systemStatus.tta_passes} passes)` : 'Disabled' },
                                        { label: 'Classes', value: systemStatus.total_classes || 0 },
                                        { label: 'Image Size', value: `${systemStatus.img_size}px` },
                                        { label: 'Status', value: systemStatus.status || 'unknown' },
                                    ].map((item, i) => (
                                        <div key={i} className="surface-inset p-3 rounded-lg">
                                            <div className="text-[10px] t-dim uppercase tracking-wider mb-1">{item.label}</div>
                                            <div className="text-sm font-semibold">{item.value}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </motion.div>
                )}

                {activeTab === 'review' && (
                    <motion.div
                        key="review"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                    >
                        <div className="surface-card-lg p-6 glass-glow">
                            <div className="flex items-center justify-between mb-4">
                                <div>
                                    <h2 className="text-lg font-bold">Human-in-the-Loop Review</h2>
                                    <p className="text-xs t-tertiary mt-1">
                                        Low-confidence predictions flagged for manual verification. Corrections feed the active learning loop.
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-yellow-500/10 text-yellow-400">
                                        {reviewQueue?.total || 0} pending
                                    </span>
                                </div>
                            </div>

                            {reviewQueue?.items?.length > 0 ? (
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                    <AnimatePresence>
                                        {reviewQueue.items.map(item => (
                                            <ReviewCard
                                                key={item.id}
                                                item={item}
                                                classNames={systemStatus?.class_names || []}
                                                onAction={handleReviewAction}
                                                actionLoading={actionLoading}
                                            />
                                        ))}
                                    </AnimatePresence>
                                </div>
                            ) : (
                                <div className="text-center py-16">
                                    <FiCheckCircle className="mx-auto text-3xl text-green-500 mb-3" />
                                    <div className="text-sm font-medium">All caught up!</div>
                                    <div className="text-xs t-tertiary mt-1">No images pending review</div>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}

                {activeTab === 'pipeline' && (
                    <motion.div
                        key="pipeline"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="space-y-6"
                    >
                        <div className="surface-card-lg p-6 glass-glow">
                            <h2 className="text-lg font-bold mb-4">Multi-Stage Inference Pipeline</h2>
                            <p className="text-xs t-tertiary mb-6">
                                Every image passes through 5 stages before producing a final prediction.
                            </p>

                            <div className="space-y-4">
                                {[
                                    {
                                        stage: '0',
                                        title: 'Data Quality Gate',
                                        desc: 'Laplacian variance blur detection · pHash duplicate detection · Low resolution rejection',
                                        color: 'from-blue-500 to-cyan-500',
                                        status: 'Active',
                                    },
                                    {
                                        stage: '1',
                                        title: 'YOLO Object Detection',
                                        desc: 'Locates the footprint in the image and crops to the bounding box for cleaner classification',
                                        color: 'from-green-500 to-emerald-500',
                                        status: systemStatus?.tta_enabled ? 'Active' : 'Standby',
                                    },
                                    {
                                        stage: '2',
                                        title: 'Species Classifier',
                                        desc: `${systemStatus?.architecture || 'EfficientNet'} model with Test-Time Augmentation (${systemStatus?.tta_passes || 3} passes)`,
                                        color: 'from-orange-500 to-amber-500',
                                        status: 'Active',
                                    },
                                    {
                                        stage: '3',
                                        title: 'Geo-Aware Filter',
                                        desc: 'Filters impossible species predictions based on GPS coordinates (e.g., no tigers in Africa)',
                                        color: 'from-purple-500 to-violet-500',
                                        status: 'Active',
                                    },
                                    {
                                        stage: '4',
                                        title: 'Confidence Calibration',
                                        desc: 'Temperature scaling (T=1.2) converts raw softmax into calibrated probabilities + Shannon entropy',
                                        color: 'from-pink-500 to-rose-500',
                                        status: 'Active',
                                    },
                                ].map((stage, i) => (
                                    <motion.div
                                        key={stage.stage}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: 0.1 + i * 0.08 }}
                                        className="flex items-start gap-4 p-4 rounded-xl surface-inset"
                                    >
                                        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${stage.color} flex items-center justify-center flex-shrink-0`}>
                                            <span className="text-white text-sm font-bold">{stage.stage}</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-sm font-semibold">{stage.title}</span>
                                                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${stage.status === 'Active'
                                                        ? 'bg-green-500/15 text-green-400'
                                                        : 'bg-yellow-500/15 text-yellow-400'
                                                    }`}>
                                                    {stage.status}
                                                </span>
                                            </div>
                                            <p className="text-xs t-tertiary">{stage.desc}</p>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>

                        {/* Active Learning Flow */}
                        <div className="surface-card-lg p-6 glass-glow">
                            <h2 className="text-lg font-bold mb-4">Active Learning Loop</h2>
                            <div className="flex items-center justify-between gap-4 flex-wrap">
                                {[
                                    { icon: FiAlertTriangle, label: 'Low Confidence', desc: 'Flagged for review', color: 'text-yellow-500' },
                                    { icon: FiEdit3, label: 'Human Review', desc: 'Manual verification', color: 'text-blue-500' },
                                    { icon: FiTarget, label: 'Hard Negatives', desc: `${analytics?.hard_negatives_mined || 0} collected`, color: 'text-red-500' },
                                    { icon: FiRefreshCw, label: 'Retrain', desc: 'Model improves', color: 'text-green-500' },
                                ].map((step, i) => (
                                    <div key={i} className="flex items-center gap-3">
                                        <div className="flex flex-col items-center text-center">
                                            <div className={`w-12 h-12 rounded-xl surface-inset flex items-center justify-center mb-2`}>
                                                <step.icon className={`text-lg ${step.color}`} />
                                            </div>
                                            <div className="text-xs font-semibold">{step.label}</div>
                                            <div className="text-[10px] t-dim">{step.desc}</div>
                                        </div>
                                        {i < 3 && (
                                            <div className="text-lg t-dim mx-1">→</div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
