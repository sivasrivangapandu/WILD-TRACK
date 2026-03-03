import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiSearch, FiMapPin, FiInfo, FiChevronRight, FiMaximize, FiCheck, FiX, FiFilter, FiZap, FiGlobe, FiAlertTriangle, FiBookOpen, FiTarget, FiStar, FiFeather, FiCompass, FiShield, FiLayers, FiActivity } from 'react-icons/fi';
import { GiPawPrint } from 'react-icons/gi';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

const SPECIES_ICONS = {
  tiger: '🐅', leopard: '🐆', elephant: '🐘', deer: '🦌', wolf: '🐺',
  bear: '🐻', fox: '🦊', lion: '🦁', rhino: '🦏', hippo: '🦛',
  horse: '🐴', rabbit: '🐇', cat: '🐱', dog: '🐕', hyena: '🐺',
  moose: '🫎', boar: '🐗', gorilla: '🦍', kangaroo: '🦘', penguin: '🐧',
};

const STATUS_COLORS = {
  'Endangered': { bg: 'bg-red-500/15 border-red-500/30', text: 'text-red-400', dot: 'bg-red-500' },
  'Critically Endangered': { bg: 'bg-red-600/20 border-red-600/40', text: 'text-red-400', dot: 'bg-red-600' },
  'Vulnerable': { bg: 'bg-yellow-500/15 border-yellow-500/30', text: 'text-yellow-400', dot: 'bg-yellow-500' },
  'Near Threatened': { bg: 'bg-amber-500/15 border-amber-500/30', text: 'text-amber-400', dot: 'bg-amber-500' },
  'Least Concern': { bg: 'bg-green-500/15 border-green-500/30', text: 'text-green-400', dot: 'bg-green-500' },
  'Domesticated': { bg: 'bg-blue-500/15 border-blue-500/30', text: 'text-blue-400', dot: 'bg-blue-500' },
};

const SEARCH_SUGGESTIONS = [
  'rhino', 'snow leopard', 'african wild dog', 'jaguar', 'mountain lion',
  'grizzly bear', 'red fox', 'bobcat', 'lynx', 'raccoon', 'badger', 'otter',
  'cheetah', 'moose', 'bison', 'coyote', 'wolverine', 'puma',
];

/* ═══════════════════════════════════════════
   KNOWLEDGE PANEL — Google-Style Two-Column
   ═══════════════════════════════════════════ */
