"""Dev-only routes — NOT for production use.

These endpoints exist solely to validate the project scaffold and support
local development. They are registered under the /dev prefix and must not
be exposed in user-facing API documentation.
"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from lib.utils import reverse_string

# DEV-ONLY: This router is intended for local development and testing only.
router = APIRouter(prefix="/dev", tags=["dev"])


class ReverseStringRequest(BaseModel):
    """Request body for POST /dev/reverse-string."""

    model_config = ConfigDict(strict=True)

    input: str


class ReverseStringResponse(BaseModel):
    """Response body for POST /dev/reverse-string."""

    result: str


@router.post("/reverse-string", response_model=ReverseStringResponse)
def post_reverse_string(body: ReverseStringRequest) -> ReverseStringResponse:
    """Reverse the input string and return it.

    This is a dev/test endpoint — do not use in production.
    """
    return ReverseStringResponse(result=reverse_string(body.input))
