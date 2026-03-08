import { useState, useCallback, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiUpload, FiX, FiImage, FiActivity, FiEye, FiCheckCircle, FiAlertTriangle, FiCpu, FiDownload, FiTarget, FiInfo, FiHelpCircle, FiGrid, FiCrosshair, FiMaximize2, FiLayers, FiNavigation } from 'react-icons/fi';
import { GiPawPrint, GiFootprint, GiClawSlashes } from 'react-icons/gi';
import { TbRulerMeasure } from 'react-icons/tb';
import { useTheme } from '../context/ThemeContext';
import { useAppState } from '../context/AppStateContext';
import api from '../services/api';
import ConfidenceRing from '../components/ConfidenceRing';
import CameraCapture from '../components/CameraCapture';
import { FiCamera } from 'react-icons/fi';

/* ═══ Track Morphology Data ═══ */
const TRACK_MORPHOLOGY = {
  tiger: {
    toeCount: '4',
    clawMarks: 'Absent — retractable claws',
    heelPad: 'Bilobed posterior, asymmetric',
    symmetry: 'Asymmetric — wider than long',
    family: 'Felidae',
    trackWidth: '12–16 cm',
    gait: 'Direct-register walk',
    distinguishing: 'Central pad wider than long with bilobed rear edge. No claw impressions.',
  },
  leopard: {
    toeCount: '4',
    clawMarks: 'Absent — retractable claws',
    heelPad: 'Tri-lobed posterior edge',
    symmetry: 'Round, proportional',
    family: 'Felidae',
    trackWidth: '7–10 cm',
    gait: 'Direct-register walk',
    distinguishing: 'Proportionally rounder and smaller than tiger. Tri-lobed rear pad edge.',
  },
  elephant: {
    toeCount: 'N/A — round pad',
    clawMarks: 'None',
    heelPad: 'Circular, cracked-skin texture',
    symmetry: 'Radially symmetric',
    family: 'Elephantidae',
    trackWidth: '40–50 cm',
    gait: 'Ambling — overlapping front-rear',
    distinguishing: 'Largest land animal print. Deep impressions with skin-texture pattern.',
  },
  deer: {
    toeCount: '2 — cloven hoof',
    clawMarks: 'Dewclaws in soft substrate',
    heelPad: 'Heart-shaped, pointed tips',
    symmetry: 'Bilaterally symmetric',
    family: 'Cervidae',
    trackWidth: '5–9 cm',
    gait: 'Walk / bounding',
    distinguishing: 'Heart-shaped cloven hooves with pointed tips. Dewclaw marks in mud/snow.',
  },
  wolf: {
    toeCount: '4',
    clawMarks: 'Present — non-retractable',
    heelPad: 'Oval, X-pattern between toes',
    symmetry: 'Oval, elongated',
    family: 'Canidae',
    trackWidth: '10–13 cm',
    gait: 'Direct-register trot',
    distinguishing: 'X-pattern between front and rear toe pairs. Visible claw marks at all toes.',
  },
};

