'use client';
import { useState, useRef } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';

const ModelViewer = dynamic(() => import('@/components/ModelViewer'), { ssr: false });

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [refineText, setRefineText] = useState('');
  const [image, setImage] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [mode, setMode] = useState('openscad');
  const [description, setDescription] = useState('');
  const [stlUrl, setStlUrl] = useState('');
  const [view3D, setView3D] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const generate = async () => {
    setLoading(true); setError(''); setImage(''); setCode(''); setStlUrl(''); setStatus('Generating...');
    try {
      const res = await fetch(`${API}/generate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt }) });
      const data = await res.json();
      if (data.image) { setImage('data:image/png;base64,' + data.image); setCode(data.scad_code || ''); setStlUrl(`${API}/download/stl?t=${Date.now()}`); setStatus(''); }
      else setError('Render failed!');
    } catch (e) { setError('Error: ' + (e instanceof Error ? e.message : String(e))); }
    setLoading(false);
  };

  const refine = async () => {
    setLoading(true); setError(''); setStatus('Refining...');
    try {
      const res = await fetch(`${API}/refine`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ previous_scad: code || prompt, instruction: refineText }) });
      const data = await res.json();
      if (data.image) { setImage('data:image/png;base64,' + data.image); if (data.scad_code) setCode(data.scad_code); setStlUrl(`${API}/download/stl?t=${Date.now()}`); setRefineText(''); setStatus('Refined!'); }
    } catch (e) { setError('Error: ' + (e instanceof Error ? e.message : String(e))); }
    setLoading(false);
  };

  const generateFromImage = async () => {
    if (!fileRef.current?.files?.[0]) { setError('Please upload an image!'); return; }
    setLoading(true); setError(''); setImage(''); setCode(''); setDescription(''); setStlUrl(''); setStatus('LLM analyzing image...');
    try {
      const formData = new FormData();
      formData.append('file', fileRef.current.files[0]);
      const res = await fetch(`${API}/generate_from_image`, { method: 'POST', body: formData });
      const data = await res.json();
      if (data.image) { setImage('data:image/png;base64,' + data.image); setCode(data.scad_code || ''); setDescription(data.description || ''); setStlUrl(`${API}/download/stl?t=${Date.now()}`); setStatus('3D Model Generated!'); }
      else setError('Failed: ' + JSON.stringify(data));
    } catch (e) { setError('Error: ' + (e instanceof Error ? e.message : String(e))); }
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <h1 className="text-3xl font-bold text-center mb-8">🧊 LLM-Based 3D Model Generator</h1>
      <div className="max-w-6xl mx-auto flex flex-wrap gap-4 mb-6">
        <button onClick={() => setMode('openscad')} className={`flex-1 min-w-[120px] py-3 rounded-xl font-semibold ${mode === 'openscad' ? 'bg-blue-600' : 'bg-gray-800'}`}>📐 Text → 3D</button>
        <button onClick={() => setMode('ai')} className={`flex-1 min-w-[120px] py-3 rounded-xl font-semibold ${mode === 'ai' ? 'bg-purple-600' : 'bg-gray-800'}`}>🧠 Image → 3D</button>
        <Link href="/cloud" className="flex-1 min-w-[120px] py-3 rounded-xl font-semibold bg-gray-800 hover:bg-gray-700 text-center flex items-center justify-center">☁️ Cloud AI</Link>
        <Link href="/huggingface" className="flex-1 min-w-[120px] py-3 rounded-xl font-semibold bg-gray-800 hover:bg-gray-700 text-center flex items-center justify-center">🤗 HuggingFace</Link>
        <Link href="/parametric" className="flex-1 min-w-[120px] py-3 rounded-xl font-semibold bg-gray-800 hover:bg-gray-700 text-center flex items-center justify-center">📐 Parametric</Link>
        <Link href="/studio" className="flex-1 min-w-[120px] py-3 rounded-xl font-semibold bg-green-700 hover:bg-green-600 text-center flex items-center justify-center">🛠️ Studio</Link>
      </div>

      <div className="max-w-6xl mx-auto">
        {mode === 'openscad' && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Left: Controls — 2/5 width on large screens */}
            <div className="lg:col-span-2 bg-gray-900 rounded-2xl p-6">
              <h2 className="text-xl font-semibold mb-4">💬 Generate</h2>
              <textarea
                className="w-full bg-gray-800 rounded-xl p-4 text-white resize-none h-24 mb-4"
                placeholder="e.g. snowman, chair, house, bridge, gear, sword, dog, fish, bird, donut, diamond, tower, windmill, guitar, cup, hammer, key, lamp, flower, wheel, bolt, nut, stairs, shelf, boat, anchor, rocket..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
              <button onClick={generate} disabled={loading || !prompt} className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-xl py-3 font-semibold transition mb-4">
                {loading ? '⏳ Generating...' : '🚀 Generate 3D Model'}
              </button>
              {(image || stlUrl) && (
                <div>
                  <h2 className="text-xl font-semibold mb-2">🔧 Refine</h2>
                  <textarea
                    className="w-full bg-gray-800 rounded-xl p-4 text-white resize-none h-16 mb-3"
                    placeholder="e.g. make it bigger, make it smaller, rotate it, move it up..."
                    value={refineText}
                    onChange={(e) => setRefineText(e.target.value)}
                  />
                  <button onClick={refine} disabled={loading || !refineText} className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 rounded-xl py-3 font-semibold transition mb-3">✏️ Refine Model</button>
                  <a href={`${API}/download/stl`} download="model.stl" className="block text-center w-full bg-green-600 hover:bg-green-700 rounded-xl py-3 font-semibold transition">⬇️ Download STL</a>
                </div>
              )}
              {status && <div className="mt-4 bg-blue-900 rounded-xl p-3 text-sm text-blue-200">{status}</div>}
              {error && <div className="mt-4 bg-red-900 rounded-xl p-3 text-sm text-red-200">{error}</div>}
              {code && <div className="mt-4"><h3 className="text-sm text-gray-400 mb-2">OpenSCAD Code:</h3><pre className="bg-gray-800 rounded-xl p-4 text-sm overflow-auto max-h-48 text-green-400">{code}</pre></div>}
            </div>
            {/* Right: 3D Preview — 3/5 width, tall */}
            <div className="lg:col-span-3 bg-gray-900 rounded-2xl p-4 flex flex-col min-h-[600px]">
              <div className="flex items-center justify-between mb-4 px-2">
                <h2 className="text-xl font-semibold">🧊 3D Preview</h2>
                {(image || stlUrl) && !loading && (
                  <div className="flex gap-1 text-xs">
                    <button onClick={() => setView3D(true)} className={`px-4 py-1.5 rounded-lg font-medium transition ${view3D ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}>🎮 3D</button>
                    <button onClick={() => setView3D(false)} className={`px-4 py-1.5 rounded-lg font-medium transition ${!view3D ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}>📷 PNG</button>
                  </div>
                )}
              </div>
              {loading && <div className="text-center flex-1 flex flex-col items-center justify-center"><p className="text-4xl mb-4 animate-pulse">⚙️</p><p className="text-gray-400">{status}</p></div>}
              {stlUrl && !loading && view3D && (
                <div className="flex-1 relative rounded-xl overflow-hidden" style={{ minHeight: '500px' }}>
                  <ModelViewer stlUrl={stlUrl} />
                </div>
              )}
              {image && !loading && !view3D && <img src={image} alt="3D" className="rounded-xl w-full flex-1 object-contain"/>}
              {!stlUrl && !image && !loading && <div className="text-gray-500 text-center flex-1 flex flex-col items-center justify-center"><p className="text-6xl mb-4">🧊</p><p>Your 3D model will appear here</p></div>}
              {stlUrl && !loading && view3D && (
                <p className="text-xs text-gray-500 mt-2 text-center">🖱️ Drag to rotate · Scroll to zoom · Right-click to pan · 🔄 Auto-rotate button in bottom-right</p>
              )}
            </div>
          </div>
        )}

        {mode === 'ai' && (
          <div>
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">
              <div className="lg:col-span-2 bg-gray-900 rounded-2xl p-6">
                <h2 className="text-xl font-semibold mb-4">📸 LLM Vision → 3D</h2>
                <p className="text-gray-400 text-sm mb-4">LLM analyzes image → OpenSCAD → 3D model!</p>
                <input ref={fileRef} type="file" accept="image/*" className="w-full bg-gray-800 rounded-xl p-4 text-white mb-4"/>
                <button onClick={generateFromImage} disabled={loading} className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 rounded-xl py-3 font-semibold transition">
                  {loading ? '⏳ AI Processing...' : '🧠 Generate 3D from Image'}
                </button>
                {(image || stlUrl) && <a href={`${API}/download/stl`} download="model.stl" className="block text-center w-full bg-green-600 hover:bg-green-700 rounded-xl py-3 font-semibold transition mt-3">⬇️ Download STL</a>}
                {status && <div className="mt-4 bg-blue-900 rounded-xl p-3 text-sm text-blue-200">{status}</div>}
                {error && <div className="mt-4 bg-red-900 rounded-xl p-3 text-sm text-red-200">{error}</div>}
                {description && <div className="mt-4 bg-gray-800 rounded-xl p-4"><h3 className="text-sm text-gray-400 mb-2">🔍 LLM Description:</h3><p className="text-white text-sm">{description}</p></div>}
                {code && <div className="mt-4"><h3 className="text-sm text-gray-400 mb-2">OpenSCAD Code:</h3><pre className="bg-gray-800 rounded-xl p-4 text-sm overflow-auto max-h-48 text-green-400">{code}</pre></div>}
              </div>
              <div className="lg:col-span-3 bg-gray-900 rounded-2xl p-4 flex flex-col min-h-[600px]">
                <div className="flex items-center justify-between mb-4 px-2">
                  <h2 className="text-xl font-semibold">🧊 3D Preview</h2>
                  {(image || stlUrl) && !loading && (
                    <div className="flex gap-1 text-xs">
                      <button onClick={() => setView3D(true)} className={`px-4 py-1.5 rounded-lg font-medium transition ${view3D ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}>🎮 3D</button>
                      <button onClick={() => setView3D(false)} className={`px-4 py-1.5 rounded-lg font-medium transition ${!view3D ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}>📷 PNG</button>
                    </div>
                  )}
                </div>
                {loading && <div className="text-center flex-1 flex flex-col items-center justify-center"><p className="text-4xl mb-4 animate-pulse">⚙️</p><p className="text-gray-400">{status}</p></div>}
                {stlUrl && !loading && view3D && (
                  <div className="flex-1 relative rounded-xl overflow-hidden" style={{ minHeight: '500px' }}>
                    <ModelViewer stlUrl={stlUrl} />
                  </div>
                )}
                {image && !loading && !view3D && <img src={image} alt="3D" className="rounded-xl w-full flex-1 object-contain"/>}
                {!stlUrl && !image && !loading && <div className="text-gray-500 text-center flex-1 flex flex-col items-center justify-center"><p className="text-6xl mb-4">🧊</p><p>Upload an image!</p></div>}
                {stlUrl && !loading && view3D && (
                  <p className="text-xs text-gray-500 mt-2 text-center">🖱️ Drag to rotate · Scroll to zoom · Right-click to pan · 🔄 Auto-rotate button in bottom-right</p>
                )}
              </div>
            </div>
            <div className="bg-gray-900 rounded-2xl p-6 text-center">
              <h2 className="text-xl font-semibold mb-4">✨ Stable Fast 3D — High Quality Mesh</h2>
              <p className="text-gray-400 text-sm mb-6">For photorealistic 3D mesh generation</p>
              <a href="https://huggingface.co/spaces/stabilityai/stable-fast-3d" target="_blank"
                className="bg-pink-600 hover:bg-pink-700 px-8 py-4 rounded-xl font-semibold text-lg inline-block">
                🚀 Open Stable Fast 3D
              </a>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}