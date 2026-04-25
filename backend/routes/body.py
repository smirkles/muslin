"""Body mesh route — POST /body/mesh."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from lib.body_model.shape_mapping import measurements_to_betas
from lib.body_model.smpl_mesh import generate_mesh
from lib.measurements import get_measurements

router = APIRouter(prefix="/body", tags=["body"])


class BodyMeshRequest(BaseModel):
    measurement_id: str


@router.post("/mesh")
def body_mesh(req: BodyMeshRequest) -> Response:
    """Generate a SMPL body mesh GLB from stored measurements."""
    try:
        measurements = get_measurements(req.measurement_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="measurement not found") from exc

    betas = measurements_to_betas(measurements)

    try:
        glb_bytes = generate_mesh(betas)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="mesh generation failed") from exc

    return Response(
        content=glb_bytes,
        media_type="model/gltf-binary",
    )
