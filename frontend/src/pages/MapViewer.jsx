import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, LayersControl } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '../services/api';
import { FiMap, FiFilter, FiActivity, FiNavigation, FiGlobe, FiDatabase, FiRefreshCw, FiWind, FiThermometer, FiBookOpen } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion';

// Create a premium custom marker icon
const createMapIcon = (confidence) => {
    const color = confidence >= 0.8 ? '#22c55e' : confidence >= 0.5 ? '#f97316' : '#ef4444';
    const shadow = `0 0 15px ${color}80`;

    return L.divIcon({
        className: 'custom-map-marker',
        html: `<div style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%; border: 3px solid #1f2937; box-shadow: ${shadow};"></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
        popupAnchor: [0, -10]
    });
};

export default function MapViewer() {
    const [localPredictions, setLocalPredictions] = useState([]);
    const [gbifData, setGbifData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dataError, setDataError] = useState('');
    const [filterSpecies, setFilterSpecies] = useState('all');
    const [dataSource, setDataSource] = useState('gbif'); // 'local' or 'gbif'

    // Premium Map Layer state
    const [mapLayer, setMapLayer] = useState('dark'); // 'dark', 'satellite', 'topo'

    // Active popup custom data states
    const [activeWeather, setActiveWeather] = useState(null);
    const [activeWiki, setActiveWiki] = useState(null);
    const [loadingPopup, setLoadingPopup] = useState(false);

    useEffect(() => {
        if (dataSource === 'local') {
            fetchLocalHistory();
        } else {
            fetchGbifData(filterSpecies);
        }
    }, [dataSource, filterSpecies]);

    const fetchLocalHistory = async () => {
        setLoading(true);
        setDataError('');
        try {
            const res = await api.getHistory(500, 0);
            const withGps = res.data.predictions.filter(p => p.latitude != null && p.longitude != null);
            setLocalPredictions(withGps);
        } catch (err) {
            console.error(err);
            setDataError('Unable to load Local App DB tracking points.');
        } finally {
            setLoading(false);
        }
    };

    // Mapping from our local app species names to precise GBIF taxonKeys to prevent generic name matches
    const speciesTaxonMap = {
        'tiger': 5219416, // Panthera tigris
        'leopard': 5219436, // Panthera pardus
        'elephant': 9427, // Elephantidae (Family to include both African and Asian)
        'wolf': 5219173, // Canis lupus
        'deer': 5298, // Cervidae
    };

    const fetchGbifData = async (speciesKey) => {
        setLoading(true);
        setDataError('');
        try {
            let urls = [];
            // If specific species, fetch that
            if (speciesKey !== 'all' && speciesTaxonMap[speciesKey]) {
                urls.push(`https://api.gbif.org/v1/occurrence/search?taxonKey=${speciesTaxonMap[speciesKey]}&hasCoordinate=true&limit=100`);
            } else {
                // If 'all', fetch a sampling from all supported species
                urls = Object.values(speciesTaxonMap).map(
                    taxon => `https://api.gbif.org/v1/occurrence/search?taxonKey=${taxon}&hasCoordinate=true&limit=50`
                );
            }

            const responses = await Promise.all(
                urls.map(async (url) => {
                    try {
                        const response = await fetch(url);
                        if (!response.ok) {
                            console.warn(`GBIF request failed (${response.status}) for URL: ${url}`);
                            return null;
                        }
                        return await response.json();
                    } catch (e) {
                        console.warn(`Fetch error for URL: ${url}`, e);
                        return null;
                    }
                })
            );

            // Filter out failed requests (nulls)
            const results = responses.filter(res => res !== null);

            let allOccurrences = [];
            results.forEach(result => {
                if (result && result.results) {
                    allOccurrences = [...allOccurrences, ...result.results.filter(r => r.decimalLatitude != null && r.decimalLongitude != null)];
                }
            });

            if (allOccurrences.length === 0) {
                setDataError('No live data found for the selected species right now. Try another filter or Local DB.');
                setGbifData([]);
                return;
            }

            // Map GBIF format back to standard unified format for rendering
            const formatted = allOccurrences.map((occ, index) => {
                // Determine species string based on exact taxonKey match
                let spName = 'unknown';

                for (const [name, key] of Object.entries(speciesTaxonMap)) {
                    if (occ.taxonKey === key || occ.speciesKey === key || occ.genusKey === key || occ.familyKey === key) {
                        spName = name;
                        break;
                    }
                }

                if (spName === 'unknown' && occ.species) spName = occ.species.toLowerCase().split(' ')[0];

                return {
                    id: occ.key || `gbif-${index}`,
                    latitude: occ.decimalLatitude,
                    longitude: occ.decimalLongitude,
                    species: spName,
                    scientificName: occ.scientificName || 'Unknown Species',
                    confidence: 0.95, // GBIF occurrences are typically high confidence occurrences
                    timestamp: occ.eventDate || occ.lastInterpreted || new Date().toISOString(),
                    isGbif: true,
                    country: occ.country || 'Unknown Location'
                }
            });

            setGbifData(formatted);
        } catch (err) {
            console.error("GBIF Fetch error:", err);
            setGbifData([]);
            setDataError('Unable to load GBIF live data right now. Please retry or switch to Local App DB.');
        } finally {
            setLoading(false);
        }
    };

    // --- Dynamic Popup Data Fetching ---
    const fetchContextData = async (lat, lng, spName) => {
        setLoadingPopup(true);
        setActiveWeather(null);
        setActiveWiki(null);
        try {
            // 1. Fetch Weather via Free Open-Meteo API
            const weatherRes = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current_weather=true`);
            if (weatherRes.ok) {
                const weatherData = await weatherRes.json();
                if (weatherData.current_weather) setActiveWeather(weatherData.current_weather);
            }

            // 2. Fetch species brief via Free Wikipedia API
            const formattedName = spName.charAt(0).toUpperCase() + spName.slice(1).toLowerCase();
            const wikiRes = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${formattedName}`);
            if (wikiRes.ok) {
                const wikiData = await wikiRes.json();
                if (wikiData.extract) setActiveWiki(wikiData.extract.length > 200 ? wikiData.extract.substring(0, 200) + '...' : wikiData.extract);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingPopup(false);
        }
    };

    const activeData = dataSource === 'local' ? localPredictions : gbifData;

    const filteredPredictions = useMemo(() => {
        if (dataSource === 'gbif') return activeData; // GBIF already filters via API parameters above
        if (filterSpecies === 'all') return activeData;
        return activeData.filter(p => p.species === filterSpecies);
    }, [activeData, filterSpecies, dataSource]);

    // Compute unique species based on overall capabilities
    const uniqueSpecies = ['tiger', 'leopard', 'elephant', 'wolf', 'deer'];

    // Default center
    const defaultCenter = [20.5937, 78.9629]; // India approx.

    return (
        <div className="h-[calc(100vh-4rem)] flex flex-col space-y-4">
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                    <motion.div whileHover={{ rotate: 10 }} className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
                        <FiMap className="text-white text-lg" />
                    </motion.div>
                    <div>
                        <h1 className="text-2xl font-bold neon-heading tracking-tight">Global Tracking Map</h1>
                        <p className="text-sm t-tertiary">Real-time geographical footprint distribution</p>
                    </div>
                </div>

                {/* Main Controls Overlay Dropdown / Action Bar */}
                <div className="flex gap-2 items-center">
                    <select
                        className="bg-black/40 backdrop-blur-md text-xs t-secondary border border-white/10 rounded-xl px-3 py-1.5 focus:outline-none focus:border-white/20 transition-all custom-select appearance-none cursor-pointer"
                        value={mapLayer}
                        onChange={(e) => setMapLayer(e.target.value)}
                    >
                        <option value="dark">🌙 Dark Base</option>
                        <option value="satellite">🛰️ Satellite</option>
                        <option value="topo">⛰️ Topography</option>
                    </select>

                    <div className="flex gap-2 bg-black/40 backdrop-blur-md p-1.5 rounded-xl border border-white/10 shadow-lg">
                        <button
                            onClick={() => setDataSource('gbif')}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium text-xs transition-all ${dataSource === 'gbif'
                                ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/10 border-green-500/30 text-green-400'
                                : 'text-gray-400 hover:text-white'
                                }`}
                            title="Global Biodiversity Data (Real-World Live Occurrence)"
                        >
                            <FiGlobe size={13} className={dataSource === 'gbif' ? 'text-green-400' : ''} />
                            GBIF Live
                        </button>
                        <div className="w-px bg-white/10 my-1 mx-1"></div>
                        <button
                            onClick={() => setDataSource('local')}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium text-xs transition-all ${dataSource === 'local'
                                ? 'bg-gradient-to-r from-orange-500/20 to-amber-500/10 border-orange-500/30 text-orange-400'
                                : 'text-gray-400 hover:text-white'
                                }`}
                            title="Your uploaded AI tracks"
                        >
                            <FiDatabase size={13} className={dataSource === 'local' ? 'text-orange-400' : ''} />
                            Local DB
                        </button>
                    </div>
                </div>
            </div>

            {/* Species Filters */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 hide-scrollbar">
                <button
                    onClick={() => setFilterSpecies('all')}
                    className={`px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all whitespace-nowrap ${filterSpecies === 'all' ? 'bg-white/15 text-white border border-white/20' : 'bg-white/5 t-tertiary hover:bg-white/10 border border-transparent'}`}
                >
                    All Species
                </button>
                {uniqueSpecies.map(sp => (
                    <button
                        key={sp}
                        onClick={() => setFilterSpecies(sp)}
                        className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all whitespace-nowrap ${filterSpecies === sp ? 'bg-white/15 text-white border border-white/20' : 'bg-white/5 t-tertiary hover:bg-white/10 border border-transparent'}`}
                    >
                        <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: sp === 'tiger' ? '#f97316' : sp === 'leopard' ? '#eab308' : sp === 'elephant' ? '#3b82f6' : sp === 'wolf' ? '#8b5cf6' : '#22c55e' }}></span>
                        {sp}
                    </button>
                ))}
            </div>

            <div className="flex-1 rounded-2xl overflow-hidden glass-glow border border-white/5 relative shadow-xl z-0 min-h-[500px]">
                {dataError && (
                    <div className="absolute top-4 left-4 right-4 z-50 p-3 rounded-xl border border-red-500/30 bg-red-500/15 text-red-200 text-sm">
                        {dataError}
                    </div>
                )}

                {loading && (
                    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                        <div className="animate-spin text-blue-500"><FiActivity size={32} /></div>
                    </div>
                )}

                {!loading && activeData.length === 0 && (
                    <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-black/80 backdrop-blur-md">
                        <FiNavigation size={48} className="text-gray-500 mb-4 opacity-50" />
                        <h2 className="text-xl font-bold text-gray-300">No GPS Tracking Data Available</h2>
                        <p className="text-sm text-gray-500 mt-2 max-w-md text-center">
                            Upload footprints with location services enabled or use the Live Camera to populate this map.
                        </p>
                    </div>
                )}

                {/* Leaflet MapContainer */}
                <MapContainer
                    key={filteredPredictions.length + mapLayer} // Force re-render on big changes
                    center={filteredPredictions.length > 0 ? [filteredPredictions[0].latitude, filteredPredictions[0].longitude] : defaultCenter}
                    zoom={4}
                    style={{ width: '100%', minHeight: '500px', height: '100%', background: '#0a0a0a' }}
                    zoomControl={true}
                    scrollWheelZoom={true} // ENABLING MOUSE WHEEL CONTROL
                    doubleClickZoom={true}
                    dragging={true}
                >
                    {/* Layer Switcher */}
                    {mapLayer === 'dark' && (
                        <TileLayer
                            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                        />
                    )}
                    {mapLayer === 'satellite' && (
                        <TileLayer
                            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                            attribution='&copy; Esri'
                        />
                    )}
                    {mapLayer === 'topo' && (
                        <TileLayer
                            url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
                            attribution='&copy; OpenTopoMap'
                        />
                    )}

                    {/* V3.1 Clustering Group */}
                    <MarkerClusterGroup
                        chunkedLoading
                        iconCreateFunction={(cluster) => {
                            return L.divIcon({
                                html: `<div class="w-10 h-10 bg-orange-500/80 backdrop-blur-md rounded-full border-2 border-white flex items-center justify-center text-white font-bold shadow-lg shadow-orange-500/50">${cluster.getChildCount()}</div>`,
                                className: 'custom-cluster-icon',
                                iconSize: L.point(40, 40, true),
                            });
                        }}
                    >
                        {filteredPredictions.map(p => (
                            <Marker
                                key={p.id}
                                position={[p.latitude, p.longitude]}
                                icon={createMapIcon(p.confidence)}
                                eventHandlers={{
                                    click: () => fetchContextData(p.latitude, p.longitude, p.species),
                                }}
                            >
                                <Popup className="custom-popup min-w-[280px]">
                                    <div className="bg-gray-900 border border-gray-800 text-white rounded-xl p-0 overflow-hidden shadow-2xl min-w-[200px]">
                                        {p.heatmap_generated && p.filename && (
                                            <div className="h-24 bg-gray-800 flex items-center justify-center text-xs font-mono text-gray-500">
                                                Footprint Profile
                                            </div>
                                        )}
                                        <div className="p-3">
                                            <div className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">
                                                {p.isGbif ? 'Live Occurrence' : 'Detected Species'}
                                            </div>
                                            <div className="text-lg font-bold capitalize text-orange-400">{p.scientificName || p.species}</div>

                                            {p.isGbif && p.country && (
                                                <div className="text-xs text-gray-300 mt-1 flex items-center gap-1">
                                                    <FiMap size={10} /> Location: {p.country}
                                                </div>
                                            )}

                                            {/* V3.1 Weather & Wikipedia Context */}
                                            <div className="mt-2 text-xs border-t border-gray-800 pt-2 pb-1 space-y-2">
                                                {loadingPopup ? (
                                                    <div className="text-gray-500 animate-pulse text-center">Fetching environmental data...</div>
                                                ) : (
                                                    <>
                                                        {activeWeather && (
                                                            <div className="flex items-center justify-between text-gray-300">
                                                                <div className="flex gap-1.5 items-center"><FiThermometer className="text-orange-500" /> {activeWeather.temperature}°C</div>
                                                                <div className="flex gap-1.5 items-center"><FiWind className="text-blue-400" /> {activeWeather.windspeed} km/h</div>
                                                            </div>
                                                        )}
                                                        {activeWiki && (
                                                            <div className="flex items-start gap-1.5 text-gray-400">
                                                                <FiBookOpen className="shrink-0 mt-0.5 text-blue-400" />
                                                                <span className="italic leading-relaxed">{activeWiki}</span>
                                                            </div>
                                                        )}
                                                    </>
                                                )}
                                            </div>

                                            <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-800 text-xs">
                                                <span className="text-gray-400">{p.isGbif ? 'Data Source' : 'Confidence'}</span>
                                                <span className={`font-mono font-bold ${p.isGbif ? 'text-green-400' : 'text-blue-400'}`}>
                                                    {p.isGbif ? 'GBIF API' : `${(p.confidence * 100).toFixed(1)}%`}
                                                </span>
                                            </div>
                                            <div className="text-[9px] text-gray-500 mt-2 font-mono text-right flex justify-between items-center">
                                                <span>Lat: {p.latitude.toFixed(2)}, Lng: {p.longitude.toFixed(2)}</span>
                                                <span>{new Date(p.timestamp).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                    </div>
                                </Popup>
                            </Marker>
                        ))}
                    </MarkerClusterGroup>
                </MapContainer>

                {/* Custom CSS overrides for Leaflet popups inside scoped map component */}
                <style dangerouslySetInnerHTML={{
                    __html: `
          .leaflet-popup-content-wrapper {
            background: transparent !important;
            padding: 0 !important;
            box-shadow: none !important;
          }
          .leaflet-popup-tip-container {
            display: none !important;
          }
          .leaflet-popup-content {
            margin: 0 !important;
          }
          .custom-popup {
            margin-bottom: 20px !important;
          }
          .custom-cluster-icon {
            background: transparent !important;
            border: none !important;
          }
          .custom-select {
            background-color: rgba(0, 0, 0, 0.4);
            color: #d1d5db;
          }
          .custom-select option {
            background-color: #111827; /* Tailwind gray-900 */
            color: #d1d5db;
          }
        `}} />
            </div>
        </div>
    );
}
