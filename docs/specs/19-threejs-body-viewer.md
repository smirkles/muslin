# Spec: Three.js Static Body Viewer

**Spec ID:** 19-threejs-body-viewer
**Status:** ready-for-implementation
**Created:** 2026-04-25
**Depends on:** 04-measurements-endpoint, 08-frontend-plumbing

## What it does

A rotatable 3D body viewer. After the user submits their measurements, Muslin generates a SMPL neutral body mesh scaled to approximate those measurements and renders it in a Three.js canvas. The user can rotate, zoom, and orbit the body to see their shape from any angle. This is must-have feature #7 in the v2 plan ("Static 3D body view"). No garment is drawn on the body in V1 — body only.

## User-facing behavior

After posting measurements, the user sees:

1. A loading state while the mesh is fetched (1–3 seconds).
2. A 3D canvas showing a grey/neutral SMPL body mesh, front-facing, waist-centred.
3. Auto-rotation around the vertical axis that stops on first user interaction.
4. Left-drag → orbit; scroll/pinch → zoom (clamped); right-drag → pan.
5. A "Reset view" button that returns the camera to default and restarts auto-rotation.
6. If the fetch fails: inline error message ("Couldn't build your 3D body — you can still continue to photo upload") with a retry button.

## Inputs and outputs

### Frontend component — `frontend/src/components/BodyViewer.tsx`

```typescript
interface BodyViewerProps {
  measurementId: string;
  className?: string;
  onMeshLoaded?: () => void;
}
```

`"use client"` component, loaded via `next/dynamic({ ssr: false })` at the consumer page.

### Backend endpoint — `POST /body/mesh`

Request: `{ "measurement_id": "uuid" }`

Response: `application/gltf-binary` (`.glb`) binary — Three.js `GLTFLoader` reads this natively.

Errors:
- **404** — `measurement_id` not in session store → `{"detail": "measurement not found"}`.
- **500** — smplx failed → `{"detail": "mesh generation failed"}`.

### Frontend API — add to `frontend/src/lib/api.ts`

```typescript
export async function fetchBodyMesh(measurementId: string): Promise<ArrayBuffer>
```

### SMPL shape parameter mapping — `backend/lib/body_model/shape_mapping.py`

```python
def measurements_to_betas(m: MeasurementsResponse) -> list[float]:
    """Return a length-10 β vector for SMPL neutral using linear mapping.

    β[0] = (bust_cm   - 92)  / SCALE_BUST   (default 20)
    β[1] = (waist_cm  - 76)  / SCALE_WAIST  (default 20)
    β[2] = (hip_cm    - 100) / SCALE_HIP    (default 20)
    β[3] = (height_cm - 168) / SCALE_HEIGHT (default 10)
    β[4..9] = 0.0
    Clamped to [-3.0, 3.0] per component.
    """
```

This is NOT full SMPL fitting — a rough visual scaling only.

## Acceptance criteria

### Backend — shape mapping

- [ ] Given reference measurements (bust=92, waist=76, hip=100, height=168), `measurements_to_betas` returns `[0.0] * 10`.
- [ ] Given bust_cm = 112 (reference + 20), `β[0] ≈ 1.0 ± 0.01`.
- [ ] Given bust_cm = 250, `β[0] == 3.0` (clamped).
- [ ] Given bust_cm = 20, `β[0] == -3.0` (clamped).
- [ ] Returned list is always length 10.

### Backend — mesh endpoint

- [ ] Given a valid `measurement_id`, `POST /body/mesh` returns 200, `Content-Type: model/gltf-binary`, body starting with `b"glTF"`.
- [ ] Given unknown `measurement_id`, response is 404 with `detail="measurement not found"`.
- [ ] Given `smplx` raises (mocked), response is 500 with `detail="mesh generation failed"`.
- [ ] The SMPL call receives β equal to `measurements_to_betas(stored_measurements)` (verified via mock).
- [ ] The neutral model is loaded from `assets/smpl_models/smpl/SMPL_NEUTRAL.pkl`.
- [ ] The returned GLB contains one mesh with 6890 vertices and 13776 faces (verified via `pygltflib` in test).
- [ ] `backend/lib/body_model/` has no `fastapi` imports (import-hygiene test).

### Frontend — API client

- [ ] `fetchBodyMesh(id)` calls `POST .../body/mesh` with `{ "measurement_id": id }`.
- [ ] On 200, resolves with `ArrayBuffer`.
- [ ] On non-2xx, rejects with `Error` containing the status code.

### Frontend — BodyViewer component

