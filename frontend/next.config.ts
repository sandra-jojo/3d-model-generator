import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Deduplicate three.js — prevents "Multiple instances of Three.js"
  // via Turbopack resolve aliases
  turbopack: {
    resolveAlias: {
      three: { browser: "./node_modules/three/build/three.module.js" },
    },
  },
};

export default nextConfig;