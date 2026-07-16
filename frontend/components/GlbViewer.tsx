'use client';
import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three-stdlib';
import { GLTFLoader } from 'three-stdlib';

interface GlbViewerProps {
  glbUrl: string;
}

export default function GlbViewer({ glbUrl }: GlbViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const [autoRotate, setAutoRotate] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const initTimer = setTimeout(() => {
      initScene();
    }, 50);

    function initScene() {
      const w = container!.clientWidth || 600;
      const h = container!.clientHeight || 500;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0f172a);

      const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 10000);
      camera.position.set(150, 120, 150);
      camera.up.set(0, 1, 0); // GLB uses Y-up by default
      cameraRef.current = camera;

      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.domElement.style.display = 'block';
      renderer.domElement.style.touchAction = 'none';
      container!.appendChild(renderer.domElement);

      // Lights
      scene.add(new THREE.AmbientLight(0x9099aa, 0.6));
      const dl1 = new THREE.DirectionalLight(0xffffff, 1.0);
      dl1.position.set(150, 200, 150);
      scene.add(dl1);
      const dl2 = new THREE.DirectionalLight(0x60a5fa, 0.5);
      dl2.position.set(-120, 100, 60);
      scene.add(dl2);
      const dl3 = new THREE.DirectionalLight(0xf59e0b, 0.3);
      dl3.position.set(0, 50, -150);
      scene.add(dl3);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.1;
      controls.minDistance = 10;
      controls.maxDistance = 2000;
      controls.autoRotateSpeed = 3.0;
      controlsRef.current = controls;

      // Grid
      const grid = new THREE.GridHelper(300, 30, 0x4b5563, 0x1e293b);
      grid.position.y = -80;
      scene.add(grid);

      // Load GLB
      const loader = new GLTFLoader();
      let model: THREE.Group | null = null;
      let frameId: number;
      setLoaded(false);
      setLoadError(false);

      loader.load(
        glbUrl,
        (gltf) => {
          model = gltf.scene;

          // Compute bounding box and normalize
          const box = new THREE.Box3().setFromObject(model);
          const size = box.getSize(new THREE.Vector3());
          const center = box.getCenter(new THREE.Vector3());
          const maxDim = Math.max(size.x, size.y, size.z, 0.001);
          const scale = 120 / maxDim;

          model.scale.setScalar(scale);
          model.position.sub(center.multiplyScalar(scale));

          // Center on grid
          model.position.y -= 40;

          scene.add(model);
          setLoaded(true);

          // Position camera
          camera.position.set(150, 100, 150);
          camera.up.set(0, 1, 0);
          controls.target.set(0, 0, 0);
          controls.update();
        },
        undefined,
        () => setLoadError(true)
      );

      const animate = () => {
        frameId = requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      };
      animate();

      const ro = new ResizeObserver(() => {
        const nw = container!.clientWidth || 600;
        const nh = container!.clientHeight || 500;
        camera.aspect = nw / nh;
        camera.updateProjectionMatrix();
        renderer.setSize(nw, nh);
      });
      ro.observe(container!);

      return () => {
        cancelAnimationFrame(frameId);
        ro.disconnect();
        controls.dispose();
        renderer.dispose();
        if (model) {
          model.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.geometry?.dispose();
              if (Array.isArray(child.material)) {
                child.material.forEach((m) => m.dispose());
              } else {
                child.material?.dispose();
              }
            }
          });
        }
        if (container!.contains(renderer.domElement)) {
          container!.removeChild(renderer.domElement);
        }
      };
    }

    return () => {
      clearTimeout(initTimer);
    };
  }, [glbUrl]);

  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  const zoomIn = () => {
    if (cameraRef.current && controlsRef.current) {
      const cam = cameraRef.current;
      const target = controlsRef.current.target;
      const dir = new THREE.Vector3().subVectors(cam.position, target).normalize();
      const dist = cam.position.distanceTo(target);
      const newDist = Math.max(dist - 40, controlsRef.current.minDistance);
      cam.position.copy(target).addScaledVector(dir, newDist);
      controlsRef.current.update();
    }
  };
  const zoomOut = () => {
    if (cameraRef.current && controlsRef.current) {
      const cam = cameraRef.current;
      const target = controlsRef.current.target;
      const dir = new THREE.Vector3().subVectors(cam.position, target).normalize();
      const dist = cam.position.distanceTo(target);
      const newDist = Math.min(dist + 40, controlsRef.current.maxDistance);
      cam.position.copy(target).addScaledVector(dir, newDist);
      controlsRef.current.update();
    }
  };

  return (
    <div className="relative w-full h-full" style={{ minHeight: '500px' }}>
      <div ref={containerRef} className="absolute inset-0" style={{ touchAction: 'none' }} />
      {!loaded && !loadError && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ pointerEvents: 'none' }}>
          <div className="text-center">
            <p className="text-4xl mb-2 animate-pulse">⚙️</p>
            <p className="text-gray-400 text-sm">Loading AI 3D mesh...</p>
          </div>
        </div>
      )}
      {loadError && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ pointerEvents: 'none' }}>
          <p className="text-red-400 text-sm">Failed to load 3D model.</p>
        </div>
      )}
      {loaded && (
        <div className="absolute bottom-3 right-3 flex flex-col gap-2" style={{ zIndex: 10 }}>
          <button onClick={() => setAutoRotate(!autoRotate)} className={`w-10 h-10 rounded-lg text-lg flex items-center justify-center transition cursor-pointer ${autoRotate ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`} title="Auto-rotate">🔄</button>
          <button onClick={zoomIn} className="w-10 h-10 rounded-lg bg-gray-800 hover:bg-gray-700 text-lg flex items-center justify-center cursor-pointer" title="Zoom in">🔍+</button>
          <button onClick={zoomOut} className="w-10 h-10 rounded-lg bg-gray-800 hover:bg-gray-700 text-lg flex items-center justify-center cursor-pointer" title="Zoom out">🔍−</button>
        </div>
      )}
    </div>
  );
}