import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { FiLayers, FiUpload, FiPercent, FiArrowRight, FiCheck, FiX, FiInfo, FiAlertTriangle } from 'react-icons/fi';
import { GiPawPrint, GiFootprint, GiClawSlashes } from 'react-icons/gi';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

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
  },
  leopard: {
    toeCount: '4',
    clawMarks: 'Absent — retractable claws',
    heelPad: 'Tri-lobed posterior edge',
    symmetry: 'Round, proportional',
    family: 'Felidae',
    trackWidth: '7–10 cm',
    gait: 'Direct-register walk',
  },
  elephant: {
    toeCount: 'N/A — round pad',
    clawMarks: 'None',
    heelPad: 'Circular, cracked-skin texture',
    symmetry: 'Radially symmetric',
    family: 'Elephantidae',
    trackWidth: '40–50 cm',
    gait: 'Ambling — overlapping front-rear',
  },
  deer: {
    toeCount: '2 — cloven hoof',
    clawMarks: 'Dewclaws in soft substrate',
    heelPad: 'Heart-shaped, pointed tips',
    symmetry: 'Bilaterally symmetric',
    family: 'Cervidae',
    trackWidth: '5–9 cm',
    gait: 'Walk / bounding',
  },
  wolf: {
    toeCount: '4',
    clawMarks: 'Present — non-retractable',
    heelPad: 'Oval, X-pattern between toes',
    symmetry: 'Oval, elongated',
    family: 'Canidae',
    trackWidth: '10–13 cm',
    gait: 'Direct-register trot',
  },
};

