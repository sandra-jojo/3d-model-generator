'use client';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';

interface ModelViewerProps {
  stlUrl: string;
  width?: string;
  height?: string;
}

export default function ModelViewer({ stlUrl, width = '100%', height = '400px' }: ModelViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111827);

    // Camera
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      10000
    );
    camera.position.set(80, 80, 120);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0x6b7280, 0.6);
    scene.add(ambientLight);
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
    dirLight.position.set(100, 100, 100);
    scene.add(dirLight);
    const dirLight2 = new THREE.DirectionalLight(0x60a5fa, 0.4);
    dirLight2.position.set(-100, 50, -100);
    scene.add(dirLight2);

    // Controls — orbit, zoom, pan with mouse
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 20;
    controls.maxDistance = 500;
    controls.autoRotate = false;
    controls.autoRotateSpeed = 2.0;

    // Grid + axes
    const grid = new THREE.GridHelper(200, 20, 0x374151, 0x1f2937);
    scene.add(grid);
    const axes = new THREE.AxesHelper(50);
    scene.add(axes);

    // Load STL
    const loader = new STLLoader();
    let mesh: THREE.Mesh | null = null;

    loader.load(
      stlUrl,
      (geometry) => {
        // Center and scale the model to fit
        geometry.computeBoundingBox();
        const bb = geometry.boundingBox!;
        const center = bb.getCenter(new THREE.Vector3());
        const size = bb.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 80 / maxDim;

        const material = new THREE.MeshPhongMaterial({
          color: 0x60a5fa,
          shininess: 80,
          specular: 0x111111,
          flatShading: false,
        });
        mesh = new THREE.Mesh(geometry, material);
        mesh.scale.setScalar(scale);
        mesh.position.sub(center.multiplyScalar(scale));

        scene.add(mesh);

        // Frame the camera around the model
        camera.position.set(80, 80, 120);
        controls.target.set(0, 0, 0);
        controls.update();
      },
      undefined,
      (error) => {
        console.error('STL load error:', error);
      }
    );

    // Animation loop
    let frameId: number;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Resize handler
    const handleResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', handleResize);
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

  return (
    <div
      ref={containerRef}
      style={{ width, height, borderRadius: '12px', overflow: 'hidden' }}
    />
  );
}