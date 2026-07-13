'use client';
import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';

type HFProvider = 'triposr' | 'stable-fast-3d' | 'hunyuan3d';

interface HFResult {
  status: string;
  space: string;
  obj_url?: string | null;
  glb_url?: string | null;
  mesh_stats?: Record<string, unknown> | string;
  error?: string;
  detail?: string;
  raw?: string;
}

const PROVIDERS: Record<HFProvider, {
  name: string;
  emoji: string;
  description: string;
  quality: string;
  qualityColor: string;
  inputType: string;
  endpoint: string;
  color: string;
}> = {
  triposr: {
    name: 'TripoSR',
    emoji: '⚡',
    description: 'Fast single-image to 3D reconstruction by Stability AI',
    quality: 'Medium',
    qualityColor: 'bg-yellow-600',
    inputType: 'Image only',
    endpoint: '/hf/triposr',
    color: 'bg-blue-600 hover:bg-blue-700',
  },
  'stable-fast-3d': {
    name: 'Stable Fast 3D',
    emoji: '🚀',
    description: 'High-quality textured 3D mesh from a single image',
    quality: 'High',
    qualityColor: 'bg-green-600',
    inputType: 'Image only',
    endpoint: '/hf/stable-fast-3d',
    color: 'bg-purple-600 hover:bg-purple-700',
  },
  hunyuan3d: {
    name: 'Hunyuan3D-2',
    emoji: '🐉',
    description: 'Tencent text or image to 3D with high-fidelity mesh generation',
    quality: 'High',
    qualityColor: 'bg-green-600',
    inputType: 'Text or Image',
    endpoint: '/hf/hunyuan3d',
    color: 'bg-orange-600 hover:bg-orange-700',
  },
};

