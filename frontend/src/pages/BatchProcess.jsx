import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { FiGrid, FiUpload, FiDownload, FiCheck, FiX } from 'react-icons/fi';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

export default function BatchProcessPage() {
  const { dark } = useTheme();
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleFiles = useCallback((fileList) => {
    const arr = Array.from(fileList).filter(f => f.type.startsWith('image/'));
    setFiles(arr);
    setResults([]);
    setProgress(0);
  }, []);

  const handleProcess = async () => {
    if (files.length === 0) return;
    setProcessing(true);
    setResults([]);
    const allResults = [];
    for (let i = 0; i < files.length; i++) {
      try {
        const res = await api.predict(files[i]);
        allResults.push({ file: files[i].name, ...res.data, status: 'success' });
      } catch { allResults.push({ file: files[i].name, status: 'error', species: 'Error', confidence: 0 }); }
      setProgress(((i + 1) / files.length) * 100);
      setResults([...allResults]);
    }
    setProcessing(false);
  };

  const downloadCSV = () => {
    const header = 'Filename,Species,Confidence,Top2,Top2_Conf,Top3,Top3_Conf\n';
    const rows = results.map(r => {
      const top3 = r.top3 || [];
      return [r.file, r.species, (r.confidence * 100).toFixed(1), top3[1]?.class || '', top3[1] ? (top3[1].confidence * 100).toFixed(1) : '', top3[2]?.class || '', top3[2] ? (top3[2].confidence * 100).toFixed(1) : ''].join(',');
    }).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `wildtrack_batch_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const cardClass = 'surface-card-lg glass-glow';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <motion.div whileHover={{ rotate: 10 }} className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
          <FiGrid className="text-white text-lg" />
        </motion.div>
        <div>
          <h1 className="text-2xl font-bold neon-heading">Batch Processing</h1>
          <p className="text-sm t-tertiary">Process multiple footprint images at once</p>
        </div>
      </div>

      <div className={`${cardClass} p-10 text-center cursor-pointer`} onClick={() => document.getElementById('batch-input').click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); handleFiles(e.dataTransfer.files); }}>
        <div className="w-16 h-16 rounded-2xl mx-auto flex items-center justify-center mb-4" style={{ background: 'var(--bg-surface-2)' }}>
          <FiUpload className="text-3xl text-orange-500" />
        </div>
        <p className="font-semibold text-lg">Drop multiple images here</p>
        <p className="text-sm mt-1 t-tertiary">or click to select &mdash; PNG, JPG, WEBP</p>
        {files.length > 0 && (<p className="mt-3 text-orange-500 font-bold">{files.length} files selected</p>)}
        <input id="batch-input" type="file" accept="image/*" multiple className="hidden" onChange={(e) => handleFiles(e.target.files)} />
      </div>

      {files.length > 0 && (
        <div className="flex gap-4">
          <button onClick={handleProcess} disabled={processing} className="px-8 py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white font-bold rounded-2xl hover:shadow-lg transition-all disabled:opacity-50">
            {processing ? 'Processing\u2026' : `Process ${files.length} Images`}
          </button>
          {results.length > 0 && !processing && (
            <button onClick={downloadCSV} className="px-6 py-3 rounded-2xl border font-semibold b-primary surface-hover">
              <FiDownload className="inline mr-2" /> Download CSV
            </button>
          )}
        </div>
      )}

      {processing && (
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="font-medium">Processing...</span>
            <span className="font-mono font-bold">{progress.toFixed(0)}%</span>
          </div>
          <div className="h-3 rounded-full" style={{ background: 'var(--bg-surface-2)' }}>
            <motion.div className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full" animate={{ width: `${progress}%` }} transition={{ duration: 0.3 }} />
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className={`${cardClass} overflow-hidden`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="" style={{ background: 'var(--bg-surface-2)' }}>
                <th className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider">#</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider">Filename</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider">Species</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider">Confidence</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i} className="border-t b-subtle hover:bg-[var(--bg-hover)]">
                  <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                  <td className="px-4 py-3 font-mono text-xs truncate max-w-[200px]">{r.file}</td>
                  <td className={`px-4 py-3 capitalize font-semibold ${r.is_unknown ? 'text-amber-500' : ''}`}>
                    {r.is_unknown ? (<><span>Unknown</span><span className="text-xs ml-1 font-normal text-gray-500">(closest: {r.raw_class})</span></>) : r.species}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 rounded-full" style={{ background: 'var(--bg-surface-2)' }}>
                        <div className={`h-full rounded-full ${
                          r.is_unknown ? 'bg-gradient-to-r from-amber-500 to-yellow-500'
                          : r.confidence >= 0.8 ? 'bg-gradient-to-r from-green-500 to-emerald-500'
                          : r.confidence >= 0.6 ? 'bg-gradient-to-r from-blue-500 to-cyan-500'
                          : r.confidence >= 0.5 ? 'bg-gradient-to-r from-orange-500 to-amber-500'
                          : 'bg-gradient-to-r from-red-500 to-rose-500'
                        }`} style={{ width: `${r.confidence * 100}%` }} />
                      </div>
                      <span className={`font-mono text-xs font-bold ${
                        r.is_unknown ? 'text-amber-500'
                        : r.confidence >= 0.8 ? 'text-green-500'
                        : r.confidence >= 0.6 ? 'text-blue-500'
                        : r.confidence >= 0.5 ? 'text-orange-500'
                        : 'text-red-500'
                      }`}>{(r.confidence * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">{r.status === 'success' ? <FiCheck className="text-green-500" /> : <FiX className="text-red-500" />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
