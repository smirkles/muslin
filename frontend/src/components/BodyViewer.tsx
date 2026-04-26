"use client";

import { useEffect, useRef, useState } from "react";
import {
  AmbientLight,
  Box3,
  DirectionalLight,
  Group,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  Scene,
  Vector3,
  WebGLRenderer,
} from "three";
import { GLTFLoader, OrbitControls } from "three-stdlib";
import type { Measurements } from "../lib/measurements";
import type { BodyGender } from "../store/wizard";

// ── Morph configuration ───────────────────────────────────────────────────────
//
// Source: bodyapps-viz femaleconfig.json + testconfig.json (LGPL v3, Fashiontec)
// Morph targets are stored as deltas from the default body shape.
// Formula: influence = (user_cm - model_default) / (model_max - model_min)
//   → 0 at default body, positive = larger, negative = smaller (Three.js allows <0)

type MorphMapping = {
  index: number;   // morph target index in the GLB
  modelMin: number;
  modelMax: number;
  modelDefault: number;
};

const FEMALE_MORPHS: Partial<Record<keyof Measurements, MorphMapping>> = {
  height_cm: { index: 0,  modelMin: 110, modelMax: 210, modelDefault: 155  },
  bust_cm:   { index: 5,  modelMin: 70,  modelMax: 100, modelDefault: 85   }, // "Breast"
  waist_cm:  { index: 11, modelMin: 65,  modelMax: 85,  modelDefault: 75   },
  hip_cm:    { index: 12, modelMin: 86,  modelMax: 114, modelDefault: 100  },
};

const MALE_MORPHS: Partial<Record<keyof Measurements, MorphMapping>> = {
  height_cm: { index: 0,  modelMin: 120,    modelMax: 190,    modelDefault: 160   },
  bust_cm:   { index: 1,  modelMin: 83.76,  modelMax: 130.56, modelDefault: 96.67 }, // "Chest"
  waist_cm:  { index: 8,  modelMin: 64,     modelMax: 100,    modelDefault: 76.66 },
  hip_cm:    { index: 12, modelMin: 96,     modelMax: 124,    modelDefault: 112   },
};

