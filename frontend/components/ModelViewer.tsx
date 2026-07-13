'use client';
import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

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

    // Wait a tick for the container to have proper dimensions
    const initTimer = setTimeout(() => {
      initScene();
    }, 50);

    function initScene() {
      const w = container!.clientWidth || 600;
      const h = container!.clientHeight || 500;

      // Scene
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0f172a);

      // Camera — positioned at an angle so we see the model from front-top-right
      const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 10000);
      camera.position.set(150, 120, 150);
      camera.up.set(0, 0, 1); // OpenSCAD uses Z-up, so tell Three.js Z is up
      cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.touchAction = 'none'; // Required for OrbitControls
    container!.appendChild(renderer.domElement);

    // Lights
    scene.add(new THREE.AmbientLight(0x9099aa, 0.6));
    const dl1 = new THREE.DirectionalLight(0xffffff, 1.0);
    dl1.position.set(150, 150, 200);
    scene.add(dl1);
    const dl2 = new THREE.DirectionalLight(0x60a5fa, 0.5);
    dl2.position.set(-120, 60, 100);
    scene.add(dl2);
    const dl3 = new THREE.DirectionalLight(0xf59e0b, 0.3);
    dl3.position.set(0, -150, 50);
    scene.add(dl3);

    // Controls — orbit, zoom, pan
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.minDistance = 30;
    controls.maxDistance = 800;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.enableRotate = true;
    controls.autoRotateSpeed = 3.0;
    controls.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.PAN,
    };
    controlsRef.current = controls;

    // Grid on the XY plane (since Z is up)
    const grid = new THREE.GridHelper(300, 30, 0x4b5563, 0x1e293b);
    grid.rotation.x = Math.PI / 2; // Lay grid flat (XY plane)
    grid.position.z = -80;
    scene.add(grid);

    // Load STL
    const loader = new STLLoader();
    let mesh: THREE.Mesh | null = null;
    let frameId: number;
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
          color: 0x60a5fa,
          metalness: 0.2,
          roughness: 0.4,
          flatShading: false,
        });
        mesh = new THREE.Mesh(geometry, material);
        mesh.scale.setScalar(scale);
        // Center the model at origin
        mesh.position.sub(center.multiplyScalar(scale));
        scene.add(mesh);
        setLoaded(true);

        // Position camera to view the model from front-right-top
        camera.position.set(150, -150, 100);
        camera.up.set(0, 0, 1);
        controls.target.set(0, 0, 0);
        controls.update();
      },
      undefined,
      () => setLoadError(true)
    );

    // Animation loop
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Resize handler
    const ro = new ResizeObserver(() => {
      const nw = container!.clientWidth || 600;
      const nh = container!.clientHeight || 500;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    });
    ro.observe(container!);

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
      if (container!.contains(renderer.domElement)) {
        container!.removeChild(renderer.domElement);
      }
    };
    }

    return () => {
      clearTimeout(initTimer);
    };
  }, [stlUrl]);

  // Auto-rotate toggle
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  // Zoom buttons — move camera closer/farther along its viewing direction
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
      {/* Canvas container — must be behind overlays */}
      <div ref={containerRef} className="absolute inset-0" style={{ touchAction: 'none' }} />

      {/* Loading overlay — pointer-events-none so mouse goes through to canvas */}
      {!loaded && !loadError && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ pointerEvents: 'none' }}>
          <div className="text-center">
            <p className="text-4xl mb-2 animate-pulse">⚙️</p>
            <p className="text-gray-400 text-sm">Loading 3D model...</p>
          </div>
        </div>
      )}
      {loadError && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ pointerEvents: 'none' }}>
          <p className="text-red-400 text-sm">Failed to load STL. Try regenerating.</p>
        </div>
      )}

      {/* Control buttons — pointer-events auto so they're clickable */}
      {loaded && (
        <div className="absolute bottom-3 right-3 flex flex-col gap-2" style={{ zIndex: 10 }}>
          <button onClick={() => setAutoRotate(!autoRotate)} className={`w-10 h-10 rounded-lg text-lg flex items-center justify-center transition cursor-pointer ${autoRotate ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`} title="Auto-rotate">
            🔄
          </button>
          <button onClick={zoomIn} className="w-10 h-10 rounded-lg bg-gray-800 hover:bg-gray-700 text-lg flex items-center justify-center cursor-pointer" title="Zoom in">
            🔍+
          </button>
          <button onClick={zoomOut} className="w-10 h-10 rounded-lg bg-gray-800 hover:bg-gray-700 text-lg flex items-center justify-center cursor-pointer" title="Zoom out">
            🔍−
          </button>
        </div>
      )}
    </div>
  );
}