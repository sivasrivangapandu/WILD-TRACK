import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  FiUpload, FiBarChart2, FiSearch, FiLayers, FiZap,
  FiMessageCircle, FiActivity, FiArrowRight
} from 'react-icons/fi';
import { GiPawPrint } from 'react-icons/gi';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

const features = [
  { icon: FiZap, title: 'Deep Learning', desc: 'MobileNetV2 (v4-cpu) with cosine decay LR — 85.8% accuracy on 5 species', color: 'from-orange-500 to-amber-500' },
  { icon: GiPawPrint, title: 'Grad-CAM', desc: 'Explainable AI heatmaps showing which parts of the footprint drive the prediction', color: 'from-blue-500 to-cyan-500' },
  { icon: FiBarChart2, title: 'Live Analytics', desc: 'Real-time dashboard with species distribution, confidence trends, and per-class metrics', color: 'from-green-500 to-emerald-500' },
  { icon: FiLayers, title: 'Batch Mode', desc: 'Process hundreds of footprint images at once with CSV export for field research', color: 'from-purple-500 to-violet-500' },
  { icon: FiSearch, title: 'Compare', desc: 'Side-by-side footprint comparison with similarity scoring between specimens', color: 'from-pink-500 to-rose-500' },
  { icon: FiMessageCircle, title: 'AI Chatbot', desc: 'Upload images and have an interactive discussion about species identification', color: 'from-teal-500 to-cyan-500' },
];

const speciesData = [
  { name: 'Tiger', emoji: '\u{1F405}', status: 'Endangered' },
  { name: 'Leopard', emoji: '\u{1F406}', status: 'Vulnerable' },
  { name: 'Elephant', emoji: '\u{1F418}', status: 'Endangered' },
  { name: 'Deer', emoji: '\u{1F98C}', status: 'Least Concern' },
  { name: 'Wolf', emoji: '\u{1F43A}', status: 'Least Concern' },
];