function computeInfluences(
  measurements: Measurements | null,
  gender: BodyGender,
): Record<number, number> {
  if (!measurements) return {};
  const config = gender === "female" ? FEMALE_MORPHS : MALE_MORPHS;
  const result: Record<number, number> = {};
  for (const [field, mapping] of Object.entries(config)) {
    const value = measurements[field as keyof Measurements];
    if (value === undefined || value === null) continue;
    const { index, modelMin, modelMax, modelDefault } = mapping as MorphMapping;
    result[index] = (value - modelDefault) / (modelMax - modelMin);
  }
  return result;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface BodyViewerProps {
  measurements: Measurements | null;
  gender: BodyGender;
  onGenderChange: (g: BodyGender) => void;
  className?: string;
}

type ViewerStatus = "loading" | "success" | "error";

export function BodyViewer({ measurements, gender, onGenderChange, className }: BodyViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<ViewerStatus>("loading");

  const rendererRef = useRef<WebGLRenderer | null>(null);
  const controlsRef = useRef<InstanceType<typeof OrbitControls> | null>(null);
  const animFrameRef = useRef<number>(0);
  // Keep mesh reference so morph influences can be updated without reloading
  const meshRef = useRef<Mesh | null>(null);

  // ── Load model whenever gender changes ──────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    // Dispose previous renderer if any
    cancelAnimationFrame(animFrameRef.current);
    controlsRef.current?.dispose();
    rendererRef.current?.dispose();
    controlsRef.current = null;
    rendererRef.current = null;
    meshRef.current = null;
    if (containerRef.current) containerRef.current.innerHTML = "";

    (async () => {
      try {
        const container = containerRef.current;
        if (!container) return;

        const w = container.clientWidth || 320;
        const h = container.clientHeight || 420;

        const scene = new Scene();
        const camera = new PerspectiveCamera(40, w / h, 0.01, 100);

        const renderer = new WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        scene.add(new AmbientLight(0xffffff, 0.7));
        const dirLight = new DirectionalLight(0xffffff, 0.9);
        dirLight.position.set(1, 3, 2);
        scene.add(dirLight);
        const rimLight = new DirectionalLight(0xfff5ee, 0.4);
        rimLight.position.set(-2, 1, -1);
        scene.add(rimLight);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.autoRotate = true;
        controls.autoRotateSpeed = 1.2;
        controls.enablePan = false;
        controls.minDistance = 0.5;
        controls.maxDistance = 5;
        controlsRef.current = controls;

        // Load GLB from public/models — served at root by Next.js
        const gltf = await new Promise<{ scene: Group }>((resolve, reject) => {
          new GLTFLoader().load(
            `/models/${gender}.glb`,
            resolve,
            undefined,
            reject,
          );
        });

        if (cancelled) return;

        // Scale model to fit: normalise so body height ≈ 1.7 (metres in GLTF space)
        const modelGroup = gltf.scene;
        const box = new Box3().setFromObject(modelGroup);
        const size = new Vector3();
        box.getSize(size);
        const targetHeight = 1.7;
        const scale = targetHeight / size.y;
        modelGroup.scale.setScalar(scale);

        // Re-centre at origin on X/Z, feet at Y=0
        const boxAfter = new Box3().setFromObject(modelGroup);
        const centre = new Vector3();
        boxAfter.getCenter(centre);
        modelGroup.position.set(-centre.x, -boxAfter.min.y, -centre.z);

        scene.add(modelGroup);

        // Find the skinned/morph mesh and apply skin-coloured material
        modelGroup.traverse((obj) => {
          if ((obj as Mesh).isMesh) {
            const mesh = obj as Mesh;
            mesh.material = new MeshStandardMaterial({
              color: 0xf0c8a0,
              roughness: 0.7,
              metalness: 0.0,
            });
            if (mesh.morphTargetInfluences) meshRef.current = mesh;
          }
        });

        // Position camera to frame the body
        camera.position.set(0, 0.85, 2.2);
        camera.lookAt(0, 0.85, 0);
        controls.target.set(0, 0.85, 0);
        controls.update();

        // Apply initial morph influences from current measurements
        applyInfluences(meshRef.current, computeInfluences(measurements, gender));

        const animate = () => {
          animFrameRef.current = requestAnimationFrame(animate);
          controls.update();
          renderer.render(scene, camera);
        };
        animate();

        setStatus("success");
      } catch {
        if (!cancelled) setStatus("error");
      }
    })();

    return () => {
      cancelled = true;
      cancelAnimationFrame(animFrameRef.current);
      controlsRef.current?.dispose();
      rendererRef.current?.dispose();
      controlsRef.current = null;
      rendererRef.current = null;
      meshRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gender]);

  // ── Update morph influences when measurements change (no reload) ────────────
  useEffect(() => {
    if (meshRef.current) {
      applyInfluences(meshRef.current, computeInfluences(measurements, gender));
    }
  }, [measurements, gender]);

  return (
    <div className={`relative ${className ?? ""}`}>
      {/* Three.js canvas target */}
      <div
        ref={containerRef}
        data-testid="body-viewer-canvas"
        onPointerDown={() => { if (controlsRef.current) controlsRef.current.autoRotate = false; }}
        style={{ width: "100%", height: "100%" }}
      />

      {/* Status overlays */}
      {status === "loading" && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-xs text-gray-400 animate-pulse">Loading body model…</div>
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-0 flex items-center justify-center px-4 text-center">
          <p className="text-xs text-gray-400">Couldn&apos;t load 3D body</p>
        </div>
      )}

      {/* Gender toggle — bottom-right corner */}
      {status === "success" && (
        <div className="absolute bottom-2 right-2 flex rounded-lg overflow-hidden border border-gray-200 text-[11px] font-semibold shadow-sm">
          <button
            type="button"
            onClick={() => onGenderChange("female")}
            className={`px-2.5 py-1 transition-colors ${
              gender === "female"
                ? "bg-rose-500 text-white"
                : "bg-white text-gray-400 hover:bg-gray-50"
            }`}
          >
            F
          </button>
          <button
            type="button"
            onClick={() => onGenderChange("male")}
            className={`px-2.5 py-1 transition-colors ${
              gender === "male"
                ? "bg-sky-500 text-white"
                : "bg-white text-gray-400 hover:bg-gray-50"
            }`}
          >
            M
          </button>
        </div>
      )}
    </div>
  );
}

function applyInfluences(mesh: Mesh | null, influences: Record<number, number>) {
  if (!mesh?.morphTargetInfluences) return;
  for (const [idx, value] of Object.entries(influences)) {
    const i = parseInt(idx, 10);
    if (i < mesh.morphTargetInfluences.length) {
      mesh.morphTargetInfluences[i] = value;
    }
  }
}
