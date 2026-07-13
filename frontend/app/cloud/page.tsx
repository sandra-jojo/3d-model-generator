'use client';
import { useState, useRef } from 'react';
import Link from 'next/link';

type Provider = 'meshy' | 'tripo';
type GenMode = 'text' | 'image';

interface TaskResult {
  status: string;
  progress: number;
  modelUrl?: string;
  modelUrls?: Record<string, string>;
  error?: string;
}

export default function CloudGenerate() {
  const [provider, setProvider] = useState<Provider>('meshy');
  const [genMode, setGenMode] = useState<GenMode>('text');
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [polling, setPolling] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const generate = async () => {
    setLoading(true); setError(''); setResult(null); setProgress(0); setStatus('Creating task...');

    try {
      const isText = genMode === 'text';
      const endpoint = provider === 'meshy'
        ? `${API}/${isText ? 'meshy/text-to-3d' : 'meshy/image-to-3d'}`
        : `${API}/${isText ? 'tripo/text-to-model' : 'tripo/image-to-model'}`;

      const body: Record<string, string> = {};
      const imageFile = !isText ? fileRef.current?.files?.[0] : undefined;
      if (isText) {
        body.prompt = prompt;
        if (negativePrompt) body.negative_prompt = negativePrompt;
      } else {
        if (!imageFile) {
          setError('Please upload an image!');
          setLoading(false);
          return;
        }
      }

      const res = isText
        ? await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        : await fetch(endpoint, { method: 'POST', body: await createFormData(imageFile) });

      const data = await res.json();

      if (data.error) {
        setError(data.error);
        setLoading(false);
        return;
      }

      // The backend handles polling and returns final result
      if (data.model_url || data.model_urls) {
        setResult({
          status: 'SUCCEEDED',
          progress: 100,
          modelUrl: data.model_url,
          modelUrls: data.model_urls,
        });
        setStatus('Done!');
      } else if (data.task_id) {
        // Need to poll manually
        setStatus('Task created, polling...');
        setPolling(true);
        pollTask(data.task_id);
      } else {
        setError('Unexpected response: ' + JSON.stringify(data));
      }
    } catch (e) {
      setError('Error: ' + (e instanceof Error ? e.message : String(e)));
    }
    setLoading(false);
  };

  const pollTask = async (taskId: string) => {
    const pollEndpoint = `${API}/${provider}/task/${taskId}`;
    let attempts = 0;
    const maxAttempts = 120; // 10 minutes max

    const interval = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch(pollEndpoint);
        const data = await res.json();

        setProgress(data.progress || 0);
        setStatus(`${data.status || 'processing'}... ${data.progress || 0}%`);

        if (data.status === 'SUCCEEDED' || data.status === 'success') {
          setResult({
            status: 'SUCCEEDED',
            progress: 100,
            modelUrl: data.model_url,
            modelUrls: data.model_urls,
          });
          setStatus('Done!');
          setPolling(false);
          clearInterval(interval);
        } else if (data.status === 'FAILED' || data.status === 'failed') {
          setError(data.error || 'Generation failed');
          setPolling(false);
          clearInterval(interval);
        } else if (attempts >= maxAttempts) {
          setError('Timeout: task took too long');
          setPolling(false);
          clearInterval(interval);
        }
      } catch (e) {
        // Network error, keep trying
        if (attempts >= maxAttempts) {
          setError('Polling failed: ' + (e instanceof Error ? e.message : String(e)));
          setPolling(false);
          clearInterval(interval);
        }
      }
    }, 5000);
  };

  const createFormData = async (file: File | undefined) => {
    const formData = new FormData();
    if (file) formData.append('file', file);
    return formData;
  };

  const modelUrl = result?.modelUrl || result?.modelUrls?.glb || result?.modelUrls?.fbx;

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">☁️ AI Cloud 3D Generation</h1>
          <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">← Back to Local Gen</Link>
        </div>

        {/* Provider Selection */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => { setProvider('meshy'); setResult(null); setError(''); }}
            className={`flex-1 py-4 rounded-xl font-semibold transition ${provider === 'meshy' ? 'bg-indigo-600' : 'bg-gray-800 hover:bg-gray-700'}`}
          >
            🎨 Meshy AI
            <p className="text-xs text-gray-300 mt-1">Text & Image → High-quality 3D mesh</p>
          </button>
          <button
            onClick={() => { setProvider('tripo'); setResult(null); setError(''); }}
            className={`flex-1 py-4 rounded-xl font-semibold transition ${provider === 'tripo' ? 'bg-orange-600' : 'bg-gray-800 hover:bg-gray-700'}`}
          >
            🚀 Tripo AI
            <p className="text-xs text-gray-300 mt-1">Text & Image → Fast 3D model generation</p>
          </button>
        </div>

        {/* Mode Selection */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setGenMode('text')}
            className={`flex-1 py-3 rounded-xl font-semibold ${genMode === 'text' ? 'bg-blue-600' : 'bg-gray-800'}`}
          >📝 Text → 3D</button>
          <button
            onClick={() => setGenMode('image')}
            className={`flex-1 py-3 rounded-xl font-semibold ${genMode === 'image' ? 'bg-purple-600' : 'bg-gray-800'}`}
          >📸 Image → 3D</button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Input Panel */}
          <div className="bg-gray-900 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-4">
              {genMode === 'text' ? '💬 Text Prompt' : '📸 Image Upload'}
            </h2>

            {genMode === 'text' ? (
              <>
                <textarea
                  className="w-full bg-gray-800 rounded-xl p-4 text-white resize-none h-24 mb-4"
                  placeholder={provider === 'meshy' ? "e.g. a monster mask, a futuristic chair..." : "e.g. a sports car, a fantasy castle..."}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                />
                <textarea
                  className="w-full bg-gray-800 rounded-xl p-4 text-white resize-none h-16 mb-4"
                  placeholder="Negative prompt (optional): e.g. blurry, low quality..."
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                />
              </>
            ) : (
              <div className="mb-4">
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  className="w-full bg-gray-800 rounded-xl p-4 text-white mb-4"
                />
                <p className="text-gray-400 text-sm">
                  Upload an image. {provider === 'meshy' ? 'Meshy will generate a 3D model from it.' : 'Tripo will generate a 3D model from it.'}
                </p>
              </div>
            )}

            <button
              onClick={generate}
              disabled={loading || polling || (genMode === 'text' && !prompt)}
              className={`w-full rounded-xl py-3 font-semibold transition disabled:bg-gray-600 ${
                provider === 'meshy' ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-orange-600 hover:bg-orange-700'
              }`}
            >
              {loading || polling ? `⏳ ${status}` : `🚀 Generate with ${provider === 'meshy' ? 'Meshy' : 'Tripo'}`}
            </button>

            {/* Progress Bar */}
            {(loading || polling) && (
              <div className="mt-4">
                <div className="bg-gray-800 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${provider === 'meshy' ? 'bg-indigo-500' : 'bg-orange-500'}`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-center text-sm text-gray-400 mt-2">{progress}%</p>
              </div>
            )}

            {/* Status */}
            {status && !loading && !polling && (
              <div className="mt-4 bg-blue-900 rounded-xl p-3 text-sm text-blue-200">{status}</div>
            )}

            {/* Error */}
            {error && (
              <div className="mt-4 bg-red-900 rounded-xl p-3 text-sm text-red-200">{error}</div>
            )}
          </div>

          {/* Result Panel */}
          <div className="bg-gray-900 rounded-2xl p-6 flex flex-col items-center justify-center min-h-96">
            <h2 className="text-xl font-semibold mb-4">🧊 3D Result</h2>

            {(loading || polling) && (
              <div className="text-center">
                <p className="text-5xl mb-4 animate-pulse">⚙️</p>
                <p className="text-gray-400">{status}</p>
              </div>
            )}

            {result && modelUrl && !loading && !polling && (
              <div className="w-full">
                {/* Model Preview */}
                <div className="bg-gray-800 rounded-xl p-4 mb-4">
                  <p className="text-green-400 text-sm mb-2">✅ Generation Complete!</p>
                  <p className="text-gray-400 text-sm mb-2">Model URL:</p>
                  <a href={modelUrl} target="_blank" className="text-blue-400 text-sm break-all hover:text-blue-300">
                    {modelUrl.substring(0, 80)}...
                  </a>
                </div>

                {/* Download Links */}
                <div className="space-y-2">
                  {result.modelUrls?.glb && (
                    <a href={result.modelUrls.glb} download className="block text-center w-full bg-green-600 hover:bg-green-700 rounded-xl py-3 font-semibold transition">
                      ⬇️ Download GLB
                    </a>
                  )}
                  {result.modelUrls?.fbx && (
                    <a href={result.modelUrls.fbx} download className="block text-center w-full bg-blue-600 hover:bg-blue-700 rounded-xl py-3 font-semibold transition">
                      ⬇️ Download FBX
                    </a>
                  )}
                  {result.modelUrls?.obj && (
                    <a href={result.modelUrls.obj} download className="block text-center w-full bg-purple-600 hover:bg-purple-700 rounded-xl py-3 font-semibold transition">
                      ⬇️ Download OBJ
                    </a>
                  )}
                  {result.modelUrls?.usdz && (
                    <a href={result.modelUrls.usdz} download className="block text-center w-full bg-pink-600 hover:bg-pink-700 rounded-xl py-3 font-semibold transition">
                      ⬇️ Download USDZ
                    </a>
                  )}
                  {result.modelUrl && !result.modelUrls && (
                    <a href={result.modelUrl} download className="block text-center w-full bg-green-600 hover:bg-green-700 rounded-xl py-3 font-semibold transition">
                      ⬇️ Download Model
                    </a>
                  )}
                </div>

                {/* Embed 3D viewer for GLB */}
                {result.modelUrls?.glb && (
                  <div className="mt-4 bg-gray-800 rounded-xl p-4">
                    <p className="text-gray-400 text-sm mb-2">3D Preview:</p>
                    <model-viewer
                      src={result.modelUrls.glb}
                      alt="3D model"
                      auto-rotate
                      camera-controls
                      style={{ width: '100%', height: '300px' }}
                    />
                  </div>
                )}
              </div>
            )}

            {!result && !loading && !polling && (
              <div className="text-gray-500 text-center">
                <p className="text-6xl mb-4">☁️</p>
                <p>Your AI-generated 3D model will appear here</p>
                <p className="text-sm mt-2">
                  {provider === 'meshy' ? 'Meshy' : 'Tripo'} generates high-quality textured meshes
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Info Panel */}
        <div className="mt-6 bg-gray-900 rounded-2xl p-6">
          <h3 className="text-lg font-semibold mb-3">ℹ️ About {provider === 'meshy' ? 'Meshy' : 'Tripo'} API</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-400">Quality</p>
              <p className="text-white">{provider === 'meshy' ? 'High-fidelity textured meshes' : 'Fast draft + refine workflow'}</p>
            </div>
            <div>
              <p className="text-gray-400">Output Formats</p>
              <p className="text-white">{provider === 'meshy' ? 'GLB, FBX, OBJ, USDZ' : 'GLB, FBX, USDZ'}</p>
            </div>
            <div>
              <p className="text-gray-400">Pricing</p>
              <p className="text-white">{provider === 'meshy' ? 'Credits per task' : 'Credits per task'}</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-4">
            ⚠️ These are paid cloud APIs. Set MESHY_API_KEY and TRIPO_API_KEY in the backend .env to enable.
            Get keys at <a href="https://www.meshy.ai/settings/api" target="_blank" className="text-blue-400">Meshy</a> or <a href="https://platform.tripo3d.ai/api-keys" target="_blank" className="text-blue-400">Tripo</a>
          </p>
        </div>
      </div>
    </main>
  );
}