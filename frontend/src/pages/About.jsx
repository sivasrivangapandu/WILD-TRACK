import { motion } from 'framer-motion';
import { FiInfo, FiCpu, FiDatabase, FiLayers, FiCode, FiMonitor } from 'react-icons/fi';
import { GiPawPrint } from 'react-icons/gi';
import { useTheme } from '../context/ThemeContext';

const techStack = [
  { icon: FiCpu, label: 'EfficientNetB3 v4', desc: 'Pre-trained on ImageNet, fine-tuned for footprints at 300×300 with SE Attention' },
  { icon: FiDatabase, label: 'SQLite + SQLAlchemy', desc: 'Persistent prediction storage with analytics' },
  { icon: FiLayers, label: 'FastAPI', desc: 'Async Python backend with auto-docs at /docs' },
  { icon: GiPawPrint, label: 'Grad-CAM', desc: 'Explainable AI heatmap visualization' },
  { icon: FiCode, label: 'React + Vite', desc: 'Modern frontend with Tailwind CSS & Framer Motion' },
  { icon: FiMonitor, label: 'Recharts', desc: 'Interactive charts for analytics dashboard' },
];

const speciesList = [
  { name: 'Tiger', emoji: '\u{1F405}' },
  { name: 'Leopard', emoji: '\u{1F406}' },
  { name: 'Elephant', emoji: '\u{1F418}' },
  { name: 'Deer', emoji: '\u{1F98C}' },
  { name: 'Wolf', emoji: '\u{1F43A}' },
];

export default function AboutPage() {
  const { dark } = useTheme();
  const cardClass = 'surface-card-lg glass-glow';

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold neon-heading flex items-center gap-2">
        <FiInfo className="text-orange-500" /> About WildTrackAI
      </h1>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`${cardClass} p-8 space-y-4`}>
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
            <GiPawPrint className="text-white text-3xl" />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold">WildTrackAI</h2>
            <p className="t-secondary">Intelligent Animal Footprint Identification</p>
          </div>
        </div>
        <p className="leading-relaxed t-secondary">
          WildTrackAI is a deep learning system that identifies animal species from footprint images.
          Built for wildlife researchers, conservationists, and ecologists, it supports 5 species
          and provides explainable AI through Grad-CAM heatmaps showing which parts of the footprint
          contributed to the classification. The model achieves 77.5% accuracy using EfficientNetB3 v4
          with Test-Time Augmentation.
        </p>
      </motion.div>

      {/* Tech stack */}
      <div className={`${cardClass} p-6`}>
        <h3 className="text-lg font-bold mb-4">Technology Stack</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {techStack.map((item, i) => (
            <motion.div key={item.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }} className="p-4 rounded-xl" style={{ background: 'var(--bg-surface-2)' }}>
              <item.icon className="text-xl text-orange-500 mb-2" />
              <div className="font-semibold text-sm">{item.label}</div>
              <div className="text-xs mt-1 t-tertiary">{item.desc}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Species */}
      <div className={`${cardClass} p-6`}>
        <h3 className="text-lg font-bold mb-4">Supported Species (5)</h3>
        <div className="grid grid-cols-5 gap-3">
          {speciesList.map(s => (
            <div key={s.name} className="p-4 rounded-xl text-center" style={{ background: 'var(--bg-surface-2)' }}>
              <div className="text-3xl mb-2">{s.emoji}</div>
              <div className="text-xs font-semibold">{s.name}</div>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className={`${cardClass} p-6`}>
        <h3 className="text-lg font-bold mb-4">How It Works</h3>
        <div className="space-y-3">
          {[
            { step: '1', text: 'Upload a footprint image (PNG, JPG, or WEBP)' },
            { step: '2', text: 'EfficientNetB3 v4 processes the image at 300×300 with TTA (3 passes)' },
            { step: '3', text: 'Softmax classification returns top-3 predictions with confidence' },
            { step: '4', text: 'Grad-CAM generates a heatmap showing important image regions' },
            { step: '5', text: 'Results saved to database for tracking and analytics' },
          ].map(s => (
            <div key={s.step} className="flex gap-3 items-start">
              <span className="w-7 h-7 rounded-full bg-gradient-to-br from-orange-500 to-amber-500 text-white text-xs flex items-center justify-center shrink-0 mt-0.5 font-bold">{s.step}</span>
              <span className="text-sm t-secondary">{s.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Model Info */}
      <div className={`${cardClass} p-6`}>
        <h3 className="text-lg font-bold mb-4">Model Details</h3>
        <div className="grid grid-cols-2 gap-4">
          {[
            { k: 'Architecture', v: 'EfficientNetB3 + SE Attention' },
            { k: 'Input Size', v: '300 × 300 px' },
            { k: 'Training Images', v: '2,000 (1,600 train + 400 val)' },
            { k: 'Accuracy', v: '77.5% (with TTA)' },
            { k: 'Framework', v: 'TensorFlow 2.20' },
            { k: 'Explainability', v: 'Grad-CAM heatmaps' },
          ].map(item => (
            <div key={item.k} className="p-3 rounded-lg" style={{ background: 'var(--bg-surface-2)' }}>
              <div className="text-xs t-tertiary">{item.k}</div>
              <div className="font-semibold text-sm mt-0.5">{item.v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