export default function HomePage() {
  const { dark } = useTheme();
  const [stats, setStats] = useState(null);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    Promise.all([
      api.getAnalytics().catch(() => null),
      api.getModelMetrics().catch(() => null),
    ]).then(([aRes, mRes]) => {
      if (aRes?.data) setStats(aRes.data);
      if (mRes?.data) setMetrics(mRes.data);
    });
  }, []);

  const accuracy = metrics?.accuracy ? (metrics.accuracy * 100).toFixed(1) : '85.8';

  return (
    <div className="space-y-14 pb-12">
      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="relative text-center py-14">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-80 h-80 bg-orange-500/[0.06] rounded-full blur-3xl" />
        </div>
        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', delay: 0.15, stiffness: 150 }} className="relative inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-orange-500 to-amber-500 mb-6 shadow-lg shadow-orange-500/20">
          <GiPawPrint className="text-white text-4xl" />
        </motion.div>
        <motion.h1 initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }} className="text-5xl font-extrabold mb-4 tracking-tight">
          <span className="animate-text-shimmer">WildTrackAI</span>
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }} className="text-lg max-w-xl mx-auto leading-relaxed t-secondary">
          Intelligent animal footprint identification using deep learning. Upload a photo and instantly identify the species with{' '}
          <span className="text-orange-500 font-semibold">{accuracy}% accuracy</span>.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }} className="flex flex-wrap gap-3 justify-center mt-8">
          <Link to="/upload" className="group px-7 py-3.5 bg-gradient-to-r from-orange-500 to-amber-500 text-white font-bold rounded-xl shadow-lg shadow-orange-500/15 hover:shadow-xl hover:shadow-orange-500/20 transition-all duration-300 flex items-center gap-2">
            <FiUpload className="text-lg" /> Upload Footprint <FiArrowRight className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <Link to="/chat" className="px-7 py-3.5 font-bold rounded-xl border transition-all duration-200 flex items-center gap-2 b-primary surface-hover">
            <FiMessageCircle className="text-orange-500" /> AI Chatbot
          </Link>
          <Link to="/dashboard" className="px-7 py-3.5 font-bold rounded-xl border transition-all duration-200 flex items-center gap-2 b-primary surface-hover">
            <FiBarChart2 /> Dashboard
          </Link>
        </motion.div>
      </motion.div>

      {/* Stats */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Model Accuracy', value: `${accuracy}%`, icon: FiActivity, gradient: 'from-orange-500 to-amber-500' },
          { label: 'Species Supported', value: '5', icon: GiPawPrint, gradient: 'from-blue-500 to-cyan-500' },
          { label: 'Total Predictions', value: stats?.total_predictions || '0', icon: FiBarChart2, gradient: 'from-green-500 to-emerald-500' },
          { label: 'Architecture', value: 'EffNetB3', icon: FiZap, gradient: 'from-purple-500 to-violet-500' },
        ].map((stat, i) => (
          <motion.div key={stat.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.55 + i * 0.06 }}
            whileHover={{ y: -2, transition: { duration: 0.15 } }}
            className="relative overflow-hidden rounded-xl p-5 surface-inset surface-hover transition-all duration-200">
            <div className={`absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl ${stat.gradient} opacity-[0.06] rounded-bl-full`} />
            <stat.icon className="text-xl mb-2 text-orange-500" />
            <div className="text-2xl font-extrabold">{stat.value}</div>
            <div className="text-[11px] mt-1 t-tertiary">{stat.label}</div>
          </motion.div>
        ))}
      </motion.div>

      {/* Features */}
      <div>
        <h2 className="text-xl font-bold mb-5">Powerful Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feat, i) => (
            <motion.div key={feat.title} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 + i * 0.06 }} whileHover={{ y: -3, transition: { duration: 0.15 } }} className="group relative overflow-hidden p-5 rounded-xl surface-inset surface-hover transition-all duration-200 cursor-default">
              <div className={`absolute top-0 right-0 w-28 h-28 bg-gradient-to-bl ${feat.color} opacity-[0.04] group-hover:opacity-[0.08] rounded-bl-full transition-opacity duration-300`} />
              <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br ${feat.color} mb-3`}>
                <feat.icon className="text-white text-lg" />
              </div>
              <h3 className="text-sm font-bold mb-1.5">{feat.title}</h3>
              <p className="text-xs leading-relaxed t-tertiary">{feat.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Species */}
      <div>
        <h2 className="text-xl font-bold mb-5">Identified Species</h2>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {speciesData.map((s, i) => (
            <motion.div key={s.name} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 + i * 0.06 }} whileHover={{ y: -2 }} className="relative overflow-hidden p-4 rounded-xl text-center transition-all duration-200 surface-inset">
              <div className="text-3xl mb-2">{s.emoji}</div>
              <div className="font-bold text-xs mb-1">{s.name}</div>
              <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${s.status === 'Endangered' ? 'bg-red-500/10 text-red-500' : s.status === 'Vulnerable' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-green-500/10 text-green-500'}`}>{s.status}</span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* How It Works */}
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="p-7 rounded-xl surface-inset">
        <h2 className="text-xl font-bold mb-5">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            { step: '1', title: 'Upload', desc: 'Drop a footprint image (PNG, JPG, WEBP)', icon: FiUpload },
            { step: '2', title: 'Analyze', desc: 'EfficientNetB3 v4 processes at 300\u00d7300', icon: FiZap },
            { step: '3', title: 'Identify', desc: 'Top-3 predictions with confidence', icon: FiSearch },
            { step: '4', title: 'Explain', desc: 'Grad-CAM heatmap highlights key regions', icon: GiPawPrint },
          ].map((item, i) => (
            <motion.div key={item.step} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.0 + i * 0.08 }} className="flex flex-col items-center text-center">
              <div className="relative">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center mb-3">
                  <item.icon className="text-white text-lg" />
                </div>
                <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-orange-500 text-white text-[10px] font-bold flex items-center justify-center">{item.step}</div>
              </div>
              <h3 className="font-bold mb-1">{item.title}</h3>
              <p className="text-xs t-tertiary">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* CTA */}
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-orange-500 via-amber-500 to-orange-600 p-8 text-center text-white">
        <div className="absolute inset-0 bg-black/[0.06]" />
        <div className="relative">
          <GiPawPrint className="text-4xl mx-auto mb-3 opacity-90" />
          <h2 className="text-2xl font-extrabold mb-2">Ready to Identify?</h2>
          <p className="text-white/70 mb-5 max-w-md mx-auto text-sm">Upload a footprint image and let our AI identify the species in seconds.</p>
          <Link to="/upload" className="inline-flex items-center gap-2 px-7 py-3.5 bg-white text-orange-600 font-bold rounded-xl hover:shadow-lg transition-all duration-200">
            <FiUpload /> Get Started
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
