"use client";

import { useRef, useEffect, useMemo, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
// Using native Three.js geometry instead of drei wrapper for full material control
import * as THREE from "three";
import { useShield } from "@/lib/shield-context";

const PULSE_DURATION = 600;

function ShieldMesh() {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshBasicMaterial>(null);
  const { lastPulse } = useShield();
  const { viewport } = useThree();

  const mouseRef = useRef({ x: 0, y: 0 });
  const targetRotation = useRef({ x: 0, y: 0, z: 0 });
  const pulseRef = useRef({
    intensity: 0,
    elapsed: 0,
    active: false,
    isScam: false,
  });

  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouseRef.current.y = -(e.clientY / window.innerHeight) * 2 + 1;
    };

    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  useEffect(() => {
    if (!lastPulse) return;

    pulseRef.current = {
      intensity: 1,
      elapsed: 0,
      active: true,
      isScam: lastPulse.verdict === "Scam",
    };
  }, [lastPulse]);

  const baseColor = useMemo(() => new THREE.Color("#818CF8"), []);
  const scamColor = useMemo(() => new THREE.Color("#E5484D"), []);
  const safeColor = useMemo(() => new THREE.Color("#3DD68C"), []);
  const currentColor = useMemo(() => new THREE.Color(), []);

  useFrame((state, delta) => {
    if (!meshRef.current || !materialRef.current) return;

    const t = state.clock.getElapsedTime();

    if (!prefersReducedMotion) {
      meshRef.current.rotation.y += 0.00125;
      meshRef.current.position.y = Math.sin(t * 1.5) * 0.04;

      targetRotation.current.x = mouseRef.current.y * 0.14;
      targetRotation.current.y = mouseRef.current.x * 0.14;
      targetRotation.current.z = -mouseRef.current.x * 0.04;

      meshRef.current.rotation.x = THREE.MathUtils.lerp(
        meshRef.current.rotation.x,
        targetRotation.current.x,
        0.05
      );

      meshRef.current.rotation.z = THREE.MathUtils.lerp(
        meshRef.current.rotation.z,
        targetRotation.current.z,
        0.05
      );
    }

    if (pulseRef.current.active) {
      pulseRef.current.elapsed += delta * 1000;

      const progress = Math.min(
        pulseRef.current.elapsed / PULSE_DURATION,
        1
      );

      pulseRef.current.intensity = 1 - progress * progress;

      if (progress >= 1) {
        pulseRef.current.active = false;
        pulseRef.current.intensity = 0;
      }
    }

    const intensity = pulseRef.current.intensity;
    const pulseColor = pulseRef.current.isScam
      ? scamColor
      : safeColor;

    currentColor
      .copy(baseColor)
      .lerp(pulseColor, intensity * 0.6);

    materialRef.current.color.copy(currentColor);
  });

  const scale =
    viewport.width < 6
      ? [1.1, 1.32, 0.35]
      : [1.4, 1.68, 0.45];

  return (
    <mesh
      ref={meshRef}
      scale={scale as [number, number, number]}
    >
      <icosahedronGeometry args={[2.2, 1]} />

      <meshBasicMaterial
        ref={materialRef}
        color="#818CF8"
        wireframe
        transparent
        opacity={0.85}
      />
    </mesh>
  );
}

function Lights() {
  return (
    <>
      <ambientLight intensity={0.2} />

      <directionalLight
        position={[5, 5, 5]}
        intensity={0.6}
        color="#E8F4F8"
      />
    </>
  );
}

function WebGLContextHandler({
  setContextLost,
}: {
  setContextLost: React.Dispatch<React.SetStateAction<boolean>>;
}) {
  const { gl } = useThree();

  useEffect(() => {
    const canvas = gl.domElement;

    const handleContextLost = (event: Event) => {
      event.preventDefault();

      setContextLost(true);

      console.warn("[Muhafiz] WebGL context lost");
    };

    const handleContextRestored = () => {
      setContextLost(false);

      console.log("[Muhafiz] WebGL context restored");
    };

    canvas.addEventListener(
      "webglcontextlost",
      handleContextLost
    );

    canvas.addEventListener(
      "webglcontextrestored",
      handleContextRestored
    );

    return () => {
      canvas.removeEventListener(
        "webglcontextlost",
        handleContextLost
      );

      canvas.removeEventListener(
        "webglcontextrestored",
        handleContextRestored
      );
    };
  }, [gl, setContextLost]);

  return null;
}

export function ShieldScene() {
  const [contextLost, setContextLost] = useState(false);

  return (
    <div className="relative w-full h-full">
      <Canvas
        camera={{
          position: [0, 0, 7],
          fov: 45,
        }}
        dpr={1}
        gl={{
          antialias: false,
          alpha: true,
          powerPreference: "low-power",
        }}
      >
        <WebGLContextHandler
          setContextLost={setContextLost}
        />

        <Lights />

        <ShieldMesh />
      </Canvas>

      {contextLost && (
        <div className="absolute inset-0 flex items-center justify-center text-text-secondary text-xs">
          Rendering paused
        </div>
      )}
    </div>
  );
}