export default function HuggingFacePage() {
  const [provider, setProvider] = useState<HFProvider>('triposr');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState<HFResult | null>(null);
  const [spaceStatus, setSpaceStatus] = useState<Record<string, string>>({});
  const [hasFile, setHasFile] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Check space status on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch(`${API}/hf/status`);
        const data = await res.json();
        setSpaceStatus(data);
      } catch {
        // ignore — status will show as unknown
      }
    };
    checkStatus();
  }, [API]);

  const generate = async () => {
    const prov = PROVIDERS[provider];
    const needsImage = prov.inputType === 'Image only';
    const hasImage = fileRef.current?.files?.[0];
    const hasText = prompt.trim() !== '';

    if (needsImage && !hasImage) {
      setError('Please upload an image for this provider!');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);
    setStatus(`Connecting to ${prov.name} Space...`);

    try {
      const formData = new FormData();
      if (hasImage) {
        formData.append('image', fileRef.current!.files![0]);
      }
      if (provider === 'hunyuan3d' && hasText) {
        formData.append('caption', prompt);
      }

      setStatus(`Generating 3D model with ${prov.name}...`);

      const res = await fetch(`${API}${prov.endpoint}`, {
        method: 'POST',
        body: formData,
      });
      let data;
      try {
        data = await res.json();
      } catch {
        setError(`Server error (${res.status}). The API may be unavailable.`);
        setLoading(false);
        return;
      }

      if (!res.ok || data.error) {
        setError(data.error ? `${data.error}${data.detail ? ': ' + data.detail : ''}` : `Server error (${res.status})`);
      } else {
        setResult(data);
        setStatus('Done!');
      }
    } catch (e) {
      setError('Error: ' + (e instanceof Error ? e.message : String(e)));
    }
    setLoading(false);
  };

  const modelUrl = result?.glb_url || result?.obj_url;
  const prov = PROVIDERS[provider];

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">🤗 HuggingFace Spaces 3D Generation</h1>
          <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">← Back to Local Gen</Link>
        </div>

        {/* Provider Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {(Object.keys(PROVIDERS) as HFProvider[]).map((key) => {
            const p = PROVIDERS[key];
            const isOnline = spaceStatus[key] === 'online';
            const isOffline = spaceStatus[key] === 'offline';
            return (
              <button
                key={key}
                onClick={() => { setProvider(key); setResult(null); setError(''); setHasFile(false); }}
                className={`text-left p-5 rounded-2xl transition border-2 ${
                  provider === key
                    ? 'border-blue-500 bg-gray-900'
                    : 'border-transparent bg-gray-900 hover:bg-gray-800'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{p.emoji}</span>
                  <h3 className="text-lg font-semibold">{p.name}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${p.qualityColor}`}>{p.quality}</span>
                </div>
                <p className="text-sm text-gray-400 mb-3">{p.description}</p>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-gray-500">Input: {p.inputType}</span>
                  {isOnline && <span className="text-green-400">● online</span>}
                  {isOffline && <span className="text-red-400">● offline</span>}
                  {!isOnline && !isOffline && <span className="text-gray-500">● checking...</span>}
                </div>
              </button>
            );
          })}
        </div>

        {/* Input + Result Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Input Panel */}
          <div className="bg-gray-900 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-4">
              {prov.emoji} {prov.name} Input
            </h2>

            {/* Image upload — shared */}
            <p className="text-gray-400 text-sm mb-2">Upload image{prov.inputType === 'Text or Image' ? ' (optional for Hunyuan3D)' : ' (required)'}:</p>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={(e) => setHasFile(!!e.target.files?.[0])}
              className="w-full bg-gray-800 rounded-xl p-4 text-white mb-4"
            />

            {/* Text prompt — for Hunyuan3D */}
            {provider === 'hunyuan3d' && (
              <>
                <p className="text-gray-400 text-sm mb-2">Text prompt (alternative to image):</p>
                <textarea
                  className="w-full bg-gray-800 rounded-xl p-4 text-white resize-none h-24 mb-4"
                  placeholder="e.g. a sports car, a fantasy castle..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                />
              </>
            )}

            <button
              onClick={generate}
              disabled={loading || (prov.inputType === 'Image only' && !hasFile)}
              className={`w-full rounded-xl py-3 font-semibold transition disabled:bg-gray-600 ${prov.color}`}
            >
              {loading ? `⏳ ${status}` : `🚀 Generate with ${prov.name}`}
            </button>

            {/* Progress / Status */}
            {loading && (
              <div className="mt-4 bg-blue-900 rounded-xl p-3 text-sm text-blue-200 animate-pulse">
                {status}
              </div>
            )}
            {!loading && status && !error && (
              <div className="mt-4 bg-green-900 rounded-xl p-3 text-sm text-green-200">{status}</div>
            )}
            {error && (
              <div className="mt-4 bg-red-900 rounded-xl p-3 text-sm text-red-200">
                {error}
                {error.includes('Space unavailable') && (
                  <p className="mt-2 text-xs">The Space may be sleeping. Try again in a minute, or visit the Space directly to wake it up.</p>
                )}
              </div>
            )}
          </div>

          {/* Result Panel */}
          <div className="bg-gray-900 rounded-2xl p-6 flex flex-col min-h-96">
            <h2 className="text-xl font-semibold mb-4">🧊 3D Result</h2>

            {loading && (
              <div className="text-center flex-1 flex flex-col items-center justify-center">
                <p className="text-5xl mb-4 animate-pulse">⚙️</p>
                <p className="text-gray-400">{status}</p>
              </div>
            )}

            {result && !loading && modelUrl && (
              <div className="w-full">
                {/* 3D Model Viewer for GLB */}
                {result.glb_url && (
                  <div className="mb-4 bg-gray-800 rounded-xl p-4">
                    <p className="text-gray-400 text-sm mb-2">3D Preview (GLB):</p>
                    <model-viewer
                      src={result.glb_url}
                      alt="3D model"
                      auto-rotate
                      camera-controls
                      style={{ width: '100%', height: '300px' }}
                    />
                  </div>
                )}

                {/* Download Links */}
                <div className="space-y-2">
                  {result.glb_url && (
                    <a href={result.glb_url} target="_blank" download
                       className="block text-center w-full bg-green-600 hover:bg-green-700 rounded-xl py-3 font-semibold transition">
                      ⬇️ Download GLB
                    </a>
                  )}
                  {result.obj_url && (
                    <a href={result.obj_url} target="_blank" download
                       className="block text-center w-full bg-blue-600 hover:bg-blue-700 rounded-xl py-3 font-semibold transition">
                      ⬇️ Download OBJ
                    </a>
                  )}
                </div>

                {/* Mesh Stats */}
                {result.mesh_stats && (
                  <div className="mt-4 bg-gray-800 rounded-xl p-4">
                    <h3 className="text-sm text-gray-400 mb-2">📊 Mesh Stats:</h3>
                    <pre className="text-xs text-green-400 overflow-auto max-h-40">
                      {typeof result.mesh_stats === 'string'
                        ? result.mesh_stats
                        : JSON.stringify(result.mesh_stats, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {result && !loading && !modelUrl && (
              <div className="w-full text-center">
                <p className="text-yellow-400 mb-2">⚠️ No downloadable model returned</p>
                <details className="text-left">
                  <summary className="text-gray-400 text-sm cursor-pointer">View raw response</summary>
                  <pre className="mt-2 bg-gray-800 rounded-xl p-4 text-xs overflow-auto max-h-40 text-gray-300">
                    {result.raw || JSON.stringify(result, null, 2)}
                  </pre>
                </details>
              </div>
            )}

            {!result && !loading && (
              <div className="text-gray-500 text-center flex-1 flex flex-col items-center justify-center">
                <p className="text-6xl mb-4">🤗</p>
                <p>Your 3D model will appear here</p>
                <p className="text-sm mt-2">{prov.name} generates {prov.inputType === 'Image only' ? 'meshes from images' : 'meshes from text or images'}</p>
              </div>
            )}
          </div>
        </div>

        {/* Info Panel */}
        <div className="mt-6 bg-gray-900 rounded-2xl p-6">
          <h3 className="text-lg font-semibold mb-3">ℹ️ About HuggingFace Spaces</h3>
          <p className="text-sm text-gray-400 mb-4">
            These endpoints call free HuggingFace Spaces via <code className="text-blue-400">gradio_client</code>.
            No API key is required, but Spaces may be sleeping or rate-limited.
            Optionally set <code className="text-blue-400">HF_TOKEN</code> in the backend .env for higher rate limits.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-400">TripoSR</p>
              <p className="text-white">Fast image→3D, OBJ+GLB output</p>
              <a href="https://huggingface.co/spaces/stabilityai/TripoSR" target="_blank"
                 className="text-blue-400 text-xs hover:text-blue-300">Open Space ↗</a>
            </div>
            <div>
              <p className="text-gray-400">Stable Fast 3D</p>
              <p className="text-white">High-quality textured mesh, GLB output</p>
              <a href="https://huggingface.co/spaces/stabilityai/stable-fast-3d" target="_blank"
                 className="text-blue-400 text-xs hover:text-blue-300">Open Space ↗</a>
            </div>
            <div>
              <p className="text-gray-400">Hunyuan3D-2</p>
              <p className="text-white">Text or image→3D, Tencent model</p>
              <a href="https://huggingface.co/spaces/tencent/Hunyuan3D-2" target="_blank"
                 className="text-blue-400 text-xs hover:text-blue-300">Open Space ↗</a>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}