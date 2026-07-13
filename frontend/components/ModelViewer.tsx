'use client';
import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';

interface ModelViewerProps {
  stlUrl: string;
}

export default function ModelViewer({ stlUrl }: ModelViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const [autoRotate, setAutoRotate] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const w = container.clientWidth || 600;
    const h = container.clientHeight || 500;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);

    // Camera
    const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 10000);
    camera.position.set(100, 80, 140);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';

    // Lights
    scene.add(new THREE.AmbientLight(0x8899aa, 0.5));
    const dl1 = new THREE.DirectionalLight(0xffffff, 1.0);
    dl1.position.set(120, 120, 100);
    scene.add(dl1);
    const dl2 = new THREE.DirectionalLight(0x3b82f6, 0.5);
    dl2.position.set(-100, 40, -80);
    scene.add(dl2);
    const dl3 = new THREE.DirectionalLight(0xf59e0b, 0.3);
    dl3.position.set(0, -100, 50);
    scene.add(dl3);

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.minDistance = 30;
    controls.maxDistance = 600;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.enableRotate = true;
    controls.autoRotateSpeed = 3.0;
    controlsRef.current = controls;

    // Grid + axes
    const grid = new THREE.GridHelper(300, 30, 0x4b5563, 0x1e293b);
    grid.position.y = -60;
    scene.add(grid);
    scene.add(new THREE.AxesHelper(80));

    // Load STL
    const loader = new STLLoader();
    let mesh: THREE.Mesh | null = null;
    setLoaded(false);
    setLoadError(false);

    loader.load(
      stlUrl,
      (geometry) => {
        geometry.computeBoundingBox();
        geometry.computeVertexNormals();
        const bb = geometry.boundingBox!;
        const center = bb.getCenter(new THREE.Vector3());
        const size = bb.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z, 1);
        const scale = 120 / maxDim;

        const material = new THREE.MeshStandardMaterial({
          color: 0x3b82f6,
          metalness: 0.3,
          roughness: 0.35,
          flatShading: false,
        });
        mesh = new THREE.Mesh(geometry, material);
        mesh.scale.setScalar(scale);
        mesh.position.sub(center.multiplyScalar(scale));
        mesh.position.y -= 20;
        scene.add(mesh);
        setLoaded(true);

        camera.position.set(100, 80, 140);
        controls.target.set(0, 0, 0);
        controls.update();
      },
      undefined,
      () => setLoadError(true)
    );

    // Animation loop
    let frameId: number;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Resize handler — use ResizeObserver for reliable sizing
    const ro = new ResizeObserver(() => {
      const nw = container.clientWidth || 600;
      const nh = container.clientHeight || 500;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    });
    ro.observe(container);

    // Cleanup
    return () => {
      cancelAnimationFrame(frameId);
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
      if (mesh) {
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      }
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [stlUrl]);

  // Auto-rotate toggle
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  // Zoom buttons
  const zoomIn = () => {
    if (cameraRef.current && controlsRef.current) {
      const dir = new THREE.Vector3();
      cameraRef.current.getWorldDirection(dir);
      cameraRef.current.position.addScaledVector(dir, 30);
      controlsRef.current.update();
    }
  };
  const zoomOut = () => {
    if (cameraRef.current && controlsRef.current) {
      const dir = new THREE.Vector3();
      cameraRef.current.getWorldDirection(dir);
      cameraRef.current.position.addScaledVector(dir, -30);
      controlsRef.current.update();
    }
  };

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" style={{ minHeight: '500px' }} />
      {/* Loading / error overlay */}
      {!loaded && !loadError && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <p className="text-4xl mb-2 animate-pulse">⚙️</p>
            <p className="text-gray-400 text-sm">Loading 3D model...</p>
          </div>
        </div>
      )}
      {loadError && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-red-400 text-sm">Failed to load STL. Try regenerating.</p>
        </div>
      )}
      {/* Control buttons */}
      {loaded && (
        <div className="absolute bottom-3 right-3 flex flex-col gap-2">
          <button onClick={() => setAutoRotate(!autoRotate)} className={`w-10 h-10 rounded-lg text-lg flex items-center justify-center transition ${autoRotate ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`} title="Auto-rotate">
            🔄
          </button>
          <button onClick={zoomIn} className="w-10 h-10 rounded-lg bg-gray-800 hover:bg-gray-700 text-lg flex items-center justify-center" title="Zoom in">
            🔍➕
          </button>
          <button onClick={zoomOut} className="w-10 h-10 rounded-lg bg-gray-800 hover:bg-gray-700 text-lg flex items-center justify-center" title="Zoom out">
            🔍➖
          </button>
        </div>
      )}
    </div>
  );
}