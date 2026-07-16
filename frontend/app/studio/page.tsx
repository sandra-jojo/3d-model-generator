'use client';
import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';

interface SceneObject {
  id: string;
  type: 'cube' | 'sphere' | 'cylinder' | 'cone' | 'union' | 'difference';
  params: {
    size?: number;
    radius?: number;
    height?: number;
    x?: number;
    y?: number;
    z?: number;
    rotation?: [number, number, number];
    color?: string;
  };
  children?: SceneObject[];
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  tokens?: number;
}

export default function StudioPage() {
  const [scene, setScene] = useState<{ objects: SceneObject[] }>({ objects: [] });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState('');
  const [selectedObj, setSelectedObj] = useState<string | null>(null);
  const [tokenStats, setTokenStats] = useState({ total: 0, parametric: 0, llm: 0 });
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const objIdCounter = useRef(0);
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendToAI = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);
    setError('');

    try {
      // Sliding window: only send last 3 messages
      const recentMessages = messages.slice(-3).map(m => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API}/studio/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          scene: scene,
          history: recentMessages,
        }),
      });
      const data = await res.json();

      if (data.error) {
        setError(data.error);
        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.error}` }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.reply,
          model: data.model_used,
          tokens: data.tokens_used,
        }]);

        // Track tokens
        setTokenStats(prev => ({
          total: prev.total + (data.tokens_used || 0),
          parametric: prev.parametric + (data.model_used === 'parametric' ? 1 : 0),
          llm: prev.llm + (data.model_used !== 'parametric' ? 1 : 0),
        }));

        // Apply actions to scene
        if (data.actions) {
          setScene(prevScene => {
            const newScene = { ...prevScene, objects: [...prevScene.objects] };
            for (const action of data.actions) {
              if (action.type === 'add' && action.object) {
                newScene.objects.push(action.object);
              } else if (action.type === 'delete') {
                // Backend sends {"type":"delete","id":"obj_1"}
                const oid = action.id || action.object_id;
                newScene.objects = newScene.objects.filter(o => o.id !== oid);
              } else if (action.type === 'modify' && (action.object_id || action.id) && action.changes) {
                const oid = action.id || action.object_id;
                newScene.objects = newScene.objects.map(o =>
                  o.id === oid ? { ...o, params: { ...o.params, ...action.changes } } : o
                );
              } else if (action.type === 'move' && (action.id || action.object_id) && action.params) {
                const oid = action.id || action.object_id;
                newScene.objects = newScene.objects.map(o =>
                  o.id === oid ? { ...o, params: { ...o.params, ...action.params } } : o
                );
              } else if (action.type === 'rotate' && (action.id || action.object_id) && action.params) {
                const oid = action.id || action.object_id;
                newScene.objects = newScene.objects.map(o =>
                  o.id === oid ? { ...o, params: { ...o.params, ...action.params } } : o
                );
              } else if (action.type === 'scale' && (action.id || action.object_id) && action.factor) {
                const oid = action.id || action.object_id;
                newScene.objects = newScene.objects.map(o => {
                  if (o.id !== oid) return o;
                  const f = action.factor;
                  const p = { ...o.params };
                  if (p.size) p.size = Math.round(p.size * f);
                  if (p.radius) p.radius = Math.round(p.radius * f);
                  if (p.height) p.height = Math.round(p.height * f);
                  if (p.w) p.w = Math.round(p.w * f);
                  if (p.d) p.d = Math.round(p.d * f);
                  if (p.h) p.h = Math.round(p.h * f);
                  return { ...o, params: p };
                });
              } else if (action.type === 'clear') {
                newScene.objects = [];
              }
            }
            return newScene;
          });
        }
      }
    } catch (e) {
      setError('Connection failed: ' + (e instanceof Error ? e.message : String(e)));
    }
    setLoading(false);
  };

  const generatePreview = async () => {
    if (scene.objects.length === 0) { setPreview(''); return; }
    try {
      const res = await fetch(`${API}/studio/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene }),
      });
      const data = await res.json();
      if (data.image) {
        setPreview('data:image/png;base64,' + data.image);
      }
    } catch {
      /* silent fail for preview */
    }
  };

  // Auto-preview when scene changes
  useEffect(() => {
    const timer = setTimeout(() => generatePreview(), 500);
    return () => clearTimeout(timer);
  }, [scene]);

  const exportSTL = async () => {
    try {
      const res = await fetch(`${API}/studio/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene, format: 'stl' }),
      });
      const data = await res.json();
      if (data.stl_path) {
        window.open(`${API}/download/stl`, '_blank');
      }
    } catch (err) {
      setError('Export failed: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  const loadTemplate = async (name: string) => {
    try {
      const res = await fetch(`${API}/studio/templates`);
      const data = await res.json();
      const template = data.templates?.[name];
      if (template) {
        // Template structure is {name, description, scene: {objects: [...]}}
        // We need to load the .scene property, not the wrapper
        const sceneData = template.scene || template;
        setScene(sceneData);
        setMessages(prev => [...prev, { role: 'assistant', content: `Loaded template: ${template.name || name}`, model: 'system', tokens: 0 }]);
      }
    } catch { /* silent */ }
  };

  const addPrimitive = (type: SceneObject['type']) => {
    const id = `obj_${++objIdCounter.current}`;
    const defaults: Record<string, SceneObject['params']> = {
      cube: { size: 20, x: 0, y: 0, z: 0 },
      sphere: { radius: 15, x: 0, y: 0, z: 0 },
      cylinder: { radius: 10, height: 30, x: 0, y: 0, z: 0 },
      cone: { radius: 15, height: 25, x: 0, y: 0, z: 0 },
    };
    setScene(prev => ({
      ...prev,
      objects: [...prev.objects, { id, type, params: defaults[type] || {} }],
    }));
  };

  const deleteObject = (id: string) => {
    setScene(prev => ({ ...prev, objects: prev.objects.filter(o => o.id !== id) }));
    if (selectedObj === id) setSelectedObj(null);
  };

  const clearScene = () => {
    setScene({ objects: [] });
    setPreview('');
  };

  const updateParam = (id: string, key: string, value: number) => {
    setScene(prev => ({
      ...prev,
      objects: prev.objects.map(o => o.id === id ? { ...o, params: { ...o.params, [key]: value } } : o),
    }));
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-4">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">🛠️ AI Design Studio</h1>
          <div className="flex gap-3 items-center text-sm">
            <span className="bg-gray-800 px-3 py-1 rounded-lg">
              📊 Tokens: <span className="text-green-400">{tokenStats.total}</span>
            </span>
            <span className="bg-gray-800 px-3 py-1 rounded-lg">
              ⚡ Parametric: <span className="text-blue-400">{tokenStats.parametric}</span>
            </span>
            <span className="bg-gray-800 px-3 py-1 rounded-lg">
              🧠 LLM calls: <span className="text-orange-400">{tokenStats.llm}</span>
            </span>
            <Link href="/" className="text-blue-400 hover:text-blue-300">← Home</Link>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-4 h-[calc(100vh-100px)]">
          {/* Left: Object List */}
          <div className="col-span-2 bg-gray-900 rounded-xl p-4 overflow-auto">
            <h3 className="font-semibold mb-3 text-sm">Primitives</h3>
            <div className="space-y-2 mb-4">
              {['cube', 'sphere', 'cylinder', 'cone'].map(t => (
                <button
                  key={t}
                  onClick={() => addPrimitive(t as SceneObject['type'])}
                  className="w-full bg-gray-800 hover:bg-gray-700 rounded-lg py-2 text-sm font-medium capitalize"
                >+ {t}</button>
              ))}
            </div>

            <h3 className="font-semibold mb-3 text-sm">Templates</h3>
            <div className="space-y-2 mb-4">
              <button onClick={() => loadTemplate('empty')} className="w-full bg-gray-800 hover:bg-gray-700 rounded-lg py-2 text-sm">Empty Scene</button>
              <button onClick={() => loadTemplate('gear_assembly')} className="w-full bg-gray-800 hover:bg-gray-700 rounded-lg py-2 text-sm">Gear Assembly</button>
              <button onClick={() => loadTemplate('phone_stand')} className="w-full bg-gray-800 hover:bg-gray-700 rounded-lg py-2 text-sm">Phone Stand</button>
            </div>

            <h3 className="font-semibold mb-3 text-sm">Objects ({scene.objects.length})</h3>
            <div className="space-y-1">
              {scene.objects.map(obj => (
                <div
                  key={obj.id}
                  onClick={() => setSelectedObj(obj.id)}
                  className={`flex items-center justify-between p-2 rounded-lg cursor-pointer text-sm ${selectedObj === obj.id ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                >
                  <span className="truncate">{obj.type} #{obj.id.slice(-4)}</span>
                  <button onClick={(e) => { e.stopPropagation(); deleteObject(obj.id); }} className="text-red-400 hover:text-red-300 ml-1">✕</button>
                </div>
              ))}
            </div>

            {scene.objects.length > 0 && (
              <button onClick={clearScene} className="w-full mt-4 bg-red-900 hover:bg-red-800 rounded-lg py-2 text-sm font-medium">Clear All</button>
            )}
          </div>

          {/* Center: 3D Preview + Properties */}
          <div className="col-span-6 flex flex-col gap-4">
            {/* Preview */}
            <div className="flex-1 bg-gray-900 rounded-xl p-4 flex flex-col items-center justify-center min-h-0">
              {preview ? (
                <img src={preview} alt="3D Preview" className="rounded-lg max-h-full max-w-full object-contain" />
              ) : scene.objects.length === 0 ? (
                <div className="text-gray-500 text-center">
                  <p className="text-5xl mb-3">🛠️</p>
                  <p>Add primitives or ask the AI agent to design something</p>
                </div>
              ) : (
                <div className="text-center">
                  <p className="text-3xl mb-2 animate-pulse">⚙️</p>
                  <p className="text-gray-400 text-sm">Rendering preview...</p>
                </div>
              )}
            </div>

            {/* Properties Panel */}
            {selectedObj && (() => {
              const obj = scene.objects.find(o => o.id === selectedObj);
              if (!obj) return null;
              return (
                <div className="bg-gray-900 rounded-xl p-4 max-h-48 overflow-auto">
                  <h3 className="font-semibold mb-2 text-sm">Properties: {obj.type}</h3>
                  <div className="grid grid-cols-3 gap-2">
                    {obj.type === 'cube' && (
                      <>
                        <PropSlider label="Size" value={obj.params.size || 20} min={1} max={100} onChange={v => updateParam(obj.id, 'size', v)} />
                      </>
                    )}
                    {(obj.type === 'sphere' || obj.type === 'cylinder' || obj.type === 'cone') && (
                      <>
                        <PropSlider label="Radius" value={obj.params.radius || 10} min={1} max={50} onChange={v => updateParam(obj.id, 'radius', v)} />
                        {(obj.type === 'cylinder' || obj.type === 'cone') && (
                          <PropSlider label="Height" value={obj.params.height || 20} min={1} max={100} onChange={v => updateParam(obj.id, 'height', v)} />
                        )}
                      </>
                    )}
                    <PropSlider label="X" value={obj.params.x || 0} min={-100} max={100} onChange={v => updateParam(obj.id, 'x', v)} />
                    <PropSlider label="Y" value={obj.params.y || 0} min={-100} max={100} onChange={v => updateParam(obj.id, 'y', v)} />
                    <PropSlider label="Z" value={obj.params.z || 0} min={-100} max={100} onChange={v => updateParam(obj.id, 'z', v)} />
                  </div>
                </div>
              );
            })()}

            {/* Export bar */}
            <div className="flex gap-2">
              <button onClick={exportSTL} disabled={scene.objects.length === 0}
                className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded-xl py-2 font-semibold text-sm">
                ⬇️ Export STL
              </button>
              <button onClick={generatePreview} disabled={scene.objects.length === 0}
                className="flex-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 rounded-xl py-2 font-semibold text-sm">
                🔄 Refresh Preview
              </button>
            </div>
          </div>

          {/* Right: AI Chat */}
          <div className="col-span-4 bg-gray-900 rounded-xl flex flex-col h-full">
            <div className="p-3 border-b border-gray-800 flex items-center gap-2">
              <span className="text-lg">🤖</span>
              <span className="font-semibold text-sm">AI Design Agent</span>
              <span className="text-xs text-gray-500 ml-auto">Ollama GLM4</span>
            </div>

            {/* Chat messages */}
            <div className="flex-1 overflow-auto p-3 space-y-3">
              {messages.length === 0 && (
                <div className="text-gray-500 text-sm text-center mt-8">
                  <p className="mb-3">Try saying:</p>
                  <div className="space-y-2">
                    {['Add a cube 30mm', 'Add a sphere 20mm radius', 'Create a cylinder 50mm tall', 'Design a phone stand', 'Make everything bigger'].map(s => (
                      <button key={s} onClick={() => setInput(s)} className="block w-full text-left bg-gray-800 hover:bg-gray-700 rounded-lg p-2 text-xs text-gray-300">&quot;{s}&quot;</button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`rounded-lg p-2 text-sm ${msg.role === 'user' ? 'bg-blue-900 ml-8' : 'bg-gray-800 mr-8'}`}>
                  <p className={msg.role === 'user' ? 'text-blue-100' : 'text-gray-200'}>{msg.content}</p>
                  {msg.role === 'assistant' && msg.model && (
                    <div className="flex gap-2 mt-1 text-xs">
                      <span className={msg.model === 'parametric' ? 'text-blue-400' : 'text-orange-400'}>
                        {msg.model === 'parametric' ? '⚡ parametric (0 tokens)' : `🧠 ${msg.model} (${msg.tokens || 0} tokens)`}
                      </span>
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="bg-gray-800 rounded-lg p-2 text-sm text-gray-400 animate-pulse">🤖 Thinking...</div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Error */}
            {error && <div className="px-3 py-1 bg-red-900 text-red-200 text-xs">{error}</div>}

            {/* Input */}
            <div className="p-3 border-t border-gray-800 flex gap-2">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendToAI()}
                placeholder="Tell the AI what to do..."
                className="flex-1 bg-gray-800 rounded-lg px-3 py-2 text-sm text-white"
                disabled={loading}
              />
              <button
                onClick={sendToAI}
                disabled={loading || !input.trim()}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 rounded-lg px-4 py-2 text-sm font-semibold"
              >Send</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

function PropSlider({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (v: number) => void }) {
  return (
    <div>
      <label className="text-xs text-gray-400">{label}: {value}mm</label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full"
      />
    </div>
  );
}