function KnowledgePanel({ species, query }) {
  if (!species) return null;

  const icon = SPECIES_ICONS[species.name?.toLowerCase()] || SPECIES_ICONS[query?.toLowerCase()] || '🐾';
  const panel = species.info_panel || {};
  const classification = species.classification || {};

  const classChain = [
    classification.kingdom,
    classification.phylum,
    classification.class,
    classification.order,
    classification.family,
    classification.genus,
  ].filter(Boolean);

  const ACCENT_COLORS = {
    orange: 'text-orange-500',
    green: 'text-green-500',
    purple: 'text-purple-500',
    amber: 'text-amber-500',
    blue: 'text-blue-500',
    emerald: 'text-emerald-500',
  };

  const Section = ({ icon: Icon, title, children, accent = 'orange' }) => (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Icon className={ACCENT_COLORS[accent] || 'text-orange-500'} size={14} />
        <span className={`font-semibold text-xs uppercase tracking-wider ${ACCENT_COLORS[accent] || 'text-orange-500'}`}>{title}</span>
      </div>
      <div className="text-sm leading-relaxed t-secondary">{children}</div>
    </div>
  );

  const InfoRow = ({ label, value }) => {
    if (!value || value === 'not documented' || value === 'unknown') return null;
    return (
      <div className="flex justify-between items-start py-2.5 border-b border-[var(--border-subtle)] last:border-b-0">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 shrink-0">{label}</span>
        <span className="text-sm t-secondary text-right ml-3">{value}</span>
      </div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* Title Bar */}
      <div className="surface-card-lg glass-glow p-6 rounded-b-none border-b-0">
        <div className="flex items-start gap-4">
          <motion.span
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            className="text-5xl mt-1"
          >
            {icon}
          </motion.span>
          <div className="flex-1">
            <h2 className="text-3xl font-extrabold neon-heading leading-tight">{species.name}</h2>
            {species.scientific_name && species.scientific_name !== 'Unknown' && (
              <p className="italic text-sm mt-1 t-tertiary">{species.scientific_name}</p>
            )}
            {classChain.length > 0 && (
              <div className="flex flex-wrap items-center gap-1 mt-2.5">
                {classChain.map((c, i) => (
                  <span key={i} className="inline-flex items-center text-[10px] t-dim">
                    {i > 0 && <FiChevronRight size={8} className="mx-0.5" />}
                    <span className={i === classChain.length - 1 ? 'font-semibold text-orange-500' : ''}>{c}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Two-Column Layout */}
      <div className="flex flex-col lg:flex-row gap-0 lg:gap-1">
        {/* ── LEFT COLUMN (Main Content) ── */}
        <div className="flex-1 lg:flex-[2] space-y-0">
          {species.overview && (
            <div className="surface-card-lg glass-glow p-6 rounded-none border-t-0 border-b border-b-[var(--border-subtle)]">
              <Section icon={FiBookOpen} title="Overview">
                <p>{species.overview}</p>
              </Section>
            </div>
          )}

          {species.ecology && (
            <div className="surface-card-lg glass-glow p-6 rounded-none border-t-0 border-b border-b-[var(--border-subtle)]">
              <Section icon={FiActivity} title="Ecology & Behavior" accent="green">
                <p>{species.ecology}</p>
              </Section>
            </div>
          )}

          {species.physical_traits && (
            <div className="surface-card-lg glass-glow p-6 rounded-none border-t-0 border-b border-b-[var(--border-subtle)]">
              <Section icon={FiFeather} title="Physical Characteristics" accent="purple">
                <p>{species.physical_traits}</p>
              </Section>
            </div>
          )}

          {species.field_identification && (
            <div className="surface-card-lg glass-glow p-6 rounded-none border-t-0 border-b border-b-[var(--border-subtle)]">
              <Section icon={FiTarget} title="Field Identification" accent="amber">
                <p>{species.field_identification}</p>
              </Section>
            </div>
          )}

          {species.distribution_summary && (
            <div className="surface-card-lg glass-glow p-6 rounded-none border-t-0 border-b border-b-[var(--border-subtle)]">
              <Section icon={FiGlobe} title="Geographic Distribution" accent="blue">
                <p>{species.distribution_summary}</p>
              </Section>
            </div>
          )}

          {species.conservation_note && (
            <div className="surface-card-lg glass-glow p-6 rounded-t-none rounded-bl-xl lg:rounded-bl-xl border-t-0">
              <Section icon={FiShield} title="Conservation & Significance" accent="emerald">
                <p>{species.conservation_note}</p>
              </Section>
            </div>
          )}
        </div>

        {/* ── RIGHT COLUMN (Info Panel) ── */}
        <div className="lg:flex-1 lg:max-w-xs">
          <div className="surface-card-lg glass-glow p-5 rounded-t-none lg:rounded-tr-xl rounded-b-xl lg:rounded-bl-none border-t-0 lg:border-t space-y-0 lg:sticky lg:top-4 h-fit">
            <div className="text-xs font-bold uppercase tracking-wider text-orange-500 mb-3 flex items-center gap-1.5">
              <FiInfo size={12} />
              Quick Facts
            </div>

            <InfoRow label="Type" value={panel.type} />
            <InfoRow label="Habitat" value={panel.habitat} />
            <InfoRow label="Region" value={panel.region} />
            <InfoRow label="Weight" value={panel.weight} />
            <InfoRow label="Height" value={panel.height} />
            <InfoRow label="Diet" value={panel.diet} />
            <InfoRow label="Lifespan" value={panel.lifespan} />
            <InfoRow label="Color" value={panel.color} />
            <InfoRow label="Skin" value={panel.skin_type} />

            {classChain.length > 2 && (
              <div className="pt-4 mt-3 border-t border-[var(--border-subtle)]">
                <div className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2.5 flex items-center gap-1.5">
                  <FiLayers size={12} />
                  Taxonomy
                </div>
                <div className="space-y-1.5">
                  {[
                    { label: 'Kingdom', value: classification.kingdom },
                    { label: 'Phylum', value: classification.phylum },
                    { label: 'Class', value: classification.class },
                    { label: 'Order', value: classification.order },
                    { label: 'Family', value: classification.family },
                    { label: 'Genus', value: classification.genus },
                  ].filter(c => c.value).map((c, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs" style={{ paddingLeft: `${i * 8}px` }}>
                      <span className="w-1 h-1 rounded-full bg-orange-500/40 shrink-0" />
                      <span className="text-gray-500">{c.label}:</span>
                      <span className="t-secondary font-medium">{c.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════
   TRAINED SPECIES CARD (local data)
   ═══════════════════════════════════════════ */
function TrainedSpeciesCard({ name, detail }) {
  if (!detail) return null;
  const statusStyle = STATUS_COLORS[detail.conservation_status] || STATUS_COLORS['Least Concern'];
  const icon = SPECIES_ICONS[name.toLowerCase()] || '🐾';
  const infoBoxClass = 'flex items-start gap-3 p-3.5 rounded-xl surface-inset';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="surface-card-lg glass-glow p-6 space-y-5"
    >
      <div className="flex items-center gap-4">
        <span className="text-5xl">{icon}</span>
        <div>
          <h2 className="text-2xl font-extrabold capitalize neon-heading">{name}</h2>
          {detail.scientific_name && (
            <p className="italic text-sm mt-0.5 t-tertiary">{detail.scientific_name}</p>
          )}
          {detail.conservation_status && (
            <span className={`inline-flex items-center gap-1.5 mt-2 px-3 py-1 rounded-full text-xs font-semibold border ${statusStyle.bg} ${statusStyle.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${statusStyle.dot}`} />
              {detail.conservation_status}
            </span>
          )}
        </div>
      </div>

      <p className="leading-relaxed text-sm t-secondary">{detail.description}</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {detail.habitat && (
          <div className={infoBoxClass}>
            <FiMapPin className="text-orange-500 mt-0.5 shrink-0" />
            <div>
              <div className="font-semibold text-[10px] uppercase tracking-wider text-gray-500 mb-0.5">Habitat</div>
              <div className="text-sm t-secondary">{detail.habitat}</div>
            </div>
          </div>
        )}
        {detail.footprint_size && (
          <div className={infoBoxClass}>
            <FiMaximize className="text-orange-500 mt-0.5 shrink-0" />
            <div>
              <div className="font-semibold text-[10px] uppercase tracking-wider text-gray-500 mb-0.5">Footprint Size</div>
              <div className="text-sm t-secondary">{detail.footprint_size}</div>
            </div>
          </div>
        )}
        {detail.weight && (
          <div className={infoBoxClass}>
            <FiInfo className="text-orange-500 mt-0.5 shrink-0" />
            <div>
              <div className="font-semibold text-[10px] uppercase tracking-wider text-gray-500 mb-0.5">Weight</div>
              <div className="text-sm t-secondary">{detail.weight}</div>
            </div>
          </div>
        )}
        {detail.distribution && (
          <div className={infoBoxClass}>
            <FiGlobe className="text-orange-500 mt-0.5 shrink-0" />
            <div>
              <div className="font-semibold text-[10px] uppercase tracking-wider text-gray-500 mb-0.5">Distribution</div>
              <div className="text-sm t-secondary">{detail.distribution}</div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════ */
export default function SpeciesExplorerPage() {
  const { dark } = useTheme();
  const [trainedSpecies, setTrainedSpecies] = useState([]);
  const [localDetails, setLocalDetails] = useState({});
  const [selected, setSelected] = useState(new Set());
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [compareMode, setCompareMode] = useState(false);

  const [aiQuery, setAiQuery] = useState('');
  const [aiSearching, setAiSearching] = useState(false);
  const [aiResults, setAiResults] = useState({});
  const [aiError, setAiError] = useState('');
  const [recentSearches, setRecentSearches] = useState([]);

  useEffect(() => {
    api.getSpecies().then(res => {
      const names = (res.data.species || []).map(s => s.name);
      setTrainedSpecies(names);
      Promise.all(names.map(name =>
        api.getSpeciesDetail(name)
          .then(r => ({ name, ...r.data.info }))
          .catch(() => ({ name, description: 'Details not available' }))
      )).then(results => {
        const map = {};
        results.forEach(d => { map[d.name] = d; });
        setLocalDetails(map);
        setLoading(false);
      });
    }).catch(() => setLoading(false));
  }, []);

  const searchAI = useCallback(async (query) => {
    const q = (query || aiQuery).trim();
    if (!q || q.length < 2) return;
    if (aiResults[q.toLowerCase()]) { setAiError(''); return; }

    setAiSearching(true);
    setAiError('');
    try {
      const res = await api.getAnimalInfo(q);
      const data = res.data;
      if (data.found && data.species) {
        setAiResults(prev => ({ ...prev, [q.toLowerCase()]: data }));
        setRecentSearches(prev => {
          const next = [q, ...prev.filter(s => s.toLowerCase() !== q.toLowerCase())];
          return next.slice(0, 8);
        });
      } else {
        setAiError(`Species profile not available for "${q}". Try another animal.`);
      }
    } catch (err) {
      setAiError(err.message || 'Unable to retrieve species information.');
    } finally {
      setAiSearching(false);
    }
  }, [aiQuery, aiResults]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') { e.preventDefault(); searchAI(); }
  };

  const filteredTrained = useMemo(() =>
    trainedSpecies.filter(s => s.toLowerCase().includes(filter.toLowerCase())),
    [trainedSpecies, filter]
  );

  const toggleSelect = (name) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === filteredTrained.length) setSelected(new Set());
    else setSelected(new Set(filteredTrained));
  };

  const getDetail = (name) => {
    if (localDetails[name]) return { ...localDetails[name], source: 'local' };
    return null;
  };

  const cardClass = 'surface-card-lg glass-glow';

  const activeAIQuery = Object.keys(aiResults).find(q => q === aiQuery.toLowerCase()) || Object.keys(aiResults).slice(-1)[0];
  const activeAIResult = activeAIQuery ? aiResults[activeAIQuery] : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full" />
          <span className="text-sm t-tertiary">Loading species database...</span>
        </div>
      </div>
    );
  }

  const selectedSpecies = Array.from(selected);
  const displaySpecies = compareMode && selectedSpecies.length > 0 ? selectedSpecies : (selected.size > 0 ? selectedSpecies : []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <motion.div whileHover={{ rotate: 10 }} className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
            <FiCompass className="text-white text-lg" />
          </motion.div>
          <div>
            <h1 className="text-2xl font-bold neon-heading">Species Explorer</h1>
            <p className="text-sm t-tertiary">Intelligent Wildlife Knowledge System</p>
          </div>
        </div>
        <motion.button
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
          onClick={() => setCompareMode(c => !c)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all ${compareMode
            ? 'bg-orange-500/15 text-orange-500 ring-1 ring-orange-500/30 shadow-sm shadow-orange-500/10'
            : 'surface-inset t-secondary'}`}
        >
          <FiFilter size={14} /> {compareMode ? 'Compare Mode ON' : 'Compare Mode'}
          {selected.size > 0 && <span className="ml-1 px-1.5 py-0.5 rounded-full bg-orange-500 text-white text-[10px]">{selected.size}</span>}
        </motion.button>
      </div>

      {/* ═══ SEARCH ENGINE ═══ */}
      <div className={`${cardClass} p-5`}>
        <div className="flex items-center gap-2 mb-3">
          <FiCompass className="text-orange-400" size={16} />
          <span className="text-sm font-bold text-orange-500">WildTrackAI Knowledge Base</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <FiSearch className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search any species... (e.g. rhino, snow leopard, jaguar)"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full pl-10 pr-4 py-3 rounded-xl border text-sm
                bg-[var(--bg-surface-2)] border-[var(--border-primary)] placeholder:t-dim
                focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none transition-all"
            />
          </div>
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => searchAI()}
            disabled={aiSearching || !aiQuery.trim()}
            className={`px-5 py-3 rounded-xl text-sm font-semibold transition-all flex items-center gap-2
              ${aiSearching
                ? 'bg-orange-500/30 text-orange-300 cursor-wait'
                : 'bg-gradient-to-r from-orange-500 to-amber-500 text-white hover:shadow-lg hover:shadow-orange-500/20 active:scale-95'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {aiSearching ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                Searching...
              </>
            ) : (
              <>
                <FiSearch size={14} />
                Search
              </>
            )}
          </motion.button>
        </div>

        {/* Suggestions */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          <span className="text-[10px] uppercase tracking-wider font-semibold self-center mr-1 t-dim">Explore:</span>
          {SEARCH_SUGGESTIONS.slice(0, 10).map(s => (
            <motion.button
              key={s}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => { setAiQuery(s); searchAI(s); }}
              className="px-2.5 py-1 rounded-full text-[11px] font-medium transition-all surface-inset t-tertiary hover:text-orange-400"
            >
              {SPECIES_ICONS[s.toLowerCase()] || '🐾'} {s}
            </motion.button>
          ))}
        </div>

        {/* Recent searches */}
        {recentSearches.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            <span className="text-[10px] uppercase tracking-wider font-semibold mr-1 t-dim">Recent:</span>
            {recentSearches.map(s => (
              <button
                key={s}
                onClick={() => { setAiQuery(s); searchAI(s); }}
                className="px-2.5 py-1 rounded-full text-[11px] font-medium transition-all
                  bg-orange-500/10 text-orange-500 border border-orange-500/20 hover:bg-orange-500/20"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Error */}
        <AnimatePresence>
          {aiError && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 flex items-center gap-2 text-sm p-3 rounded-xl border bg-red-500/10 border-red-500/20 text-red-500"
            >
              <FiAlertTriangle size={14} />
              {aiError}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ═══ KNOWLEDGE PANEL RESULT ═══ */}
      <AnimatePresence>
        {activeAIResult && (
          <KnowledgePanel species={activeAIResult.species} query={activeAIQuery} />
        )}
      </AnimatePresence>

      {/* ═══ TRAINED SPECIES ═══ */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <FiBookOpen className="text-green-500" size={16} />
          <span className="text-sm font-bold text-green-500">Trained Species</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/15 text-green-500 border border-green-500/30">
            {trainedSpecies.length} species
          </span>
        </div>

        <div className={`${cardClass} p-4 mb-4`}>
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Filter trained species..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border bg-[var(--bg-surface-2)] border-[var(--border-primary)] focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none text-sm"
              />
            </div>
            <motion.button
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
              onClick={selectAll}
              className="px-3 py-2.5 rounded-xl text-xs font-medium transition surface-inset t-secondary"
            >
              {selected.size === filteredTrained.length ? 'Deselect All' : 'Select All'}
            </motion.button>
            {selected.size > 0 && (
              <motion.button initial={{ scale: 0 }} animate={{ scale: 1 }}
                onClick={() => setSelected(new Set())}
                className="p-2.5 rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition"
              >
                <FiX size={16} />
              </motion.button>
            )}
          </div>

          <div className="flex flex-wrap gap-2 mt-3">
            {filteredTrained.map(s => (
              <motion.button
                key={s}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => toggleSelect(s)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all
                  ${selected.has(s)
                    ? 'bg-orange-500/15 text-orange-500 ring-1 ring-orange-500/30 shadow-sm'
                    : 'surface-inset t-secondary'}`}
              >
                {selected.has(s) && <FiCheck size={12} />}
                <span className="text-base">{SPECIES_ICONS[s] || '🐾'}</span>
                <span className="capitalize">{s}</span>
              </motion.button>
            ))}
            {filteredTrained.length === 0 && (
              <p className="text-sm py-2 t-dim">No trained species match your filter</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-2">
            {filteredTrained.map((s, i) => (
              <motion.button
                key={s}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                onClick={() => {
                  if (compareMode) toggleSelect(s);
                  else setSelected(new Set([s]));
                }}
                className={`w-full flex items-center gap-3 p-4 rounded-2xl text-left transition-all group ${
                  selected.has(s)
                    ? 'bg-orange-500/10 border-2 border-orange-500/30 shadow-sm shadow-orange-500/5'
                    : `${cardClass} hover:shadow-md border hover:border-orange-500/10`
                }`}
              >
                <span className="text-3xl">{SPECIES_ICONS[s] || '🐾'}</span>
                <div className="flex-1 min-w-0">
                  <span className="capitalize font-semibold block">{s}</span>
                  {localDetails[s]?.scientific_name && (
                    <span className="text-xs italic t-tertiary">{localDetails[s].scientific_name}</span>
                  )}
                </div>
                {compareMode && (
                  <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition ${
                    selected.has(s) ? 'border-orange-500 bg-orange-500' : 'border-[var(--border-primary)]'
                  }`}>
                    {selected.has(s) && <FiCheck className="text-white text-xs" />}
                  </div>
                )}
                <FiChevronRight className={`transition-transform ${selected.has(s) ? 'text-orange-500 rotate-90' : 'text-gray-400 group-hover:text-orange-400'}`} />
              </motion.button>
            ))}
          </div>

          <div className="lg:col-span-2">
            <AnimatePresence mode="wait">
              {displaySpecies.length > 0 ? (
                <motion.div
                  key={displaySpecies.join('-')}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="space-y-5"
                >
                  {compareMode && displaySpecies.length > 1 && (
                    <div className={`${cardClass} p-4 text-center`}>
                      <span className="text-xs font-semibold uppercase tracking-wider text-orange-500">
                        Comparing {displaySpecies.length} Species
                      </span>
                    </div>
                  )}

                  <div className={compareMode && displaySpecies.length > 1 ? 'grid grid-cols-1 md:grid-cols-2 gap-4' : ''}>
                    {displaySpecies.map(name => (
                      <TrainedSpeciesCard key={name} name={name} detail={getDetail(name)} />
                    ))}
                  </div>

                  {compareMode && displaySpecies.length > 1 && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`${cardClass} p-6 overflow-x-auto`}
                    >
                      <h3 className="text-lg font-bold mb-4 t-primary">Comparison Table</h3>
                      <table className="w-full text-sm t-secondary">
                        <thead>
                          <tr className="border-b b-primary">
                            <th className="text-left py-2 px-3 font-semibold">Property</th>
                            {displaySpecies.map(name => (
                              <th key={name} className="text-left py-2 px-3 font-semibold capitalize">
                                {SPECIES_ICONS[name] || '🐾'} {name}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {['conservation_status', 'habitat', 'weight', 'footprint_size', 'distribution'].map(prop => (
                            <tr key={prop} className="border-b b-subtle">
                              <td className="py-2 px-3 font-medium capitalize text-xs text-gray-500">{prop.replace(/_/g, ' ')}</td>
                              {displaySpecies.map(name => {
                                const d = getDetail(name);
                                return <td key={name} className="py-2 px-3 text-xs">{d?.[prop] || '—'}</td>;
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </motion.div>
                  )}
                </motion.div>
              ) : (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={`${cardClass} p-16 text-center`}>
                  <GiPawPrint className="text-5xl mx-auto mb-4 text-orange-500/30" />
                  <p className="text-lg font-semibold mb-2 t-secondary">
                    {compareMode ? 'Select species to compare' : 'Select a species to view details'}
                  </p>
                  <p className="text-sm t-dim">
                    {compareMode ? 'Click multiple species from the list or use chips above' : 'Click any species from the list on the left'}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
