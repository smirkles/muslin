"use client";

import { useEffect, useRef, useState } from "react";
import {
  AmbientLight,
  DirectionalLight,
  PerspectiveCamera,
  Scene,
  WebGLRenderer,
} from "three";
import { GLTFLoader, OrbitControls } from "three-stdlib";

import { fetchBodyMesh } from "../lib/api";

interface BodyViewerProps {
  measurementId: string;
  className?: string;
  onMeshLoaded?: () => void;
}

type ViewerStatus = "loading" | "success" | "error";

export function BodyViewer({ measurementId, className, onMeshLoaded }: BodyViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<ViewerStatus>("loading");
  const [retryCount, setRetryCount] = useState(0);

  const rendererRef = useRef<WebGLRenderer | null>(null);
  const controlsRef = useRef<InstanceType<typeof OrbitControls> | null>(null);
  const animFrameRef = useRef<number>(0);
  const onMeshLoadedRef = useRef(onMeshLoaded);

  useEffect(() => {
    onMeshLoadedRef.current = onMeshLoaded;
  });

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    (async () => {
      try {
        const buffer = await fetchBodyMesh(measurementId);
        if (cancelled) return;

        const container = containerRef.current;
        if (!container) return;

        const w = container.clientWidth || 400;
        const h = container.clientHeight || 600;

        const scene = new Scene();
        const camera = new PerspectiveCamera(45, w / h, 0.1, 100);
        camera.position.set(0, 1.0, 3.5);
        camera.lookAt(0, 1.0, 0);

        const renderer = new WebGLRenderer({ antialias: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        const ambientLight = new AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);
        const dirLight = new DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(2, 5, 3);
        scene.add(dirLight);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.autoRotate = true;
        controlsRef.current = controls;

        const loader = new GLTFLoader();
        await new Promise<void>((resolve, reject) => {
          loader.parse(
            buffer,
            "",
            (gltf) => {
              scene.add(gltf.scene);
              resolve();
            },
            (err: unknown) => reject(err),
          );
        });

        if (cancelled) return;

        const animate = () => {
          animFrameRef.current = requestAnimationFrame(animate);
          controls.update();
          renderer.render(scene, camera);
        };
        animate();

        setStatus("success");
        onMeshLoadedRef.current?.();
      } catch {
        if (!cancelled) {
          setStatus("error");
        }
      }
    })();

    return () => {
      cancelled = true;
      cancelAnimationFrame(animFrameRef.current);
      controlsRef.current?.dispose();
      rendererRef.current?.dispose();
      controlsRef.current = null;
      rendererRef.current = null;
    };
  }, [measurementId, retryCount]);

  const handlePointerDown = () => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = false;
    }
  };

  const handleReset = () => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = true;
    }
  };

  return (
    <div className={className}>
      {status === "loading" && (
        <div data-testid="body-viewer-loading" role="status">
          Loading 3D body...
        </div>
      )}
      {status === "error" && (
        <div>
          <p>Couldn&apos;t build your 3D body — you can still continue to photo upload</p>
          <button type="button" onClick={() => setRetryCount((c) => c + 1)}>
            Retry
          </button>
        </div>
      )}
      <div
        ref={containerRef}
        data-testid="body-viewer-canvas"
        onPointerDown={handlePointerDown}
        style={{ width: "100%", height: "100%" }}
      />
      {status === "success" && (
        <button type="button" onClick={handleReset}>
          Reset view
        </button>
      )}
    </div>
  );
}
