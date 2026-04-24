"""Measurements route — POST /measurements.

Thin handler: validates input via Pydantic, delegates logic to lib.measurements.
"""

from fastapi import APIRouter

from lib.measurements import Measurements, MeasurementsResponse, derive_size_label

router = APIRouter(tags=["measurements"])


@router.post("/measurements", response_model=MeasurementsResponse)
def create_measurements(body: Measurements) -> MeasurementsResponse:
    """Accept validated body measurements and return them with a derived size label."""
    return MeasurementsResponse(
        **body.model_dump(),
        size_label=derive_size_label(body.bust_cm),
    )
