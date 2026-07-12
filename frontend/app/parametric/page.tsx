'use client';
import { useState, useEffect } from 'react';

interface TemplateParam {
  name: string;
  type: 'number' | 'boolean' | 'string';
  default: number | boolean | string;
  min?: number;
  max?: number;
  unit?: string;
}

interface Template {
  id: string;
  name: string;
  category: string;
  description: string;
  parameters: TemplateParam[];
}

export default function ParametricPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selected, setSelected] = useState<Template | null>(null);
  const [params, setParams] = useState<Record<string, number | boolean | string>>({});
  const [image, setImage] = useState('');
  const [scadCode, setScadCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('All');
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${API}/parametric/templates`)
      .then(r => r.json())
      .then(data => setTemplates(data.templates || []))
      .catch(e => setError('Failed to load templates: ' + e));
  }, [API]);

  const categories = ['All', ...Array.from(new Set(templates.map(t => t.category)))];
  const filtered = filter === 'All' ? templates : templates.filter(t => t.category === filter);

  const selectTemplate = (tmpl: Template) => {
    setSelected(tmpl);
    const defaults: Record<string, number | boolean | string> = {};
    tmpl.parameters.forEach(p => { defaults[p.name] = p.default; });
    setParams(defaults);
    setImage('');
    setScadCode('');
    setError('');
  };

  const generate = async () => {
    if (!selected) return;
    setLoading(true); setError(''); setImage(''); setScadCode(''); setStatus('Generating...');
    try {
      const res = await fetch(`${API}/parametric/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id: selected.id, parameters: params }),
      });
      const data = await res.json();
      if (data.image) {
        setImage('data:image/png;base64,' + data.image);
        setScadCode(data.scad_code || '');
        setStatus('');
      } else {
        setError(data.detail || 'Generation failed');
      }
    } catch (e) {
      setError('Error: ' + (e instanceof Error ? e.message : String(e)));
    }
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">📐 Parametric Modeling</h1>
          <a href="/" className="text-blue-400 hover:text-blue-300 text-sm">← Back to Home</a>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Template List */}
          <div className="bg-gray-900 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-4">Templates</h2>
            {/* Category filter */}
            <div className="flex flex-wrap gap-2 mb-4">
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setFilter(cat)}
                  className={`px-3 py-1 rounded-lg text-sm font-medium ${filter === cat ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                >{cat}</button>
              ))}
            </div>
            {/* Template grid */}
            <div className="space-y-2">
              {filtered.map(tmpl => (
                <button
                  key={tmpl.id}
                  onClick={() => selectTemplate(tmpl)}
                  className={`w-full text-left p-3 rounded-xl transition ${selected?.id === tmpl.id ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                >
                  <div className="font-semibold">{tmpl.name}</div>
                  <div className="text-xs text-gray-400">{tmpl.category}</div>
                  <div className="text-xs text-gray-500 mt-1">{tmpl.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Parameter Controls */}
          <div className="bg-gray-900 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-4">Parameters</h2>
            {!selected && <p className="text-gray-500">Select a template to begin</p>}
            {selected && (
              <div>
                <p className="text-gray-400 text-sm mb-4">{selected.description}</p>
                {selected.parameters.map(param => (
                  <div key={param.name} className="mb-4">
                    <label className="text-sm text-gray-300 mb-1 block">
                      {param.name.replace(/_/g, ' ')}
                      {param.unit && <span className="text-gray-500 ml-1">({param.unit})</span>}
                    </label>
                    {param.type === 'boolean' ? (
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => setParams(p => ({ ...p, [param.name]: !p[param.name] }))}
                          className={`px-4 py-2 rounded-lg font-medium ${params[param.name] ? 'bg-green-600' : 'bg-gray-700'}`}
                        >
                          {params[param.name] ? '✅ Yes' : '❌ No'}
                        </button>
                      </div>
                    ) : param.type === 'string' ? (
                      <input
                        type="text"
                        value={params[param.name] as string || ''}
                        onChange={e => setParams(p => ({ ...p, [param.name]: e.target.value }))}
                        maxLength={param.max || 20}
                        className="w-full bg-gray-800 rounded-lg p-2 text-white"
                      />
                    ) : (
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={param.min}
                          max={param.max}
                          value={params[param.name] as number}
                          onChange={e => setParams(p => ({ ...p, [param.name]: parseFloat(e.target.value) }))}
                          className="flex-1"
                        />
                        <input
                          type="number"
                          value={params[param.name] as number}
                          onChange={e => setParams(p => ({ ...p, [param.name]: parseFloat(e.target.value) || param.default }))}
                          className="w-20 bg-gray-800 rounded-lg p-2 text-white text-center"
                        />
                      </div>
                    )}
                  </div>
                ))}
                <button
                  onClick={generate}
                  disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-xl py-3 font-semibold transition mt-4"
                >
                  {loading ? '⏳ Generating...' : '🚀 Generate Model'}
                </button>
                {status && <div className="mt-3 text-sm text-blue-300">{status}</div>}
                {error && <div className="mt-3 text-sm text-red-300 bg-red-900 rounded-lg p-2">{error}</div>}
              </div>
            )}
          </div>

          {/* Preview */}
          <div className="bg-gray-900 rounded-2xl p-6 flex flex-col items-center justify-center min-h-96">
            <h2 className="text-xl font-semibold mb-4">Preview</h2>
            {loading && (
              <div className="text-center">
                <p className="text-5xl mb-4 animate-pulse">⚙️</p>
                <p className="text-gray-400">Generating with OpenSCAD...</p>
              </div>
            )}
            {image && !loading && (
              <div className="w-full">
                <img src={image} alt="3D Preview" className="rounded-xl w-full mb-4" />
                <a href={`${API}/download/stl`} download="model.stl"
                  className="block text-center w-full bg-green-600 hover:bg-green-700 rounded-xl py-3 font-semibold transition">
                  ⬇️ Download STL
                </a>
                {scadCode && (
                  <div className="mt-4">
                    <h3 className="text-sm text-gray-400 mb-2">OpenSCAD Code:</h3>
                    <pre className="bg-gray-800 rounded-xl p-4 text-sm overflow-auto max-h-48 text-green-400">{scadCode}</pre>
                  </div>
                )}
              </div>
            )}
            {!image && !loading && (
              <div className="text-gray-500 text-center">
                <p className="text-6xl mb-4">📐</p>
                <p>Select a template and generate</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}