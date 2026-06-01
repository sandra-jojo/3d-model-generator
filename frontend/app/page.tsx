'use client';
import { useState, useRef } from 'react';

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
  const fileRef = useRef<HTMLInputElement>(null);
  const API = 'https://3d-model-generator-production.up.railway.app';

  const generate = async () => {
    setLoading(true);
    setError('');
    setImage('');
    setCode('');
    setStatus('Generating...');
    try {
      const res = await fetch(`${API}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });
      const data = await res.json();
      if (data.image) {
        setImage('data:image/png;base64,' + data.image);
        setCode(data.scad_code || prompt);
        setStatus('');
      } else {
        setError('Render failed!');
      }
    } catch (e: any) {
      setError('Error: ' + e?.message);
    }
    setLoading(false);
  };

  const refine = async () => {
    setLoading(true);
    setError('');
    setStatus('Refining...');
    try {
      const res = await fetch(`${API}/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ previous_scad: code || prompt, instruction: refineText })
      });
      const data = await res.json();
      if (data.image) {
        setImage('data:image/png;base64,' + data.image);
        if (data.scad_code) setCode(data.scad_code);
        setRefineText('');
        setStatus('✅ Refined!');
      }
    } catch (e: any) {
      setError('Error: ' + e?.message);
    }
    setLoading(false);
  };

  const generateFromImage = async () => {
    if (!fileRef.current?.files?.[0]) {
      setError('Please upload an image!');
      return;
    }
    setLoading(true);
    setError('');
    setImage('');
    setCode('');
    setDescription('');
    setStatus('🔍 LLM analyzing image...');
    try {
      const formData = new FormData();
      formData.append('file', fileRef.current.files[0]);
      const res = await fetch(`${API}/generate_from_image`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.image) {
        setImage('data:image/png;base64,' + data.image);
        setCode(data.scad_code || '');
        setDescription(data.description || '');
        setStatus('✅ 3D Model Generated!');
      } else {
        setError('Failed: ' + (JSON.stringify(data)));
      }
    } catch (e: any) {
      setError('Error: ' + e?.message);
    }
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <h1 className="text-3xl font-bold text-center mb-8">🧊 LLM-Based 3D Model Generator</h1>
      <div className="max-w-6xl mx-auto flex gap-4 mb-6">
        <button onClick={() => setMode('openscad')}
          className={`flex-1 py-3 rounded-xl font-semibold ${mode === 'openscad' ? 'bg-blue-600' : 'bg-gray-800'}`}>
          📐 Text → 3D
        </button>
        <button onClick={() => setMode('ai')}
          className={`flex-1 py-3 rounded-xl font-semibold ${mode === 'ai' ? 'bg-purple-600' : 'bg-gray-800'}`}>
          🧠 Image → 3D (AI)
        </button>
      </div>

      {mode === 'openscad' ? (
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gray-900 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-4">💬 Describe your 3D object</h2>
            <textarea
              className="w-full bg-gray-800 rounded-xl p-4 text-white resize-none h-24 mb-4"
              placeholder="e.g. snowman, chair, house..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <button onClick={generate} disabled={loading || !prompt}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-xl py-3 font-semibold transition mb-4">
              {loading ? '⏳ Generating...' : '🚀 Generate 3D Model'}
            </button>
            
              <>
                <h2 className="text-xl font-semibold mb-2">🔧 Refine</h2>
                <textarea
                  className="w-full bg-gray-800 rounded-xl p-4 text-white resize-none h-16 mb-3"
                  placeholder="e.g. make it bigger, make it taller..."
                  value={refineText}
                  onChange={(e) => setRefineText(e.target.value)}
                />
                <button onClick={refine} disabled={loading || !refineText}
                  className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 rounded-xl py-3 font-semibold transition mb-3">
                  ✏️ Refine Model
                </button>
                <a href={`${API}/download/stl`} download="model.stl"
                  className="block text-center w-full bg-green-600 hover:bg-green-700 rounded-xl py-3 font-semibold transition">
                  ⬇️ Download STL
                </a>
              </>
            )}
            {status && <div className="mt-4 bg-blue-900 rounded-xl p-3 text-sm text-blue-200">{status}</div>}
            {error && <div className="mt-4 bg-red-900 rounded-xl p-3 text-sm text-red-200">{error}</div>}
            {code && (
              <div className="mt-4">
                <h3 className="text-sm text-gray-400 mb-2">OpenSCAD Code:</h3>
                <pre className="bg-gray-800 rounded-xl p-4 text-sm overflow-auto max-h-48 text-green-400">{code}</pre>
              </div>
            )}
            {image && (
              <a href={`${API}/download/stl`} download="model.stl"
                className="block text-center w-full bg-green-600 hover:bg-green-700 rounded-xl py-3 font-semibold transition mt-3">
                ⬇️ Download STL
              </a>
            )}
          </div>
          <div className="bg-gray-900 rounded-2xl p-6 flex flex-col items-center justify-center min-h-64">
            <h2 className="text-xl font-semibold mb-4">🧊 3D Preview</h2>
            {loading && <div className="text-center"><p className="text-4xl mb-4 animate-pulse">⚙️</p><p className="text-gray-400">{status}</p></div>}
            {image && !loading && <img src={image} alt="3D" className="rounded-xl w-full"/>}
    
            {!image && !loading && (
              <div className="text-gray-500 text-center">
                <p className="text-6xl mb-4">🧊</p>
                <p>Your 3D model will appear here</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="max-w-6xl mx-auto col-span-2 mt-6" style={{gridColumn: "1 / -1"}}>
          <div className="bg-gray-900 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-4">📸 Upload Image → AI → 3D</h2>
            <p className="text-gray-400 text-sm mb-4">
              LLM analyzes your image → generates 3D model!
            </p>
            <input ref={fileRef} type="file" accept="image/*"
              className="w-full bg-gray-800 rounded-xl p-4 text-white mb-4"/>
            <button onClick={generateFromImage} disabled={loading}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 rounded-xl py-3 font-semibold transition">
              {loading ? '⏳ AI Processing...' : '🧠 Generate 3D from Image'}
            </button>
            {status && <div className="mt-4 bg-blue-900 rounded-xl p-3 text-sm text-blue-200">{status}</div>}
            {error && <div className="mt-4 bg-red-900 rounded-xl p-3 text-sm text-red-200">{error}</div>}
            {description && (
              <div className="mt-4 bg-gray-800 rounded-xl p-4">
                <h3 className="text-sm text-gray-400 mb-2">🔍 LLM Description:</h3>
                <p className="text-white text-sm">{description}</p>
              </div>
            )}
            {code && (
              <div className="mt-4">
                <h3 className="text-sm text-gray-400 mb-2">OpenSCAD Code:</h3>
                <pre className="bg-gray-800 rounded-xl p-4 text-sm overflow-auto max-h-48 text-green-400">{code}</pre>
              </div>
            )}
          </div>
          <div className="bg-gray-900 rounded-2xl p-6 flex flex-col items-center justify-center min-h-64">
            <h2 className="text-xl font-semibold mb-4">🧊 3D Preview</h2>
            {loading && <div className="text-center"><p className="text-4xl mb-4 animate-pulse">⚙️</p><p className="text-gray-400">{status}</p></div>}
            {image && !loading && <img src={image} alt="3D" className="rounded-xl w-full"/>}
            {!image && !loading && (
              <div className="text-gray-500 text-center">
                <p className="text-6xl mb-4">🧊</p>
                <p>Upload an image to generate 3D!</p>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