/* ═══ Morphological Contrast Panel ═══ */
function MorphologicalContrast({ result1, result2 }) {
  if (!result1 || !result2 || result1.is_unknown || result2.is_unknown) return null;

  const morph1 = TRACK_MORPHOLOGY[result1.species?.toLowerCase()];
  const morph2 = TRACK_MORPHOLOGY[result2.species?.toLowerCase()];
  if (!morph1 || !morph2) return null;

  const isSameSpecies = result1.species === result2.species;
  const traits = ['toeCount', 'clawMarks', 'heelPad', 'symmetry', 'family', 'trackWidth', 'gait'];
  const traitLabels = ['Toe Count', 'Claw Marks', 'Heel Pad', 'Symmetry', 'Family', 'Track Width', 'Gait'];

  // Calculate morphological similarity (count matching traits / total traits)
  const matchingTraits = traits.filter(t => morph1[t] === morph2[t]).length;
  const morphSimilarity = (matchingTraits / traits.length) * 100;

  // Confidence contrast explanation with quality adjustment
  const confDiff = Math.abs((result1.quality_adjusted_confidence || result1.confidence) - (result2.quality_adjusted_confidence || result2.confidence));
  const cond1 = result1.quality_adjusted_confidence || result1.confidence;
  const cond2 = result2.quality_adjusted_confidence || result2.confidence;
  const confDiffPercent = confDiff * 100;
  
  let confidenceInsight = '';
  if (isSameSpecies) {
    if (confDiffPercent < 5) {
      confidenceInsight = `Excellent alignment: Both images show ${result1.species} with consistent confidence (${confDiffPercent.toFixed(1)}% difference).`;
    } else if (confDiffPercent < 15) {
      confidenceInsight = `Minor variance: ${result1.species} identified, but image quality affects confidence slightly (${confDiffPercent.toFixed(1)}% difference).`;
    } else {
      confidenceInsight = `Significant variance: Same species detected, but confidence differs notably (${confDiffPercent.toFixed(1)}%). One image may have poorer clarity or angle.`;
    }
  } else {
    confidenceInsight = `Different species detected (${confDiffPercent.toFixed(1)}% confidence delta). Verify morphological traits visually to confirm structural difference.`;
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      {/* Species Match Indicator */}
      <div className={`p-4 rounded-xl border ${isSameSpecies 
        ? 'bg-green-500/5 border-green-500/20' 
        : 'bg-amber-500/5 border-amber-500/20'}`}>
        <div className="flex items-start gap-3">
          {isSameSpecies ? (
            <FiCheck className="text-green-500 mt-1 shrink-0" size={16} />
          ) : (
            <FiAlertTriangle className="text-amber-500 mt-1 shrink-0" size={16} />
          )}
          <div>
            <div className={`font-semibold ${isSameSpecies ? 'text-green-500' : 'text-amber-500'}`}>
              {isSameSpecies ? 'Same Species Identified' : 'Different Species Detected'}
            </div>
            <div className="text-xs mt-1 t-secondary">{confidenceInsight}</div>
          </div>
        </div>
      </div>

      {/* Morphological Similarity Score */}
      <div className={`p-4 rounded-xl border ${morphSimilarity >= 71 ? 'bg-green-500/5 border-green-500/20' : morphSimilarity >= 43 ? 'bg-yellow-500/5 border-yellow-500/20' : 'bg-red-500/5 border-red-500/20'}`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider t-tertiary mb-1">Morphological Alignment</div>
            <div className="text-sm t-secondary">{matchingTraits} of {traits.length} traits match</div>
          </div>
          <div className="text-right">
            <div className={`text-2xl font-extrabold ${morphSimilarity >= 71 ? 'text-green-500' : morphSimilarity >= 43 ? 'text-yellow-500' : 'text-red-500'}`}>
              {morphSimilarity.toFixed(0)}%
            </div>
            <div className="text-xs t-tertiary">{morphSimilarity >= 71 ? 'Highly aligned' : morphSimilarity >= 43 ? 'Partially aligned' : 'Poorly aligned'}</div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Morphology Comparison */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider t-tertiary flex items-center gap-2">
          <FiLayers size={12} /> Morphological Contrast        </h3>
        
        {traits.map((trait, i) => {
          const val1 = morph1[trait];
          const val2 = morph2[trait];
          const matches = val1 === val2;
          
          return (
            <div key={trait} className="grid grid-cols-3 gap-3 items-start">
              {/* Left footprint */}
              <div className={`p-3 rounded-lg text-xs border ${matches && !isSameSpecies ? 'border-orange-500/20 bg-orange-500/5' : 'surface-inset'}`}>
                <div className="text-[10px] uppercase tracking-wider t-tertiary font-medium mb-1">{traitLabels[i]}</div>
                <div className="text-sm font-semibold leading-snug">{val1}</div>
              </div>

              {/* Match indicator */}
              <div className="flex justify-center items-start pt-1">
                {matches ? (
                  <FiCheck className="text-green-500" size={14} />
                ) : (
                  <FiX className="text-amber-500" size={14} />
                )}
              </div>

              {/* Right footprint */}
              <div className={`p-3 rounded-lg text-xs border ${matches && !isSameSpecies ? 'border-orange-500/20 bg-orange-500/5' : 'surface-inset'}`}>
                <div className="text-[10px] uppercase tracking-wider t-tertiary font-medium mb-1">{traitLabels[i]}</div>
                <div className="text-sm font-semibold leading-snug">{val2}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Confidence Difference Analysis */}
      {!isSameSpecies && (
        <div className="p-4 rounded-xl text-xs leading-relaxed border bg-blue-500/5 border-blue-500/15">
          <div className="flex items-start gap-2">
            <FiInfo className="text-blue-500 mt-0.5 shrink-0" size={12} />
            <div>
              <span className="font-semibold text-blue-500">Structural Misalignment: </span>
              <span className="t-secondary">
                The model detected structurally distinct footprints. This may indicate genuine species difference,
                or preprocessing artifacts in one image. Compare toe spacing, pad geometry, and claw impressions visually.
              </span>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default function ComparePage() {
  const { dark } = useTheme();
  const [images, setImages] = useState([null, null]);
  const [previews, setPreviews] = useState([null, null]);
  const [results, setResults] = useState([null, null]);
  const [similarity, setSimilarity] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFile = useCallback((index, file) => {
    if (!file) return;
    const newImages = [...images];
    const newPreviews = [...previews];
    newImages[index] = file;
    setImages(newImages);
    const reader = new FileReader();
    reader.onload = (e) => { newPreviews[index] = e.target.result; setPreviews([...newPreviews]); };
    reader.readAsDataURL(file);
    setSimilarity(null);
    setResults([null, null]);
  }, [images, previews]);

  const handleCompare = async () => {
    if (!images[0] || !images[1]) return;
    setLoading(true);
    try {
      const [r1, r2] = await Promise.all([api.predict(images[0]), api.predict(images[1])]);
      setResults([r1.data, r2.data]);
      if (r1.data.embedding && r2.data.embedding) {
        const a = r1.data.embedding, b = r2.data.embedding;
        const dot = a.reduce((sum, v, i) => sum + v * b[i], 0);
        const magA = Math.sqrt(a.reduce((s, v) => s + v * v, 0));
        const magB = Math.sqrt(b.reduce((s, v) => s + v * v, 0));
        setSimilarity(dot / (magA * magB));
      } else {
        const same = r1.data.species === r2.data.species;
        setSimilarity(same ? Math.min(r1.data.confidence, r2.data.confidence) : 0);
      }
    } catch (err) { console.error('Compare error:', err); }
    finally { setLoading(false); }
  };

  const cardClass = 'surface-card-lg glass-glow';

  const DropZone = ({ index }) => (
    <div
      className={`${cardClass} p-6 text-center cursor-pointer hover:shadow-md transition-all min-h-[300px] flex flex-col items-center justify-center`}
      onClick={() => document.getElementById(`compare-file-${index}`).click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => { e.preventDefault(); handleFile(index, e.dataTransfer.files?.[0]); }}
    >
      {previews[index] ? (
        <div className="space-y-3 w-full">
          <img src={previews[index]} alt={`Image ${index + 1}`} className="rounded-xl max-h-52 mx-auto object-contain" />
          {results[index] && (
            <div className={`p-4 rounded-xl ${results[index].is_unknown
              ? 'bg-amber-500/10 border border-amber-500/20'
              : 'surface-inset'}`}>
              {results[index].is_unknown ? (
                <>
                  <div className="text-xs text-amber-500 mb-1 font-medium">Species Not Identified</div>
                  <div className="font-extrabold text-lg text-amber-600 dark:text-amber-400">Unknown</div>
                  <div className="text-xs text-gray-500">Closest: <span className="capitalize">{results[index].raw_class}</span></div>
                </>
              ) : (
                <>
                  <div className="text-xs text-gray-500 mb-1">Predicted Species</div>
                  <div className="font-extrabold capitalize text-lg">{results[index].species}</div>
                </>
              )}
              <div className={`text-sm font-mono font-bold ${results[index].is_unknown ? 'text-amber-500' : 'text-orange-500'}`}>{(results[index].confidence * 100).toFixed(1)}%</div>
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'var(--bg-surface-2)' }}>
            <FiUpload className="text-2xl text-gray-400" />
          </div>
          <p className="font-semibold">Image {index + 1}</p>
          <p className="text-xs mt-1 t-dim">Drop or click to upload</p>
        </>
      )}
      <input id={`compare-file-${index}`} type="file" accept="image/*" className="hidden" onChange={(e) => handleFile(index, e.target.files?.[0])} />
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center">
          <FiLayers className="text-white text-lg" />
        </div>
        <div>
          <h1 className="text-2xl font-bold neon-heading">Compare Footprints</h1>
          <p className="text-sm t-tertiary">Side-by-side footprint identification comparison</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DropZone index={0} />
        <DropZone index={1} />
      </div>

      <div className="text-center">
        <button onClick={handleCompare} disabled={!images[0] || !images[1] || loading} className="px-10 py-4 bg-gradient-to-r from-orange-500 to-amber-500 text-white font-bold rounded-2xl hover:shadow-xl hover:shadow-orange-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-lg">
          {loading ? (
            <span className="flex items-center gap-2"><div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" /> Comparing...</span>
          ) : (<><FiPercent className="inline mr-2" /> Compare</>)}
        </button>
      </div>

      {similarity !== null && (
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-6">
          {/* Morphological Contrast */}
          <div className="surface-card-lg glass-glow p-6">
            <MorphologicalContrast result1={results[0]} result2={results[1]} />
          </div>

          {/* Similarity & Confidence Summary */}
          <div className={`${cardClass} p-10 text-center`}>
            <div className="text-sm text-gray-500 mb-3 font-medium">Overall Similarity Score</div>
            <div className={`text-6xl font-extrabold ${similarity > 0.8 ? 'text-green-500' : similarity > 0.5 ? 'text-yellow-500' : 'text-red-500'}`}>
              {(similarity * 100).toFixed(1)}%
            </div>
            <div className="mt-4 text-sm t-secondary">
              {similarity > 0.8 ? 'High similarity — likely same species' : similarity > 0.5 ? 'Moderate similarity — possibly related species' : 'Low similarity — likely different species'}
            </div>

            {/* Confidence Grid */}
            <div className="mt-6 grid grid-cols-2 gap-3 text-left">
              <div className="p-4 rounded-lg surface-inset text-xs space-y-2">
                <div className="text-[10px] uppercase tracking-wider t-tertiary font-medium">Image 1 {results[0]?.requires_field_validation ? '⚠️' : ''}</div>
                <div>
                  <div className="text-[10px] t-tertiary mb-1">Model Confidence</div>
                  <div className={`text-lg font-bold ${results[0]?.is_unknown ? 'text-amber-500' : 'text-orange-500'}`}>
                    {(results[0]?.confidence * 100).toFixed(1)}%
                  </div>
                </div>
                {results[0]?.quality_adjusted_confidence !== undefined && results[0]?.quality_adjusted_confidence !== results[0]?.confidence && (
                  <div>
                    <div className="text-[10px] t-tertiary mb-1">Quality-Adjusted</div>
                    <div className={`text-sm font-semibold ${results[0]?.quality_adjusted_confidence < 0.5 ? 'text-red-500' : 'text-yellow-500'}`}>
                      {(results[0]?.quality_adjusted_confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                )}
                <div className="text-[10px] t-tertiary capitalize pt-1 border-t border-white/10">{results[0]?.species || 'Unknown'}</div>
              </div>
              <div className="p-4 rounded-lg surface-inset text-xs space-y-2">
                <div className="text-[10px] uppercase tracking-wider t-tertiary font-medium">Image 2 {results[1]?.requires_field_validation ? '⚠️' : ''}</div>
                <div>
                  <div className="text-[10px] t-tertiary mb-1">Model Confidence</div>
                  <div className={`text-lg font-bold ${results[1]?.is_unknown ? 'text-amber-500' : 'text-orange-500'}`}>
                    {(results[1]?.confidence * 100).toFixed(1)}%
                  </div>
                </div>
                {results[1]?.quality_adjusted_confidence !== undefined && results[1]?.quality_adjusted_confidence !== results[1]?.confidence && (
                  <div>
                    <div className="text-[10px] t-tertiary mb-1">Quality-Adjusted</div>
                    <div className={`text-sm font-semibold ${results[1]?.quality_adjusted_confidence < 0.5 ? 'text-red-500' : 'text-yellow-500'}`}>
                      {(results[1]?.quality_adjusted_confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                )}
                <div className="text-[10px] t-tertiary capitalize pt-1 border-t border-white/10">{results[1]?.species || 'Unknown'}</div>
              </div>
            </div>

            {/* Quality Warnings */}
            {(results[0]?.requires_field_validation || results[1]?.requires_field_validation) && (
              <div className="mt-6 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs">
                <div className="flex items-start gap-2">
                  <FiAlertTriangle className="text-red-500 mt-0.5 shrink-0" size={12} />
                  <span className="t-secondary">
                    {results[0]?.requires_field_validation && <div>Image 1: Severe blur detected — field validation recommended</div>}
                    {results[1]?.requires_field_validation && <div>Image 2: Severe blur detected — field validation recommended</div>}
                  </span>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