/* ═══ Track Morphology Panel ═══ */
function TrackMorphologyPanel({ species, showHeatmap, confidence, imageQuality }) {
  const morph = TRACK_MORPHOLOGY[species?.toLowerCase()];
  if (!morph) return null;

  // Derive Structural Alignment from confidence
  const structuralAlignment =
    confidence > 0.75 ? 'High' : confidence > 0.5 ? 'Moderate' : 'Low';

  // Estimate interdigital spread based on species
  const interdigitalSpread = {
    tiger: 'Moderate — asymmetric spacing',
    leopard: 'Moderate — symmetric spacing',
    elephant: 'N/A — radial pad',
    deer: 'N/A — cloven hoof',
    wolf: 'Moderate — X-pattern toes',
  }[species?.toLowerCase()] || 'Unknown';

  // Determine quality warning icon and colors
  const qualityWarningConfig = {
    caution: {
      bgColor: 'bg-yellow-500/5 border border-yellow-500/15',
      iconColor: 'text-yellow-400/70',
      textColor: 'text-yellow-500',
      icon: FiAlertTriangle,
    },
    warning: {
      bgColor: 'bg-amber-500/5 border border-amber-500/15',
      iconColor: 'text-amber-400/70',
      textColor: 'text-amber-500',
      icon: FiAlertTriangle,
    },
    critical: {
      bgColor: 'bg-red-500/5 border border-red-500/15',
      iconColor: 'text-red-400/70',
      textColor: 'text-red-500',
      icon: FiAlertTriangle,
    },
  };

  const traits = [
    { icon: GiFootprint, label: 'Toe Count', value: morph.toeCount },
    { icon: GiClawSlashes, label: 'Claw Marks', value: morph.clawMarks },
    { icon: FiMaximize2, label: 'Heel Pad', value: morph.heelPad },
    { icon: FiLayers, label: 'Symmetry', value: morph.symmetry },
    { icon: GiPawPrint, label: 'Family', value: morph.family },
    { icon: TbRulerMeasure, label: 'Track Width', value: morph.trackWidth },
    { icon: FiNavigation, label: 'Gait Pattern', value: morph.gait },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6, duration: 0.3 }}
      className="mt-6 space-y-4"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <FiGrid size={13} className="text-orange-400/70" />
        <span className="text-xs font-semibold uppercase tracking-wider t-tertiary">
          Track Morphology Analysis
        </span>
      </div>

      {/* Data grid — 2-column breathable layout */}
      <div className="grid grid-cols-2 gap-y-2 gap-x-4 p-4 rounded-xl border b-subtle" style={{ background: 'var(--bg-card)' }}>
        {traits.map((trait) => {
          const Icon = trait.icon;
          return (
            <div key={trait.label} className="flex items-start gap-2 py-1">
              <Icon size={12} className="text-orange-400/70 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wider t-tertiary font-medium">{trait.label}</div>
                <div className="text-sm font-semibold leading-snug">{trait.value}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Structural Alignment Score */}
      <div className="grid grid-cols-2 gap-2 p-3 rounded-xl text-xs border b-subtle" style={{ background: 'var(--bg-card)' }}>
        <div>
          <div className="text-[10px] uppercase tracking-wider t-tertiary font-medium">Structural Alignment</div>
          <div className={`text-sm font-semibold mt-1 ${structuralAlignment === 'High' ? 'text-green-500' :
            structuralAlignment === 'Moderate' ? 'text-blue-500' :
              'text-amber-500'
            }`}>{structuralAlignment}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider t-tertiary font-medium">Interdigital Spread</div>
          <div className="text-sm font-semibold mt-1 text-orange-500">{interdigitalSpread}</div>
        </div>
      </div>

      {/* Distinguishing feature callout */}
      <div className="p-3 rounded-xl text-xs leading-relaxed surface-inset">
        <div className="flex items-start gap-2">
          <FiCrosshair size={12} className="text-orange-500 mt-0.5 shrink-0" />
          <div>
            <span className="font-semibold text-orange-500">Key Identifier: </span>
            <span className="t-secondary">{morph.distinguishing}</span>
          </div>
        </div>
      </div>

      {/* Image Quality Warning */}
      {imageQuality && imageQuality.quality_warning && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className={`p-3 rounded-xl text-xs leading-relaxed ${qualityWarningConfig[imageQuality.quality_severity]?.bgColor || 'surface-inset'}`}
        >
          <div className="flex items-start gap-2">
            {(() => {
              const config = qualityWarningConfig[imageQuality.quality_severity];
              const Icon = config?.icon || FiAlertTriangle;
              return <Icon size={12} className={`${config?.iconColor || 'text-amber-400/70'} mt-0.5 shrink-0`} />;
            })()}
            <div>
              <span className={`font-semibold ${qualityWarningConfig[imageQuality.quality_severity]?.textColor || 'text-amber-500'}`}>
                Image Quality Alert:
              </span>
              <span className="t-secondary block mt-1">{imageQuality.quality_warning}</span>
              <span className="text-[10px] t-dim mt-1 block">Blur Score: {imageQuality.blur_level.toFixed(1)}/100</span>
            </div>
          </div>
        </motion.div>
      )}

      {/* Confidence–morphology alignment */}
      {confidence != null && confidence < 0.5 && (
        <div className="p-3 rounded-xl text-xs leading-relaxed bg-amber-500/5 border border-amber-500/15">
          <div className="flex items-start gap-2">
            <FiAlertTriangle size={12} className="text-amber-400/70 mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold text-amber-500">Low Structural Alignment: </span>
              <span className="t-secondary">
                Model confidence ({(confidence * 100).toFixed(0)}%) indicates weak morphological alignment with known {species} track structure. Field validation recommended.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Heatmap insight — only when heatmap is active */}
      {showHeatmap && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 rounded-xl text-xs leading-relaxed bg-orange-500/5 border border-orange-500/10"
        >
          <div className="flex items-start gap-2">
            <FiEye size={12} className="text-orange-400/70 mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold text-orange-500">Gradient Activation Map: </span>
              <span className="t-secondary">
                Regions highlighted in red/orange indicate areas of highest gradient activation
                contributing to the classification decision. These typically correspond to
                morphologically significant structures — pad geometry, inter-digital spacing,
                and claw impressions. Blue/cool zones had negligible influence on the output class.
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}

/* ═══ Progressive Analysis Animation ═══ */
function AnalysisAnimation() {
  const steps = [
    { title: 'Uploading image', icon: FiUpload },
    { title: 'Running model inference', icon: FiCpu },
    { title: 'Generating gradient activation', icon: FiTarget },
    { title: 'Analyzing morphology', icon: GiPawPrint },
  ];

  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-16">
      {/* Rotating spinner with morphing icon */}
      <div className="relative w-24 h-24">
        {/* Outer rotating ring */}
        <motion.div
          className="absolute inset-0 border-3 border-transparent border-t-orange-500 border-r-orange-500/30 rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />

        {/* Middle rotating ring (slower) */}
        <motion.div
          className="absolute inset-2 border-2 border-transparent border-b-orange-400/50 rounded-full"
          animate={{ rotate: -360 }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        />

        {/* Center icon that morphs per step */}
        <motion.div
          key={activeStep}
          className="absolute inset-0 flex items-center justify-center"
          initial={{ opacity: 0, scale: 0.6, rotate: -30 }}
          animate={{ opacity: 1, scale: 1, rotate: 0 }}
          exit={{ opacity: 0, scale: 0.6, rotate: 30 }}
          transition={{ duration: 0.4 }}
        >
          {(() => {
            const StepIcon = steps[activeStep].icon;
            return <StepIcon className="text-orange-500 text-2xl" />;
          })()}
        </motion.div>
      </div>

      {/* Progressive step indicator */}
      <div className="mt-8 w-48 space-y-2">
        {steps.map((step, i) => {
          const isActive = i === activeStep;
          const isDone = i < activeStep;

          return (
            <motion.div
              key={step.title}
              initial={{ opacity: 0.4, x: -10 }}
              animate={{
                opacity: isActive ? 1 : isDone ? 0.6 : 0.3,
                x: 0,
                backgroundColor: isActive ? 'var(--bg-surface-2)' : 'transparent',
              }}
              transition={{ duration: 0.3 }}
              className="p-3 rounded-lg text-xs flex items-center gap-2"
            >
              <motion.div
                animate={{
                  scale: isActive ? [1, 1.2, 1] : 1,
                  opacity: isDone ? 1 : isActive ? 1 : 0.4,
                }}
                transition={{ duration: 0.6, repeat: isActive ? Infinity : 0 }}
              >
                {isDone ? (
                  <FiCheckCircle className="text-green-500" size={14} />
                ) : (
                  <div className={`w-3 h-3 rounded-full ${isActive ? 'bg-orange-500' : 'bg-gray-400'}`} />
                )}
              </motion.div>
              <span className={`font-medium ${isActive ? 'text-orange-500' : isDone ? 't-secondary' : 't-dim'}`}>
                {step.title}
              </span>
            </motion.div>
          );
        })}
      </div>

      {/* Overall progress message */}
      <motion.span
        key={activeStep}
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -5 }}
        className="mt-8 text-sm font-medium text-orange-500"
      >
        {steps[activeStep].title}...
      </motion.span>
    </div>
  );
}

/* ═══ Result Insight ═══ */
function ResultInsight({ result }) {
  let insight = null;
  let icon = FiHelpCircle;
  let bgColor = 'bg-blue-500/10 border border-blue-500/20 text-blue-500';

  if (result.confidence >= 0.9) {
    insight = 'High confidence prediction. This footprint clearly matches the identified species.';
    icon = FiCheckCircle;
    bgColor = 'bg-green-500/10 border border-green-500/20 text-green-500';
  } else if (result.confidence >= 0.7 && !result.is_unknown) {
    insight = 'Good match with moderate confidence. The footprint shows clear characteristics of the identified species.';
    icon = FiInfo;
    bgColor = 'bg-blue-500/10 border border-blue-500/20 text-blue-500';
  } else if (result.confidence >= 0.4 && !result.is_unknown) {
    insight = 'Moderate confidence. The footprint may belong to similar species. Consider additional context (location, habitat).';
    icon = FiAlertTriangle;
    bgColor = 'bg-yellow-500/10 border border-yellow-500/20 text-yellow-500';
  } else if (result.is_unknown) {
    insight = 'Below confidence threshold. The footprint may be degraded, belong to an unknown species, or show mixed characteristics.';
    icon = FiAlertTriangle;
    bgColor = 'bg-amber-500/10 border border-amber-500/20 text-amber-500';
  }

  const Icon = icon;
  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-xl text-sm flex gap-3 ${bgColor}`}>
      <Icon className="shrink-0 mt-0.5" size={16} />
      <div>
        <div className="font-semibold mb-1">Insight</div>
        <p className="text-xs leading-relaxed">{insight}</p>
      </div>
    </motion.div>
  );
}

export default function UploadPage() {
  const { dark } = useTheme();
  const { uploadState, setUploadState } = useAppState();

  // Destructure from global state
  const { file, preview, result, loading, error, showHeatmap, isCameraActive } = uploadState;

  const [dragActive, setDragActive] = useState(false);

  // Helper to update global state partially
  const updateState = (updates) => setUploadState(prev => ({ ...prev, ...updates }));

  // GPS Location state
  const [location, setLocation] = useState(null);

  // Background Videos mapping
  const SPECIES_VIDEOS = {
    tiger: "https://res.cloudinary.com/demo/video/upload/tiger.mp4",
    elephant: "https://res.cloudinary.com/demo/video/upload/elephants.mp4",
    leopard: "https://cdn.pixabay.com/video/2021/08/11/84687-586718423_large.mp4", // Leopard
    deer: "https://cdn.pixabay.com/video/2019/04/23/22934-331668478_large.mp4",  // Deer in forest
    wolf: "https://cdn.pixabay.com/video/2020/03/17/33827-399088686_large.mp4",  // Wolf in snow
    default: "https://cdn.pixabay.com/video/2020/07/22/45366-443144893_large.mp4"
  };

  // Attempt to get GPS on component mount
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        },
        (err) => console.log('Geolocation skipped or denied', err)
      );
    }
  }, []);

  const handleFile = useCallback((f) => {
    if (!f) return;

    // reset previous result/error when new file selected
    updateState({ file: f, result: null, error: null });

    const reader = new FileReader();
    reader.onload = (e) => updateState({ preview: e.target.result });
    reader.readAsDataURL(f);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const handleSubmit = async () => {
    if (!file) return;
    updateState({ loading: true, error: null });
    try {
      // Create FormData
      const formData = new FormData();
      formData.append('file', file);

      // NOTE: We are NOT sending GPS coordinates by default anymore. 
      // The backend geo-filter will zero-out probabilities for animals 
      // that don't live in the user's location (e.g. elephants in North America).
      // Since users test with images from the internet, this causes "incorrect" predictions.
      /*
      if (location) {
        formData.append('latitude', location.lat);
        formData.append('longitude', location.lng);
      }
      */

      const resData = await api.predict(file, null); // Skip location parameter in api wrapper too
      updateState({ result: resData.data });
    } catch (err) {
      updateState({ error: err.message || 'Prediction failed' });
    } finally {
      updateState({ loading: false });
    }
  };

  const reset = () => {
    setUploadState({
      file: null,
      preview: null,
      result: null,
      loading: false,
      error: null,
      showHeatmap: false,
      isCameraActive: false
    });
  };

  const cardClass = 'surface-card-lg glass-glow transition-all';

  // Confidence-coded glow class for the result card
  const resultGlowClass = useMemo(() => {
    if (!result) return '';
    if (result.is_unknown) return 'confidence-glow-amber';
    const pct = result.confidence * 100;
    if (pct >= 80) return 'confidence-glow-green';
    if (pct >= 60) return 'confidence-glow-blue';
    if (pct >= 50) return 'confidence-glow-orange';
    return 'confidence-glow-red';
  }, [result]);

  return (
    <>
      {/* Dynamic Background Video */}
      <AnimatePresence mode="wait">
        {result && !result.is_unknown && (
          <motion.div
            key={result.species}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.5, ease: "easeInOut" }}
            className="fixed inset-0 z-0 overflow-hidden bg-black"
          >
            <video
              autoPlay
              loop
              muted
              playsInline
              className="absolute min-w-full min-h-full object-cover opacity-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
            >
              <source src={SPECIES_VIDEOS[result.species?.toLowerCase()] || SPECIES_VIDEOS.default} type="video/mp4" />
            </video>
            {/* Elegant dark overlays to ensure the app UI remains fully readable */}
            <div className="absolute inset-0 bg-black/60" />
            <div className="absolute inset-0 bg-gradient-to-t from-[var(--bg-card)] via-[#0a0a0a]/50 to-transparent" />
            <div className="absolute inset-0 bg-gradient-to-r from-[#0a0a0a] via-transparent to-[#0a0a0a] opacity-90" />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="max-w-5xl mx-auto space-y-6 relative z-10 transition-colors duration-1000">
        <div className="flex items-center gap-3 mb-2">
          <motion.div whileHover={{ rotate: 10 }} className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg transition-colors duration-1000 ${result ? 'bg-white/10 backdrop-blur-md shadow-white/5' : 'bg-gradient-to-br from-orange-500 to-amber-500 shadow-orange-500/20'}`}>
            <FiUpload className="text-white text-lg" />
          </motion.div>
          <div>
            <h1 className={`text-2xl font-bold transition-colors duration-1000 ${result ? 'text-white drop-shadow-lg' : 'neon-heading'}`}>Upload Footprint</h1>
            <p className={`text-sm transition-colors duration-1000 ${result ? 'text-white/80' : 't-tertiary'}`}>Identify species with calibrated AI confidence</p>
          </div>
        </div>

        {/* Drop zone / Camera Toggle */}
        {!preview && !isCameraActive && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`${cardClass} p-12 text-center ${dragActive ? 'ring-2 ring-orange-500 border-orange-500 bg-orange-500/5' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
          >
            <motion.div animate={dragActive ? { scale: 1.1 } : { scale: 1 }} className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-orange-500/10 to-amber-500/10 mb-6">
              <FiImage className="text-4xl text-orange-500" />
            </motion.div>
            <p className="text-xl font-semibold mb-2">Drop footprint image here</p>
            <p className="text-sm t-tertiary mb-8">or choose an upload method below</p>

            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <button
                onClick={() => document.getElementById('file-input').click()}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-lg shadow-orange-500/20 hover:scale-105 active:scale-95 transition-all"
              >
                <FiUpload /> Browse Files
              </button>
              <button
                onClick={() => updateState({ isCameraActive: true })}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold border border-orange-500/30 text-orange-500 bg-orange-500/5 hover:bg-orange-500/10 hover:scale-105 active:scale-95 transition-all"
              >
                <FiCamera /> Use Camera
              </button>
            </div>
            <input id="file-input" type="file" accept="image/*" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
          </motion.div>
        )}

        {/* Camera Capture UI */}
        {!preview && isCameraActive && (
          <CameraCapture
            onCapture={(f) => {
              updateState({ isCameraActive: false });
              handleFile(f);
            }}
            onCancel={() => updateState({ isCameraActive: false })}
          />
        )}

        {/* Preview + results */}
        {preview && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`${cardClass} p-6`}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'var(--bg-surface-2)' }}>
                  <FiImage className="text-orange-500" />
                </div>
                <span className="font-medium truncate max-w-xs text-sm">{file?.name}</span>
                <span className="text-xs px-2 py-0.5 rounded-full t-tertiary" style={{ background: 'var(--bg-surface-2)' }}>
                  {(file?.size / 1024).toFixed(0)} KB
                </span>
              </div>
              <button onClick={reset} className="p-2 rounded-xl transition surface-hover">
                <FiX />
              </button>
            </div>

            <div className="flex flex-col lg:flex-row gap-6">
              {/* Image */}
              <div className="flex-1">
                <div className="rounded-xl overflow-hidden min-h-[320px]" style={{ background: 'var(--bg-surface-2)' }}>
                  <img
                    src={showHeatmap && result?.heatmap ? `data:image/png;base64,${result.heatmap}` : preview}
                    alt="preview"
                    className="w-full max-h-96 object-contain"
                  />
                </div>
                {result?.heatmap && (
                  <button onClick={() => updateState({ showHeatmap: !showHeatmap })} className="mt-3 text-sm flex items-center gap-1.5 text-orange-500 hover:text-orange-400 font-medium transition">
                    <FiEye size={14} /> {showHeatmap ? 'Show Original Image' : 'Show Grad-CAM Heatmap'}
                  </button>
                )}

                <div className="border-t border-white/5 my-4" />

                {/* Track Morphology Analysis */}
                {result && !result.is_unknown && (
                  <TrackMorphologyPanel species={result.species} showHeatmap={showHeatmap} confidence={result.confidence} imageQuality={result.image_quality} />
                )}
              </div>

              {/* Results */}
              <div className="flex-1 space-y-4">
                {!result && !loading && (
                  <motion.button whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }}
                    onClick={handleSubmit} disabled={loading}
                    className="w-full py-4 bg-gradient-to-r from-orange-500 to-amber-500 text-white font-bold rounded-2xl shadow-lg shadow-orange-500/20 hover:shadow-xl hover:shadow-orange-500/30 transition-all text-lg">
                    <FiActivity className="inline mr-2" /> Identify Species
                  </motion.button>
                )}

                {loading && (
                  <AnalysisAnimation />
                )}

                {error && (
                  <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-sm">{error}</div>
                )}

                <AnimatePresence>
                  {result && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                      {/* Main prediction — confidence-coded glow card */}
                      <div className={`relative p-5 rounded-2xl overflow-hidden ${resultGlowClass} ${result.is_unknown
                        ? 'bg-gradient-to-br from-amber-500/10 to-yellow-500/5 border border-amber-500/20'
                        : ''}`}
                        style={result.is_unknown ? {} : { background: 'var(--bg-card)' }}>

                        <div className="flex items-start gap-4">
                          {/* Confidence Ring — cinematic gauge */}
                          <motion.div
                            initial={{ opacity: 0, scale: 0.6 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.3, type: 'spring', stiffness: 180 }}
                            className="flex-shrink-0 confidence-orb"
                          >
                            <ConfidenceRing
                              confidence={result.confidence}
                              size={100}
                              strokeWidth={7}
                              isUnknown={result.is_unknown}
                            />
                          </motion.div>

                          {/* Species info */}
                          <div className="flex-1 min-w-0">
                            {result.is_unknown ? (
                              <>
                                <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}
                                  className="text-xs uppercase tracking-wider text-amber-500 font-semibold flex items-center gap-1.5">
                                  <FiAlertTriangle size={12} /> Species Not Identified
                                </motion.div>
                                <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }}
                                  className="text-2xl font-extrabold text-amber-600 dark:text-amber-400 mt-1">Unknown Species</motion.div>
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
                                  className="text-xs mt-1 t-secondary">
                                  Closest match: <span className="capitalize font-semibold text-amber-500">{result.raw_class}</span>
                                </motion.div>
                              </>
                            ) : (
                              <>
                                <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}
                                  className="text-xs uppercase tracking-wider text-gray-500 font-semibold flex items-center gap-1.5">
                                  <FiTarget size={12} /> Predicted Species
                                </motion.div>
                                <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }}
                                  className="text-2xl font-extrabold capitalize mt-1">{result.species}</motion.div>
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
                                  className="flex items-center gap-2 mt-2 flex-wrap">
                                  <FiCheckCircle className="text-green-500" size={14} />
                                  <span className="text-xs font-medium text-green-500">Identified with {(result.confidence * 100).toFixed(1)}% confidence</span>
                                </motion.div>
                                {/* Model + TTA badges */}
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }}
                                  className="flex items-center gap-2 mt-2 flex-wrap">
                                  {result.model_version && (
                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-orange-500/15 text-orange-500 border border-orange-500/20">
                                      <FiCpu size={10} /> {result.model_version}
                                    </span>
                                  )}
                                  {result.tta_enabled && (
                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-blue-500/15 text-blue-500 border border-blue-500/20">
                                      TTA
                                    </span>
                                  )}
                                </motion.div>

                                {/* ── V2 Reliability Verdict ── */}
                                <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }}
                                  className="mt-3"
                                >
                                  {(() => {
                                    const conf = result.quality_adjusted_confidence || result.confidence;
                                    const isReview = result.needs_review || result.requires_field_validation;
                                    const reliability = conf >= 0.75 ? 'High'
                                      : conf >= 0.6 ? 'Moderate'
                                        : conf >= 0.4 ? 'Low' : 'Insufficient';
                                    const reliabilityColor = conf >= 0.75 ? 'text-green-400 bg-green-500/10 border-green-500/20'
                                      : conf >= 0.6 ? 'text-blue-400 bg-blue-500/10 border-blue-500/20'
                                        : conf >= 0.4 ? 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
                                          : 'text-red-400 bg-red-500/10 border-red-500/20';
                                    const verdictIcon = isReview ? FiAlertTriangle : FiCheckCircle;
                                    const VerdictIcon = verdictIcon;

                                    return (
                                      <div className={`flex items-center gap-2 p-2.5 rounded-xl border text-xs font-semibold ${reliabilityColor}`}>
                                        <VerdictIcon size={14} />
                                        <span>{reliability} Reliability</span>
                                        <span className="mx-1 opacity-30">|</span>
                                        <span className="font-normal">
                                          {isReview
                                            ? 'Review Recommended — field validation suggested'
                                            : 'AI Confidence Verified'}
                                        </span>
                                      </div>
                                    );
                                  })()}
                                </motion.div>
                              </>
                            )}
                          </div>
                        </div>

                        {result.is_unknown && (
                          <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}
                            className="mt-4 p-3 rounded-xl text-xs bg-amber-500/10 text-amber-500">
                            Confidence below 40% threshold. This footprint may belong to a species not in our database (deer, elephant, leopard, tiger, wolf) or the image may not be a clear footprint.
                          </motion.div>
                        )}

                        {/* Confidence bar */}
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
                          className="mt-4">
                          <div className="flex justify-between text-sm mb-1.5">
                            <span className="t-secondary">Confidence</span>
                            <span className={`font-mono font-bold ${result.is_unknown ? 'text-amber-500' : 'text-orange-500'}`}>{(result.confidence * 100).toFixed(1)}%</span>
                          </div>
                          <div className="h-3 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-2)' }}>
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${result.confidence * 100}%` }}
                              transition={{ duration: 1.2, ease: [0.25, 0.46, 0.45, 0.94] }}
                              className={`h-full rounded-full ${result.is_unknown ? 'bg-gradient-to-r from-amber-500 to-yellow-500' : 'bg-gradient-to-r from-orange-500 to-amber-500'}`} />
                          </div>
                          {/* Confidence level label */}
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 1.25 }}
                            className={`text-xs mt-2 font-medium flex items-center gap-1 ${result.confidence >= 0.9 ? 'text-green-500' :
                              result.confidence >= 0.7 ? 'text-blue-500' :
                                result.confidence >= 0.4 ? 'text-yellow-500' : 'text-orange-500'
                              }`}>
                            {result.confidence >= 0.9 ? '✓ Very High Confidence' :
                              result.confidence >= 0.7 ? '→ Good Confidence' :
                                result.confidence >= 0.4 ? '⚠ Moderate Confidence' : '? Low Confidence'}
                          </motion.div>
                        </motion.div>

                        {/* Entropy info */}
                        {result.entropy !== undefined && (
                          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.4 }}
                            className={`mt-3 pt-3 border-t text-xs space-y-1.5 b-subtle`}>
                            <div className="flex justify-between">
                              <span className="text-gray-500 uppercase tracking-wider font-semibold flex items-center gap-1"><FiCpu size={11} /> Model Uncertainty</span>
                              <span className={`font-bold ${result.entropy_ratio > 0.85 ? 'text-red-500' : result.entropy_ratio > 0.5 ? 'text-yellow-500' : 'text-green-500'}`}>
                                {result.entropy_ratio > 0.85 ? 'High' : result.entropy_ratio > 0.5 ? 'Moderate' : 'Low'} ({(result.entropy_ratio * 100).toFixed(0)}%)
                              </span>
                            </div>
                            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-2)' }}>
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${result.entropy_ratio * 100}%` }}
                                transition={{ duration: 1, delay: 1.4 }}
                                className={`h-full rounded-full ${result.entropy_ratio > 0.85 ? 'bg-red-500' : result.entropy_ratio > 0.5 ? 'bg-yellow-500' : 'bg-green-500'}`} />
                            </div>
                            <div className="flex gap-3 text-gray-500 font-mono text-[10px] mt-2">
                              <span title="Shannon Entropy">H={result.entropy?.toFixed(3)}</span>
                              <span title="Temperature scaling">T={result.temperature || 1}</span>
                              <span title="Classification threshold">θ=0.4</span>
                            </div>
                            <motion.div
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              transition={{ delay: 1.5 }}
                              className={`text-[11px] leading-relaxed mt-2 p-2 rounded`} style={{ background: 'var(--bg-surface-2)' }}>
                              {result.entropy_ratio > 0.85 ? 'The model shows high uncertainty. Multiple species have similar confidence scores. Results should be verified or additional context considered.' :
                                result.entropy_ratio > 0.5 ? 'The model shows moderate uncertainty. While a prediction is made, other species have notable probability. Context awareness is recommended.' :
                                  'The model is confident. The predicted species has significantly higher probability than alternatives.'}
                            </motion.div>
                          </motion.div>
                        )}
                      </div>

                      {/* ── AI CONSENSUS VALIDATION PANEL ── */}
                      {result.consensus && (
                        <motion.div
                          initial={{ opacity: 0, y: 12 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.95, duration: 0.4 }}
                          className={`p-5 rounded-2xl border overflow-hidden relative ${result.consensus.verdict_level === 'verified' ? 'border-green-500/25 bg-green-500/[0.04]' :
                            result.consensus.verdict_level === 'consensus' ? 'border-blue-500/25 bg-blue-500/[0.04]' :
                              result.consensus.verdict_level === 'ambiguous' ? 'border-red-500/25 bg-red-500/[0.04]' :
                                result.consensus.verdict_level === 'weak' ? 'border-yellow-500/25 bg-yellow-500/[0.04]' :
                                  'border-purple-500/25 bg-purple-500/[0.04]'
                            }`}
                        >
                          {/* Background accent */}
                          <div className={`absolute top-0 right-0 w-24 h-24 rounded-bl-full opacity-[0.06] ${result.consensus.verdict_level === 'verified' ? 'bg-green-500' :
                            result.consensus.verdict_level === 'consensus' ? 'bg-blue-500' :
                              result.consensus.verdict_level === 'ambiguous' ? 'bg-red-500' :
                                'bg-yellow-500'
                            }`} />

                          {/* Header */}
                          <div className="flex items-center gap-2 mb-4">
                            <div className={`w-6 h-6 rounded-md flex items-center justify-center ${result.consensus.verdict_level === 'verified' ? 'bg-green-500/15' :
                              result.consensus.verdict_level === 'consensus' ? 'bg-blue-500/15' :
                                result.consensus.verdict_level === 'ambiguous' ? 'bg-red-500/15' :
                                  'bg-yellow-500/15'
                              }`}>
                              {result.consensus.agreement
                                ? <FiCheckCircle size={13} className={result.consensus.verdict_level === 'verified' ? 'text-green-400' : 'text-blue-400'} />
                                : <FiAlertTriangle size={13} className="text-red-400" />
                              }
                            </div>
                            <span className="text-xs font-bold uppercase tracking-wider t-tertiary">AI Consensus Validation</span>
                            <span className={`ml-auto px-2 py-0.5 rounded-full text-[10px] font-bold ${result.consensus.verdict_level === 'verified' ? 'bg-green-500/15 text-green-400' :
                              result.consensus.verdict_level === 'consensus' ? 'bg-blue-500/15 text-blue-400' :
                                result.consensus.verdict_level === 'ambiguous' ? 'bg-red-500/15 text-red-400' :
                                  result.consensus.verdict_level === 'weak' ? 'bg-yellow-500/15 text-yellow-400' :
                                    'bg-purple-500/15 text-purple-400'
                              }`}>
                              {result.consensus.verdict}
                            </span>
                          </div>

                          {/* Dual model comparison */}
                          <div className="grid grid-cols-2 gap-3 mb-4">
                            {/* Primary Model */}
                            <div className="p-3 rounded-xl surface-inset">
                              <div className="text-[10px] t-dim uppercase tracking-wider font-semibold mb-1.5">Primary — TTA Path</div>
                              <div className="text-sm font-bold capitalize">{result.consensus.primary_prediction}</div>
                              <div className="flex items-center gap-2 mt-2">
                                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-2)' }}>
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${result.consensus.primary_confidence * 100}%` }}
                                    transition={{ delay: 1.1, duration: 0.8 }}
                                    className="h-full rounded-full bg-gradient-to-r from-orange-500 to-amber-500"
                                  />
                                </div>
                                <span className="text-xs font-mono font-bold text-orange-500">{(result.consensus.primary_confidence * 100).toFixed(1)}%</span>
                              </div>
                            </div>

                            {/* Second Opinion */}
                            <div className="p-3 rounded-xl surface-inset">
                              <div className="text-[10px] t-dim uppercase tracking-wider font-semibold mb-1.5">Second Opinion</div>
                              <div className={`text-sm font-bold capitalize ${!result.consensus.agreement ? 'text-red-400' : ''}`}>
                                {result.consensus.second_opinion_prediction}
                              </div>
                              <div className="flex items-center gap-2 mt-2">
                                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-2)' }}>
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${result.consensus.second_opinion_confidence * 100}%` }}
                                    transition={{ delay: 1.2, duration: 0.8 }}
                                    className={`h-full rounded-full ${result.consensus.agreement ? 'bg-gradient-to-r from-blue-500 to-cyan-500' : 'bg-gradient-to-r from-red-500 to-pink-500'}`}
                                  />
                                </div>
                                <span className={`text-xs font-mono font-bold ${result.consensus.agreement ? 'text-blue-500' : 'text-red-400'}`}>
                                  {(result.consensus.second_opinion_confidence * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Metrics row */}
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="p-2 rounded-lg surface-inset">
                              <div className="text-[9px] t-dim uppercase tracking-wider">Agreement</div>
                              <div className={`text-sm font-bold mt-1 ${result.consensus.agreement ? 'text-green-400' : 'text-red-400'}`}>
                                {result.consensus.agreement ? 'Yes' : 'No'}
                              </div>
                            </div>
                            <div className="p-2 rounded-lg surface-inset">
                              <div className="text-[9px] t-dim uppercase tracking-wider">Disagreement</div>
                              <div className={`text-sm font-bold mt-1 ${result.consensus.disagreement_score > 0.15 ? 'text-red-400' : result.consensus.disagreement_score > 0.05 ? 'text-yellow-400' : 'text-green-400'}`}>
                                {(result.consensus.disagreement_score * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="p-2 rounded-lg surface-inset">
                              <div className="text-[9px] t-dim uppercase tracking-wider">Stability</div>
                              <div className={`text-sm font-bold mt-1 ${result.consensus.confidence_stable ? 'text-green-400' : 'text-yellow-400'}`}>
                                {result.consensus.confidence_stable ? 'Stable' : 'Unstable'}
                              </div>
                            </div>
                          </div>

                          {/* Alternative warning */}
                          {result.consensus.alternative && (
                            <motion.div
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              transition={{ delay: 1.4 }}
                              className="mt-3 p-3 rounded-xl bg-red-500/[0.06] border border-red-500/15 text-xs"
                            >
                              <div className="flex items-start gap-2">
                                <FiAlertTriangle size={12} className="text-red-400 mt-0.5 shrink-0" />
                                <div>
                                  <span className="font-semibold text-red-400">⚠ AI Uncertainty Detected: </span>
                                  <span className="t-secondary">
                                    Second opinion model suggests <span className="font-semibold capitalize text-red-400">{result.consensus.alternative.species}</span> ({(result.consensus.alternative.confidence * 100).toFixed(1)}%).
                                    Species may be visually similar. Manual verification recommended.
                                  </span>
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </motion.div>
                      )}

                      {/* Top predictions — cinematic stagger reveal */}
                      {result.top3 && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.1 }}>
                          <h3 className="text-xs font-semibold mb-3 uppercase tracking-wider flex items-center gap-2 t-tertiary">
                            <FiActivity size={12} /> Probability Distribution
                          </h3>
                          <div className="space-y-2">
                            {result.top3.map((item, i) => {
                              const isTop = i === 0;
                              const barColor = isTop
                                ? (result.is_unknown ? 'bg-gradient-to-r from-amber-500 to-yellow-500' : 'bg-gradient-to-r from-orange-500 to-amber-500')
                                : '';
                              const barStyle = isTop ? {} : { background: 'var(--text-dim)' };
                              return (
                                <motion.div key={item.class} initial={{ opacity: 0, x: -15 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 1.2 + i * 0.12, type: 'spring', stiffness: 200 }}
                                  className={`flex items-center gap-3 p-3 rounded-xl transition-all group ${isTop ? 'bg-orange-500/5 border border-orange-500/10' : 'surface-inset surface-hover'}`}>
                                  <span className={`text-xs font-bold w-7 h-7 rounded-lg flex items-center justify-center ${isTop ? 'bg-gradient-to-br from-orange-500 to-amber-500 text-white shadow-sm' : 'surface-inset t-secondary'}`}>
                                    #{i + 1}
                                  </span>
                                  <span className={`capitalize flex-1 font-medium text-sm ${isTop ? 'text-orange-500' : ''}`}>{item.class}</span>
                                  <span className={`font-mono text-sm font-semibold tabular-nums ${isTop ? 'text-orange-500' : ''}`}>{(item.confidence * 100).toFixed(1)}%</span>
                                  <div className="w-24 h-2.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-2)' }}>
                                    <motion.div initial={{ width: 0 }} animate={{ width: `${item.confidence * 100}%` }} transition={{ duration: 0.8, delay: 1.2 + i * 0.12 }}
                                      className={`h-full rounded-full ${barColor}`} style={barStyle} />
                                  </div>
                                </motion.div>
                              );
                            })}
                          </div>
                        </motion.div>
                      )}

                      {/* Animal info */}
                      {result.animal_info?.description && (
                        <div className="p-4 rounded-xl text-sm bg-blue-500/10 border border-blue-500/20 text-blue-500">
                          <div className="font-semibold mb-1">About this species</div>
                          {result.animal_info.description}
                        </div>
                      )}

                      {/* Actionable Insight */}
                      <ResultInsight result={result} />

                      {/* Download PDF Report */}
                      <motion.button whileHover={{ scale: 1.02, y: -2, boxShadow: '0 8px 30px rgba(249,115,22,0.3)' }} whileTap={{ scale: 0.98 }}
                        onClick={async () => {
                          try {
                            const res = await api.generateReport(file || new File([await (await fetch(preview)).blob()], 'footprint.jpg'));
                            const url = URL.createObjectURL(res.data);
                            const a = document.createElement('a');
                            a.href = url; a.download = `wildtrack_report.pdf`; a.click();
                            URL.revokeObjectURL(url);
                          } catch (e) { /* report generation failed */ }
                        }}
                        className="w-full py-3.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-lg shadow-orange-500/20 flex items-center justify-center gap-2 transition-all">
                        <FiDownload size={16} /> Download PDF Report
                      </motion.button>

                      <motion.button whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                        onClick={reset} className="w-full py-3 rounded-xl text-sm font-medium border transition b-primary surface-hover">
                        Upload Another Footprint
                      </motion.button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </>
  );
}
