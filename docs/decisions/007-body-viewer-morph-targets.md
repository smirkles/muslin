# ADR 007: Body Viewer — Morph-Target GLB Instead of SMPL

**Date:** 2026-04-26
**Status:** Accepted
**Spec:** 19-threejs-body-viewer

---

## Context

Spec 19 called for a live 3D body viewer driven by the user's measurements. The original plan used the SMPL body model via the `smplx` Python package: `POST /body/mesh` would call `generate_mesh()` → return a GLB.

This broke on the development machine (Intel Mac, macOS Sequoia):

- PyTorch dropped Intel Mac (x86_64) support after version 2.2.2.
- PyTorch 2.2.2 was compiled against NumPy 1.x. NumPy 2.4.4 (installed) disables the NumPy bridge: `tensor.numpy()` raises `"Numpy is not available"`.
- The mesh generation pipeline requires `tensor.numpy()` to hand vertex data from smplx → trimesh.
- Upgrading PyTorch is impossible (no wheel exists for x86_64 macOS ≥ 2.3.0).
- Downgrading NumPy to <2.0 was explicitly rejected to avoid breaking other dependencies.

## Decision

Replace the SMPL server-round-trip with **client-side GLB morph targets**:

1. **Source models:** bodyapps-viz (Fashiontec, LGPL v3) — MakeHuman-based bodies with 17 morph targets per model, including Height, Bust/Chest, Waist, and Hip Girth. Two models: female body (`female.js`) and male body (`basis.js`).

2. **One-time conversion:** A throwaway Node.js script (`/tmp/body-convert/convert.js`) using `three@0.95` (the last npm version with both `JSONLoader` and `GLTFExporter`) converts the old Three.js JSON v3 geometry format to GLB. Key steps:
   - Strip texture-loading from materials (avoids `document is not defined` in Node.js).
   - Parse geometry + morph targets via `JSONLoader.parse()`.
   - Convert morph targets from **absolute vertex positions** (Three.js JSON format) to **displacement deltas** (required by GLTF spec): `delta[i] = morph_vertex[i] - base_vertex[i]`.
   - Export via `GLTFExporter` with a mocked `window.FileReader` (uses Node.js `Blob.arrayBuffer()` with `onloadend`).
   - Output: `frontend/public/models/female.glb` and `male.glb` (~20MB each, uncompressed).

3. **Runtime:** `BodyViewer.tsx` loads the appropriate GLB via `GLTFLoader.load('/models/{gender}.glb')`, scales the scene to 1.7m height using a bounding-box normalisation, and applies `morphTargetInfluences` whenever the user's measurements change — no server call, instant updates.

4. **Morph mapping formula:** `influence = (user_cm − model_default) / (model_max − model_min)`. Values outside [0,1] are intentional — Three.js morphTargetInfluences supports negative values (shrinking below default).

   | User measurement | Female morph index | Male morph index |
   |---|---|---|
   | height_cm | 0 (Height, 110–210, default 155) | 0 (Height, 120–190, default 160) |
   | bust_cm | 5 (Breast, 70–100, default 85) | 1 (Chest, 83.76–130.56, default 96.67) |
   | waist_cm | 11 (Waist, 65–85, default 75) | 8 (Waist, 64–100, default 76.66) |
   | hip_cm | 12 (Hip Girth, 86–114, default 100) | 12 (Hip Girth, 96–124, default 112) |

5. **Gender toggle:** M/F buttons in the BodyViewer overlay. Selection stored in `useWizardStore` as `bodyGender`. Reloads the GLB; morph influences re-applied.

6. **`POST /body/mesh` route:** Left in place in the backend but unused by the frontend. No deletion needed — it may be revived if the SMPL dependency is resolved (e.g. by running on Apple Silicon or in Docker).

## Attribution

Models derived from bodyapps-viz by Fashiontec / OpnTec, LGPL v3.
Source: https://github.com/OpnTec/bodyapps-viz

Per LGPL v3, users must be able to replace the LGPL-licensed component. The GLB files are static assets loaded at runtime; a user can supply their own `/models/female.glb` and `/models/male.glb` to replace them without recompiling the application.

Credit line in demo footer: "3D body models derived from bodyapps-viz (Fashiontec, LGPL v3)."

## Consequences

- No PyTorch dependency for body viewer. Works on any machine with a browser.
- Body updates instantly as measurements change (no network latency).
- 20MB per model × 2 = 40MB static assets. Acceptable for a demo running locally; for production, Draco compression would reduce this to ~3–5MB each.
- Morph ranges are approximations — the model's internal parameter space doesn't perfectly match real-world body measurement units. Visual fidelity is sufficient for a demo.
- If an Apple Silicon or Docker environment becomes available, the SMPL route can be re-enabled by restoring the `fetchBodyMesh` call in `BodyViewer.tsx`.
