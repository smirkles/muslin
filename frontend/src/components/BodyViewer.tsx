"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  AmbientLight,
  Box3,
  CylinderGeometry,
  DirectionalLight,
  Group,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  Scene,
  SphereGeometry,
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

// ── Constants ─────────────────────────────────────────────────────────────────

const DEFAULT_CAM = { x: 0, y: 0.85, z: 2.2 } as const;
const DEFAULT_TARGET = { x: 0, y: 0.85, z: 0 } as const;

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
  const cameraRef = useRef<PerspectiveCamera | null>(null);
  const controlsRef = useRef<InstanceType<typeof OrbitControls> | null>(null);
  const animFrameRef = useRef<number>(0);
  const meshRef = useRef<Mesh | null>(null);
  const sceneRef = useRef<Scene | null>(null);
  const underwearGroupRef = useRef<Group | null>(null);

  const handleResetView = useCallback(() => {
    const controls = controlsRef.current;
    const camera = cameraRef.current;
    if (!controls || !camera) return;
    camera.position.set(DEFAULT_CAM.x, DEFAULT_CAM.y, DEFAULT_CAM.z);
    camera.lookAt(DEFAULT_TARGET.x, DEFAULT_TARGET.y, DEFAULT_TARGET.z);
    controls.target.set(DEFAULT_TARGET.x, DEFAULT_TARGET.y, DEFAULT_TARGET.z);
    controls.autoRotate = true;
    controls.update();
  }, []);

  // ── Load model whenever gender changes ──────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    // Dispose previous renderer + geometry/materials to avoid memory leaks
    cancelAnimationFrame(animFrameRef.current);
    if (meshRef.current) {
      if (Array.isArray(meshRef.current.material)) {
        meshRef.current.material.forEach((m) => m.dispose());
      } else {
        (meshRef.current.material as MeshStandardMaterial).dispose();
      }
      meshRef.current.geometry.dispose();
    }
    if (underwearGroupRef.current) {
      disposeGroup(underwearGroupRef.current);
      underwearGroupRef.current = null;
    }
    sceneRef.current = null;
    controlsRef.current?.dispose();
    rendererRef.current?.dispose();
    controlsRef.current = null;
    rendererRef.current = null;
    cameraRef.current = null;
    meshRef.current = null;
    if (containerRef.current) containerRef.current.innerHTML = "";

    (async () => {
      try {
        const container = containerRef.current;
        if (!container) return;

        const w = container.clientWidth || 320;
        const h = container.clientHeight || 420;

        const scene = new Scene();
        sceneRef.current = scene;
        const camera = new PerspectiveCamera(40, w / h, 0.01, 100);
        cameraRef.current = camera;

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
        camera.position.set(DEFAULT_CAM.x, DEFAULT_CAM.y, DEFAULT_CAM.z);
        camera.lookAt(DEFAULT_TARGET.x, DEFAULT_TARGET.y, DEFAULT_TARGET.z);
        controls.target.set(DEFAULT_TARGET.x, DEFAULT_TARGET.y, DEFAULT_TARGET.z);
        controls.update();

        // Apply initial morph influences from current measurements
        applyInfluences(meshRef.current, computeInfluences(measurements, gender));

        // Remove any underwear the measurements effect might have race-added
        // before this async load completed (sceneRef was set before GLB loaded)
        if (underwearGroupRef.current) {
          disposeGroup(underwearGroupRef.current);
          scene.remove(underwearGroupRef.current);
          underwearGroupRef.current = null;
        }
        const uwGroup = buildUnderwearGroup(measurements, gender);
        underwearGroupRef.current = uwGroup;
        scene.add(uwGroup);

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
      if (meshRef.current) {
        if (Array.isArray(meshRef.current.material)) {
          meshRef.current.material.forEach((m) => m.dispose());
        } else {
          (meshRef.current.material as MeshStandardMaterial).dispose();
        }
        meshRef.current.geometry.dispose();
      }
      if (underwearGroupRef.current) {
        disposeGroup(underwearGroupRef.current);
        underwearGroupRef.current = null;
      }
      sceneRef.current = null;
      controlsRef.current?.dispose();
      rendererRef.current?.dispose();
      controlsRef.current = null;
      rendererRef.current = null;
      cameraRef.current = null;
      meshRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally omit
  // `measurements`: morph updates run in the dedicated effect below so the
  // heavy model reload only fires on gender change, not every keystroke.
  }, [gender]);

  // ── Update morph influences + underwear when measurements change (no reload) ──
  useEffect(() => {
    if (meshRef.current) {
      applyInfluences(meshRef.current, computeInfluences(measurements, gender));
    }
    const scene = sceneRef.current;
    if (scene) {
      if (underwearGroupRef.current) {
        disposeGroup(underwearGroupRef.current);
        scene.remove(underwearGroupRef.current);
      }
      const uwGroup = buildUnderwearGroup(measurements, gender);
      underwearGroupRef.current = uwGroup;
      scene.add(uwGroup);
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
        <div
          role="status"
          data-testid="body-viewer-loading"
          className="absolute inset-0 flex items-center justify-center"
        >
          <div className="text-xs text-gray-400 animate-pulse">Loading body model…</div>
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-4 text-center">
          <p className="text-xs text-gray-400">Couldn&apos;t load 3D body</p>
          <button
            type="button"
            onClick={() => setStatus("loading")}
            className="text-xs text-sky-500 underline hover:text-sky-700"
          >
            Retry
          </button>
        </div>
      )}

      {/* Controls — visible once loaded */}
      {status === "success" && (
        <>
          {/* Reset view — bottom-left */}
          <button
            type="button"
            data-testid="body-viewer-reset"
            onClick={handleResetView}
            className="absolute bottom-2 left-2 text-[10px] text-gray-400 bg-white/80 border border-gray-200 rounded-md px-2 py-1 hover:text-gray-600 transition-colors shadow-sm"
          >
            Reset view
          </button>

          {/* Gender toggle — bottom-right */}
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
        </>
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

function disposeGroup(group: Group) {
  group.traverse((obj) => {
    const mesh = obj as Mesh;
    if (!mesh.isMesh) return;
    mesh.geometry.dispose();
    if (Array.isArray(mesh.material)) {
      mesh.material.forEach((m) => m.dispose());
    } else {
      (mesh.material as MeshStandardMaterial).dispose();
    }
  });
}

// Body landmark Y positions for bodyapps-viz model normalised to 1.7 scene units (feet at 0)
const BODY_Y = {
  crotch: 0.75,
  hipFull: 0.85,
  underbust: 1.10,
  bust: 1.17,
} as const;

function clamp(v: number, lo: number, hi: number) {
  return Math.min(Math.max(v, lo), hi);
}

function buildUnderwearGroup(
  measurements: Measurements | null,
  gender: BodyGender,
): Group {
  const group = new Group();

  const height     = measurements?.height_cm    ?? 168;
  const hip        = measurements?.hip_cm       ?? 99;
  const bust       = measurements?.bust_cm      ?? 92;
  const waist      = measurements?.waist_cm     ?? 74;
  const apexToApex = measurements?.apex_to_apex_cm ?? 18.5;

  // circumference → scene-space radius, clamped to a plausible visual range
  const spc    = 1.7 / height;
  const hipR   = clamp((hip   / (2 * Math.PI)) * spc, 0.09, 0.22);
  const waistR = clamp((waist / (2 * Math.PI)) * spc, 0.07, 0.18);
  const bustR  = clamp((bust  / (2 * Math.PI)) * spc, 0.08, 0.20);
  const halfApex = clamp((apexToApex / 2) * spc, 0.05, 0.11);

  const mat = new MeshStandardMaterial({
    color: gender === "female" ? 0xc8a8c0 : 0x8fb3cc,
    roughness: 0.95,
    metalness: 0,
  });

  // Briefs: from crotch up to just above hip fullness
  const pantsH = BODY_Y.hipFull - BODY_Y.crotch + 0.06;
  const pants = new Mesh(
    new CylinderGeometry(waistR * 1.01, hipR * 1.01, pantsH, 32),
    mat,
  );
  pants.position.y = BODY_Y.crotch + pantsH / 2;
  group.add(pants);

  if (gender === "female") {
    // Bra band at underbust
    const band = new Mesh(
      new CylinderGeometry(bustR * 0.93, bustR * 0.93, 0.035, 32),
      mat,
    );
    band.position.y = BODY_Y.underbust;
    group.add(band);

    // Cups: fixed small Z offset so perspective can't push them out of frame
    const cupR = Math.min(bustR * 0.44, 0.065);
    for (const side of [-1, 1] as const) {
      const cup = new Mesh(new SphereGeometry(cupR, 16, 12), mat);
      cup.scale.z = 0.55;
      cup.position.set(side * halfApex, BODY_Y.bust, 0.11);
      group.add(cup);
    }
  }

  return group;
}