- [ ] On mount, `fetchBodyMesh` is called exactly once with `measurementId`.
- [ ] While fetching, a loading indicator is visible (`role="status"` or `data-testid="body-viewer-loading"`).
- [ ] On success, Three.js `Scene` contains the loaded mesh, an `AmbientLight`, and a `DirectionalLight`.
- [ ] `onMeshLoaded` (if provided) is called exactly once after mesh loads.
- [ ] On fetch error, an error message and "Retry" button appear; retry re-invokes `fetchBodyMesh`.
- [ ] `OrbitControls` from `three-stdlib` is used.
- [ ] Auto-rotation is enabled on mount (`controls.autoRotate = true`).
- [ ] On `pointerdown`, `controls.autoRotate` becomes `false`.
- [ ] "Reset view" button resets camera and re-enables auto-rotation.
- [ ] On unmount, `renderer.dispose()`, `controls.dispose()`, and animation frame are cleaned up.
- [ ] Consumer page loads `BodyViewer` via `next/dynamic(..., { ssr: false })`.

### General

- [ ] `pnpm test` passes (Three.js and GLTFLoader mocked throughout).
- [ ] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.
- [ ] `pnpm lint` exits 0.

## Out of scope

- Garment draping / cloth simulation.
- Full SMPL fitting (SMPLify) — direct β assignment only.
- Male/female models — neutral only.
- Pose changes — default T-pose.
- Measurement adjustment inside the viewer.
- Caching meshes across sessions.
- Exporting the GLB for user download.
- WebXR / AR.

## Technical approach

- `backend/lib/body_model/shape_mapping.py` — `measurements_to_betas()` pure function.
- `backend/lib/body_model/smpl_mesh.py` — `generate_mesh(betas) -> bytes` wrapping `smplx.create` + `trimesh` GLB export. Cache loaded model at module level (avoid re-loading 40 MB pkl per request).
- `backend/routes/body.py` — thin `POST /body/mesh` route.
- Three.js setup: `PerspectiveCamera(45, aspect, 0.1, 100)`, position `(0, 1.0, 3.5)`, `lookAt(0, 1.0, 0)`. Lighting: `AmbientLight(0xffffff, 0.6)` + `DirectionalLight(0xffffff, 0.8)` at `(2, 5, 3)`. `ResizeObserver` for responsive canvas.

## Dependencies

- **Backend:** `smplx` (already installed), `trimesh` (new), `pygltflib` (dev/test only).
- **Frontend:** `three` (new), `three-stdlib` (new), `@types/three` (dev).
- **Specs first:** 04-measurements-endpoint (already shipped), 08-frontend-plumbing (already shipped).
- **Manual setup:** `assets/smpl_models/smpl/SMPL_NEUTRAL.pkl` must exist (already downloaded). Backend fails fast at module import with a clear error pointing to `docs/setup.md` if missing.

## Testing approach

- **Unit tests (backend):** `tests/lib/body_model/test_shape_mapping.py` — identity, scaling, clamping. `tests/lib/body_model/test_smpl_mesh.py` — with `smplx.create` mocked. `tests/routes/test_body_mesh.py` — 200 / 404 / 500.
- **Frontend tests:** `BodyViewer.test.tsx` — loading, success, error+retry, unmount cleanup, auto-rotate disable on pointerdown. Mock `three` and `GLTFLoader`.
- **Manual verification:** submit real measurements, confirm body roughly matches proportions, rotate/zoom/pan smoothly, reset view works, try extreme measurements (body still renders).

## Open questions

1. **Which page hosts the viewer?** Recommended: `/app/photos` (above the photo uploader), since the wizard routes there after measurements. Alternative: dedicate `/app/body`. Steph decides before implementation.
2. **β scale constants** — recommended defaults: BUST=WAIST=HIP=20, HEIGHT=10. Calibrate visually after first manual verification.
3. **Self-wrapping `next/dynamic`** — should `BodyViewer` self-wrap so consumers can't accidentally statically import `three`? Default: consumer wraps. Revisit if import accidents occur.
4. **Camera position** — default `(0, 1.0, 3.5)` metres. May need adjustment after first visual check.

## Notes for implementer

- Cache the SMPL model at module level — load is ~2 s. Patch `smplx.create` before importing the module in tests.
- Three.js + jsdom is hostile. Mock `three` thoroughly — do not attempt real rendering in Vitest.
- GLB magic header: first 4 bytes are `glTF` (0x67 0x6C 0x54 0x46). Easy assertion.
- Memory hygiene on unmount: traverse scene and dispose every geometry, material, texture. `renderer.dispose()` alone is not enough.
- No prompts involved — pure deterministic code.
- Day 6 "3D garment drape" stretch will add a garment mesh as a sibling in the scene graph. Keep scene structure clean for that addition.
- If you want to deviate from GLB + trimesh + three-stdlib, stop and write an ADR in `docs/decisions/` rather than switching silently.
- Write failing tests first per `CLAUDE.md` rule 5.
