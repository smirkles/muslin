"""Measurements route — POST /measurements.

Thin handler: validates input via Pydantic, delegates logic to lib.measurements.
"""

from fastapi import APIRouter

from lib.measurements import (
    Measurements,
    MeasurementsResponse,
    derive_size_label,
    store_measurements,
)

router = APIRouter(tags=["measurements"])


@router.post("/measurements", response_model=MeasurementsResponse)
def create_measurements(body: Measurements) -> MeasurementsResponse:
    """Accept validated body measurements and return them with a size label and session ID."""
    response = MeasurementsResponse(
        **body.model_dump(),
        size_label=derive_size_label(body.bust_cm),
        measurement_id="",
    )
    measurement_id = store_measurements(response)
    return response.model_copy(update={"measurement_id": measurement_id})
